"""
PDF Document Classifier Service.

Classifies PDF documents into categories for adaptive processing.
Uses hybrid two-tier approach: rule-based (fast) + LLM refinement (high confidence).
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from llm_services.services.base.base_service import BaseLLMService

logger = logging.getLogger(__name__)


# Document processing strategies (ft-016, spec-llm.md v3.2.0)
DOCUMENT_STRATEGIES = {
    'resume': {
        'max_chunks': 50,
        'max_chars': 50_000,
        'sampling': 'full',
        'summary_tokens': 1_000,
        'chunk_selection': 'sequential',
        'map_reduce': False
    },
    'certificate': {
        'max_chunks': 10,
        'max_chars': 10_000,
        'sampling': 'full',
        'summary_tokens': 500,
        'chunk_selection': 'sequential',
        'map_reduce': False
    },
    'research_paper': {
        'max_chunks': 100,
        'max_chars': 100_000,
        'sampling': 'section_aware',
        'summary_tokens': 1_500,
        'chunk_selection': 'section_priority',
        'map_reduce': False
    },
    'project_report': {
        'max_chunks': 150,
        'max_chars': 150_000,
        'sampling': 'adaptive',
        'summary_tokens': 2_000,
        'chunk_selection': 'heading_aware',
        'map_reduce': False
    },
    'academic_thesis': {
        'max_chunks': 300,
        'max_chars': 300_000,
        'sampling': 'map_reduce',
        'summary_tokens': 3_000,
        'chunk_selection': 'chapter_aware',
        'map_reduce': True,
        'map_chunk_size': 50_000,
        'reduce_strategy': 'hierarchical'
    }
}


class PDFDocumentClassifier(BaseLLMService):
    """
    Classify PDF documents into categories for adaptive processing.

    Uses hybrid two-tier classification:
    - Tier 1: Rule-based (fast, free, 85% accuracy)
    - Tier 2: LLM refinement (2s, $0.003, 95% accuracy)

    Categories: resume, certificate, research_paper, project_report, academic_thesis

    Related: ADR-20251007-hybrid-pdf-classification-strategy
    """

    CLASSIFICATION_KEYWORDS = {
        'resume': ['experience', 'education', 'skills', 'work history', 'employment'],
        'certificate': ['certificate', 'awarded', 'completion', 'certified', 'accredited'],
        'research_paper': ['abstract', 'methodology', 'results', 'references', 'introduction'],
        'project_report': ['implementation', 'design', 'architecture', 'testing', 'deployment'],
        'academic_thesis': ['thesis', 'dissertation', 'chapter', 'acknowledgements', 'advisor']
    }

    def __init__(self):
        """Initialize PDF document classifier."""
        super().__init__()
        self.service_name = 'pdf_document_classifier'

    async def classify_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify PDF document into one of 5 categories.

        Args:
            file_path: Path to PDF file
            metadata: Optional metadata (page_count, file_size, first_page_text)

        Returns:
            {
                'category': str,  # resume, certificate, paper, report, thesis
                'confidence': float,  # 0.0-1.0
                'processing_strategy': Dict[str, Any],
                'metadata': Dict[str, Any]
            }
        """
        try:
            # Extract metadata if not provided
            if metadata is None:
                metadata = await self._extract_metadata(file_path)

            logger.warning(
                f"[ft-016] Classification input: "
                f"pages={metadata.get('page_count')}, "
                f"size={metadata.get('file_size', 0)/1024:.1f}KB, "
                f"file={file_path}"
            )

            # Tier 1: Rule-based classification (fast path)
            category, confidence = self._classify_by_rules(metadata)
            logger.warning(f"[ft-016] Rule-based: category={category}, confidence={confidence:.2f}")

            # Tier 2: LLM refinement for low confidence (<0.7)
            if confidence < 0.7:
                logger.warning(f"[ft-016] Low confidence ({confidence:.2f}), using LLM refinement")
                category, confidence = await self._classify_with_llm(metadata, file_path)
                logger.warning(f"[ft-016] LLM-refined: category={category}, confidence={confidence:.2f}")

            # Get processing strategy for category
            strategy = self._get_processing_strategy(category)

            logger.warning(
                f"[ft-016] Classification result: '{category}' "
                f"(confidence: {confidence:.2f}, "
                f"max_chars: {strategy['max_chars']:,}, "
                f"sampling: {strategy['sampling']})"
            )

            return {
                'category': category,
                'confidence': confidence,
                'processing_strategy': strategy,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Classification error: {e}, falling back to 'resume'")
            # Fallback to safe default
            return {
                'category': 'resume',
                'confidence': 0.5,
                'processing_strategy': DOCUMENT_STRATEGIES['resume'],
                'metadata': metadata or {}
            }

    def _classify_by_rules(
        self,
        metadata: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Rule-based classification using page count, size, and keywords.

        Returns:
            (category, confidence)
        """
        page_count = metadata.get('page_count', 0)
        file_size = metadata.get('file_size', 0)
        first_page_text = metadata.get('first_page_text', '').lower()

        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in self.CLASSIFICATION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in first_page_text)
            category_scores[category] = score

        # Apply heuristics based on page count and file size

        # Small documents (1-3 pages, <300KB)
        if page_count <= 3 and file_size < 300_000:
            if category_scores.get('certificate', 0) > 0:
                return 'certificate', 0.9
            elif category_scores.get('resume', 0) > 0:
                return 'resume', 0.85
            # Default for small docs
            return 'certificate' if file_size < 100_000 else 'resume', 0.7

        # Resumes (1-5 pages, common size)
        if 1 <= page_count <= 5:
            if category_scores.get('resume', 0) > 0:
                return 'resume', 0.85

        # Large documents (50+ pages)
        if page_count >= 50:
            if category_scores.get('academic_thesis', 0) > 0:
                return 'academic_thesis', 0.9
            # Large docs likely thesis or large report
            return 'academic_thesis' if page_count > 100 else 'project_report', 0.75

        # Medium-small documents (5-20 pages)
        if 5 <= page_count <= 20:
            if category_scores.get('research_paper', 0) > 0:
                return 'research_paper', 0.85
            # Could be short report or paper
            return 'research_paper' if category_scores.get('abstract', 0) > 0 else 'project_report', 0.7

        # Medium documents (10-50 pages) - likely reports
        if 10 <= page_count <= 50:
            return 'project_report', 0.7

        # Default: Use keyword scores
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            max_keywords = len(self.CLASSIFICATION_KEYWORDS[best_category])
            confidence = min(category_scores[best_category] / max_keywords, 0.6)
            return best_category, confidence

        # Ultimate fallback
        return 'resume', 0.5

    async def _classify_with_llm(
        self,
        metadata: Dict[str, Any],
        file_path: str
    ) -> Tuple[str, float]:
        """
        LLM-based classification for ambiguous cases.

        Uses GPT-5-mini for cost efficiency.
        """
        try:
            prompt = f"""Analyze this PDF document metadata and classify it into ONE of these categories:
- resume: Professional CV or resume (1-5 pages)
- certificate: Certification or award document (1-3 pages)
- research_paper: Academic research paper (5-20 pages)
- project_report: Technical project documentation (10-50 pages)
- academic_thesis: PhD thesis or dissertation (50+ pages)

Metadata:
- Pages: {metadata.get('page_count')}
- File size: {metadata.get('file_size')} bytes
- First page excerpt: {metadata.get('first_page_text', '')[:500]}

Return ONLY the category name and confidence (0.0-1.0) in JSON format:
{{"category": "resume", "confidence": 0.95}}"""

            response = await self._call_llm_for_classification(prompt)
            result = self._extract_json_from_response(response['content'])

            category = result.get('category', 'resume')
            confidence = float(result.get('confidence', 0.5))

            # Validate category
            if category not in DOCUMENT_STRATEGIES:
                logger.warning(f"Invalid category '{category}' from LLM, using 'resume'")
                category = 'resume'
                confidence = 0.5

            return category, confidence

        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return 'resume', 0.5

    async def _call_llm_for_classification(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM API for classification.

        Uses GPT-5-mini for cost efficiency (~$0.003 per classification).
        """
        try:
            # Use task executor with circuit breaker
            result = await self.task_executor.execute_with_retry(
                task_name='pdf_classification',
                task_func=self._make_llm_call,
                prompt=prompt,
                model='gpt-5-mini',
                max_tokens=100,
                temperature=0.1  # Low temp for deterministic classification
            )
            return result

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    async def _make_llm_call(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Make actual LLM API call."""
        # Import here to avoid circular dependency
        from openai import AsyncOpenAI
        import os

        client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        return {
            'content': response.choices[0].message.content,
            'tokens': response.usage.total_tokens,
            'cost': self._calculate_cost(response.usage.total_tokens, model)
        }

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try direct JSON parse
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in markdown code block
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find bare JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            # Fallback
            logger.warning(f"Could not extract JSON from: {content}")
            return {'category': 'resume', 'confidence': 0.5}

    def _get_processing_strategy(self, category: str) -> Dict[str, Any]:
        """Get processing strategy for document category."""
        return DOCUMENT_STRATEGIES.get(category, DOCUMENT_STRATEGIES['resume'])

    async def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic metadata from PDF file."""
        # This will be implemented to call existing extract_pdf_metadata
        # For now, return empty dict (will be enhanced in integration)
        logger.warning(f"Metadata extraction not yet integrated for {file_path}")
        return {
            'page_count': 0,
            'file_size': 0,
            'first_page_text': ''
        }

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost for token usage."""
        # GPT-5-mini pricing (TBD, using estimates)
        # Input: $0.001/1K tokens, Output: $0.002/1K tokens
        # Simplified: average $0.0015/1K tokens
        return (tokens / 1000) * 0.0015
