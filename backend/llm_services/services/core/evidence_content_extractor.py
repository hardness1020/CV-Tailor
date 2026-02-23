"""
EvidenceContentExtractor - Extract structured content from evidence sources.
Implements ft-005-multi-source-artifact-preprocessing.md

This service uses LLM for intelligent extraction from a SINGLE evidence source.
Separates LLM operations from pure I/O (handled by DocumentLoaderService).
"""

import logging
import time
import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field

from ..base.base_service import BaseLLMService
from .document_loader_service import DocumentLoaderService
from ...models import ModelPerformanceMetric

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Structured content extracted from a single source"""
    source_type: str  # 'github', 'pdf', 'video', 'audio', 'web_link'
    source_url: str
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0-1.0
    processing_cost: float = 0.0
    error_message: Optional[str] = None
    extraction_success: bool = True

    # Aliases for backward compatibility with tests
    @property
    def technologies(self) -> List[str]:
        return self.data.get('technologies', [])

    @property
    def achievements(self) -> List[str]:
        return self.data.get('achievements', [])

    @property
    def quantified_metrics(self) -> List[Dict[str, Any]]:
        return self.data.get('metrics', [])

    @property
    def raw_summary(self) -> str:
        return self.data.get('summary', '')


class EvidenceContentExtractor(BaseLLMService):
    """
    Extract structured content from a SINGLE evidence source using LLM.

    Key responsibilities:
    - Use DocumentLoaderService for I/O
    - Extract technologies, achievements, metrics with LLM from ONE evidence
    - Normalize extracted data to standard taxonomy
    - Calculate confidence scores for that evidence
    - Creates data for ONE EnhancedEvidence record
    """

    # Technology normalization mapping
    TECH_MAPPING = {
        'react.js': 'React',
        'reactjs': 'React',
        'react': 'React',
        'nodejs': 'Node.js',
        'node.js': 'Node.js',
        'node': 'Node.js',
        'python3': 'Python',
        'python 3': 'Python',
        'postgresql': 'PostgreSQL',
        'postgres': 'PostgreSQL',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'docker-compose': 'Docker',
        'django': 'Django',
        'flask': 'Flask',
        'express': 'Express',
        'expressjs': 'Express',
        'vue.js': 'Vue',
        'vuejs': 'Vue',
        'angular': 'Angular',
        'angularjs': 'Angular',
        'mongodb': 'MongoDB',
        'mysql': 'MySQL',
        'redis': 'Redis',
        'aws': 'AWS',
        'amazon web services': 'AWS',
        'gcp': 'Google Cloud',
        'google cloud platform': 'Google Cloud',
        'azure': 'Azure',
        'microsoft azure': 'Azure',
    }

    def __init__(self):
        super().__init__()
        self.doc_loader = DocumentLoaderService()
        # Add PDF classifier for adaptive processing (ft-016)
        from ..infrastructure.pdf_document_classifier import PDFDocumentClassifier
        self.pdf_classifier = PDFDocumentClassifier()

    def _get_service_config(self) -> Dict[str, Any]:
        """Get content extraction specific configuration"""
        return self.settings_manager.get_llm_config()

    async def extract_github_content(self,
                                    repo_url: str,
                                    repo_stats: Optional[Dict[str, Any]] = None,
                                    user_id: Optional[int] = None) -> ExtractedContent:
        """
        Extract technologies, frameworks, metrics from GitHub repository using agent-based analysis.

        UPDATED in v1.3.0 (ft-013): Replaced legacy fixed-file extraction with GitHubRepositoryAgent.
        Uses 4-phase agent architecture:
        - Phase 1: Reconnaissance (GitHub API metadata, project type)
        - Phase 2: File Prioritization (LLM-powered file selection)
        - Phase 3: Hybrid Analysis (config/source/infra/docs parsing)
        - Phase 4: Refinement (optional iteration if confidence <0.75)

        See: docs/features/ft-013-github-agent-traversal.md
        """
        from .github_repository_agent import GitHubRepositoryAgent

        start_time = time.time()

        try:
            # Initialize agent
            agent = GitHubRepositoryAgent()

            # Run agent analysis
            result = await agent.analyze_repository(
                repo_url=repo_url,
                user_id=user_id,
                token_budget=8000,
                repo_stats=repo_stats
            )

            # Warn if result has empty summary
            if result.success and not result.data.get('summary'):
                logger.warning(
                    f"[GitHub Extraction] Agent returned SUCCESS but empty summary for {repo_url}. "
                    f"Technologies: {len(result.data.get('technologies', []))}, "
                    f"Confidence: {result.confidence:.2f}. "
                    f"Check if documentation files were loaded and analyzed."
                )
            elif result.success:
                logger.info(
                    f"[GitHub Extraction] Successfully extracted content with summary "
                    f"({len(result.data.get('summary', ''))} chars)"
                )

            # Track performance if user_id provided
            if user_id and result.success:
                processing_time = int((time.time() - start_time) * 1000)
                await self._track_extraction_performance(
                    user_id=user_id,
                    task_type='github_content_extraction',
                    processing_time_ms=processing_time,
                    success=True,
                    cost=result.processing_cost
                )

            return result

        except Exception as e:
            logger.error(f"GitHub agent analysis failed: {e}", exc_info=True)
            processing_time = int((time.time() - start_time) * 1000)

            return ExtractedContent(
                source_type='github',
                source_url=repo_url,
                success=False,
                data={'error': str(e)},
                confidence=0.0,
                error_message=str(e),
                extraction_success=False
            )

    async def extract_pdf_content(self,
                                 pdf_chunks: List[Dict[str, Any]],
                                 user_id: Optional[int] = None,
                                 source_url: Optional[str] = None) -> ExtractedContent:
        """
        Extract achievements, technologies, metrics from PDF document.

        ENHANCED in ft-016: Adaptive processing based on document type classification.

        Args:
            pdf_chunks: List of document chunks from document loader
            user_id: Optional user ID for tracking
            source_url: Optional source URL for the PDF (extracted from chunk metadata if not provided)
        """
        start_time = time.time()

        # Extract source_url and file_path from chunks metadata
        if not source_url and pdf_chunks:
            source_url = pdf_chunks[0].get('metadata', {}).get('source_url', 'pdf_document')

        file_path = pdf_chunks[0].get('metadata', {}).get('file_path') if pdf_chunks else None

        # Default classification (fallback if classification fails)
        category = 'resume'
        classification_confidence = 0.5
        strategy = {'max_chunks': 50, 'max_chars': 50_000, 'sampling': 'full', 'summary_tokens': 1_000, 'map_reduce': False}

        try:
            # Adaptive Processing (ft-016): Classify document for optimal strategy
            if file_path:
                try:
                    logger.warning(f"[ft-016] Classifying PDF: {file_path}")
                    classification = await self.pdf_classifier.classify_document(file_path)
                    category = classification['category']
                    classification_confidence = classification['confidence']
                    strategy = classification['processing_strategy']

                    logger.warning(
                        f"[ft-016] PDF classified as '{category}' "
                        f"(confidence: {classification_confidence:.2f}, "
                        f"strategy: {strategy['sampling']}, "
                        f"max_chars: {strategy['max_chars']:,}, "
                        f"max_chunks: {strategy['max_chunks']})"
                    )
                except Exception as e:
                    logger.warning(f"[ft-016] Classification failed, using default strategy: {e}")

            # Check if map-reduce extraction is needed (for large documents like theses)
            if strategy.get('map_reduce', False):
                logger.warning(
                    f"[ft-016] Using map-reduce extraction for {category} "
                    f"(map_chunk_size: {strategy.get('map_chunk_size', 0):,} chars)"
                )
                return await self._map_reduce_extraction(pdf_chunks, strategy, user_id, source_url)

            # Apply adaptive chunk selection based on strategy
            logger.warning(f"[ft-016] Selecting chunks: sampling={strategy['sampling']}, total_chunks={len(pdf_chunks)}")
            selected_chunks = self._select_chunks_by_strategy(pdf_chunks, strategy)
            logger.warning(f"[ft-016] Selected {len(selected_chunks)}/{len(pdf_chunks)} chunks")

            # Combine chunks with adaptive character limit
            full_text = self._combine_chunks(selected_chunks, strategy['max_chars'])
            logger.warning(
                f"[ft-016] Combined text: {len(full_text):,} chars "
                f"(limit: {strategy['max_chars']:,}, "
                f"utilization: {len(full_text)/strategy['max_chars']*100:.1f}%)"
            )

            # Use LLM to extract structured content
            # Enhanced for ft-030: Source attribution to prevent hallucinations
            # ft-030: HIGH-PRECISION MODE - Same strict rules for all document types
            # Confidence threshold raised to >= 0.8 to eliminate hallucinations
            anti_hallucination_rules = """CRITICAL ANTI-HALLUCINATION RULES (HIGH-PRECISION MODE):
- ONLY extract information that is EXPLICITLY STATED in the document
- For EVERY extracted item, provide the exact SOURCE QUOTE from the document
- Include source location (page number, section name)
- Assign a confidence score (0.0-1.0) based on how directly the quote supports the item
- DO NOT infer or assume information that is not directly stated
- Confidence threshold: >= 0.8 required (0.95+ for exact match, 0.8-0.9 for clear context, <0.8 rejected)
- For academic documents: Research tools/methodologies count as technologies IF explicitly mentioned
- Examples of valid extraction:
  * "Python" from "implemented in Python 3.9" → confidence 0.98 (explicit)
  * "SPSS" from "statistical analysis using SPSS 28" → confidence 0.96 (explicit with version)
  * "machine learning" from "machine learning algorithms were applied" → confidence 0.85 (explicit methodology)
- Examples of INVALID extraction (DO NOT extract):
  * "TensorFlow" from "applied neural networks" → NO explicit mention
  * "React" from "built a web interface" → NO framework specified"""

            extraction_prompt = f"""Analyze this PDF document and extract structured information for a professional CV/resume.

{anti_hallucination_rules}

Document type: {category}
Document Content:
{full_text}

Extract the following in JSON format with SOURCE ATTRIBUTION:

1. "summary": A concise 2-3 sentence professional summary
   - Highlight key expertise, role, and primary skills
   - Focus on professional identity and core competencies
   - Example: "Full-stack software engineer with 5+ years experience building scalable web applications. Specialized in Python/Django backend development and React frontends. Strong background in cloud infrastructure and DevOps practices."

2. "technologies": Array of technology objects with SOURCE ATTRIBUTION
   - Each technology must include:
     * "name": Technology name (e.g., "PostgreSQL", "React", "AWS")
     * "source_attribution": Object with:
       - "source_quote": Exact quote from document mentioning this technology
       - "source_location": Page/section where found
       - "confidence": 0.0-1.0 (0.95+ for exact match, 0.8-0.9 for clear context, <0.8 rejected)
       - "reasoning": Brief explanation of how quote supports the technology
   - Only extract EXPLICITLY mentioned technologies
   - Include: programming languages, frameworks, databases, cloud platforms, tools
   - Examples of good attribution:
     * {{"name": "Python", "source_attribution": {{"source_quote": "Developed backend services using Python", "source_location": "page 1", "confidence": 0.98, "reasoning": "Direct mention"}}}}
     * {{"name": "Django", "source_attribution": {{"source_quote": "Django framework for REST API", "source_location": "page 1", "confidence": 0.97, "reasoning": "Explicit framework mention"}}}}

3. "achievements": Array of achievement objects with SOURCE ATTRIBUTION
   - MUST include specific numbers, percentages, or metrics
   - Each achievement must include:
     * "text": The achievement statement
     * "source_attribution": Object with source_quote, source_location, confidence, reasoning
   - Focus on: business impact, performance improvements, scale, efficiency gains
   - Good examples:
     * {{"text": "Improved API response time by 40%", "source_attribution": {{"source_quote": "Optimized API queries, improving response time by 40%", "source_location": "page 1, Experience", "confidence": 0.95, "reasoning": "Direct quote with metric"}}}}
     * {{"text": "Led team of 5 engineers", "source_attribution": {{"source_quote": "Team lead for 5-person engineering team", "source_location": "page 2", "confidence": 0.92, "reasoning": "Direct mention of team size"}}}}
   - If no quantified achievements exist, return empty array []

CRITICAL: Only include items that have CONCRETE EVIDENCE in the document.
Every item MUST have source_attribution with confidence >= 0.8, or it should be excluded.
HIGH-PRECISION MODE: We prioritize accuracy over completeness. Only extract technologies you are highly confident about.

Return ONLY valid JSON with no preamble or explanation. Use this exact structure:
{{
  "summary": "professional summary here",
  "technologies": [
    {{"name": "tech1", "source_attribution": {{"source_quote": "quote", "source_location": "page X", "confidence": 0.95, "reasoning": "explanation"}}}},
    {{"name": "tech2", "source_attribution": {{"source_quote": "quote", "source_location": "page Y", "confidence": 0.92, "reasoning": "explanation"}}}}
  ],
  "achievements": [
    {{"text": "achievement with metric", "source_attribution": {{"source_quote": "quote", "source_location": "page Z", "confidence": 0.98, "reasoning": "explanation"}}}}
  ]
}}"""

            llm_response = await self._call_llm_for_extraction(
                prompt=extraction_prompt,
                user_id=user_id,
                task_type='pdf_content_extraction'
            )

            # Parse LLM response using improved JSON extraction
            extracted = self._extract_json_from_response(llm_response['content'])

            # ft-030: Check if extraction is structurally valid but content-empty
            is_empty = (
                not extracted or
                (not extracted.get('summary', '').strip() and
                 len(extracted.get('technologies', [])) == 0 and
                 len(extracted.get('achievements', [])) == 0)
            )

            if is_empty:
                # ft-030 HIGH-PRECISION: Accept empty result rather than guess with regex
                # Regex extraction would create unattributed technologies (hallucinations)
                logger.warning(
                    f"[ft-030 HIGH-PRECISION] LLM returned empty extraction for {category} document. "
                    f"Accepting empty result (no regex fallback to prevent hallucinations)."
                )
                # Keep extracted as empty (already has default empty values)

            # Ensure all expected keys exist
            extracted.setdefault('summary', '')
            extracted.setdefault('technologies', [])
            extracted.setdefault('achievements', [])

            # ft-030 HIGH-PRECISION: Filter out low-confidence extractions (< 0.8)
            filtered_technologies = self._filter_by_confidence_threshold(
                extracted.get('technologies', []),
                threshold=0.8,
                item_type='technologies'
            )
            filtered_achievements = self._filter_by_confidence_threshold(
                extracted.get('achievements', []),
                threshold=0.8,
                item_type='achievements'
            )
            extracted['technologies'] = filtered_technologies
            extracted['achievements'] = filtered_achievements

            # Extract quantified metrics
            metrics = await self.extract_quantified_metrics(full_text, user_id)

            # ft-030: Calculate source attribution metrics
            attribution_metrics = self._calculate_attribution_metrics(extracted)
            attribution_coverage = attribution_metrics['coverage']
            inferred_item_ratio = attribution_metrics['inferred_ratio']

            # Normalize technologies (now includes skills merged in)
            # For ft-030: Extract technology names from attribution format
            technologies_raw = extracted.get('technologies', [])
            if technologies_raw and isinstance(technologies_raw[0], dict):
                # New format with attribution
                technologies = await self.normalize_technologies(
                    [tech.get('name', tech) if isinstance(tech, dict) else tech for tech in technologies_raw]
                )
            else:
                # Legacy format (backward compatibility)
                technologies = await self.normalize_technologies(technologies_raw)

            # Calculate confidence
            confidence = self._calculate_pdf_confidence(
                has_achievements=len(extracted.get('achievements', [])) > 0,
                has_metrics=len(metrics) > 0,
                has_technologies=len(technologies) > 0,
                content_length=len(full_text)
            )

            # ft-030: Apply confidence penalty for high inferred ratio
            if inferred_item_ratio > 0.30:
                penalty = (inferred_item_ratio - 0.30) * 0.5  # Up to 35% penalty
                confidence = max(0.0, confidence - penalty)
                logger.warning(
                    f"[ft-030] High inferred ratio ({inferred_item_ratio:.2%}) - "
                    f"applied confidence penalty: -{penalty:.2f}"
                )

            processing_time = int((time.time() - start_time) * 1000)

            result = ExtractedContent(
                source_type='pdf',
                source_url=source_url or 'pdf_document',
                success=True,
                data={
                    'summary': extracted.get('summary', ''),  # Professional summary from LLM
                    'technologies': technologies,  # Now includes skills merged in
                    'achievements': extracted.get('achievements', []),
                    'metrics': metrics,
                    'document_category': category,  # ft-016: Store document classification
                    'classification_confidence': classification_confidence,  # ft-016: Store classification confidence
                    'attribution_coverage': attribution_coverage,  # ft-030: Percentage of items with attribution
                    'inferred_item_ratio': inferred_item_ratio  # ft-030: Percentage of inferred items
                },
                confidence=confidence,
                processing_cost=llm_response.get('cost', 0.0),
                extraction_success=True
            )

            # Track performance
            if user_id:
                await self._track_extraction_performance(
                    user_id=user_id,
                    task_type='pdf_content_extraction',
                    processing_time_ms=processing_time,
                    success=True,
                    cost=llm_response.get('cost', 0.0)
                )

            return result

        except Exception as e:
            logger.error(f"PDF content extraction failed: {e}")
            processing_time = int((time.time() - start_time) * 1000)

            return ExtractedContent(
                source_type='pdf',
                source_url=source_url or 'pdf_document',
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e),
                extraction_success=False
            )

    async def extract_video_transcription(self,
                                         video_path: str,
                                         metadata: Optional[Dict[str, Any]] = None,
                                         user_id: Optional[int] = None) -> ExtractedContent:
        """
        Transcribe video/audio and extract key topics and technologies.
        """
        start_time = time.time()

        try:
            # TODO: Implement actual video transcription using Whisper API
            # For now, return a placeholder with low confidence
            logger.warning("Video transcription not yet fully implemented, returning placeholder")

            processing_time = int((time.time() - start_time) * 1000)

            return ExtractedContent(
                source_type='video',
                source_url=video_path,
                success=True,
                data={
                    'transcription': 'Video transcription not yet implemented',
                    'topics': [],
                    'key_moments': [],
                    'technologies': [],
                    'achievements': [],
                    'summary': 'Video content pending transcription'
                },
                confidence=0.3,  # Low confidence for placeholder
                processing_cost=0.0,
                extraction_success=True
            )

        except Exception as e:
            logger.error(f"Video transcription failed: {e}")
            return ExtractedContent(
                source_type='video',
                source_url=video_path,
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e),
                extraction_success=False
            )

    async def normalize_technologies(self, technologies: List[str]) -> List[str]:
        """
        Normalize technology names to standard taxonomy.
        """
        normalized = set()

        for tech in technologies:
            tech_lower = tech.lower().strip()

            # Check if in mapping
            if tech_lower in self.TECH_MAPPING:
                normalized.add(self.TECH_MAPPING[tech_lower])
            else:
                # Keep original with proper capitalization
                normalized.add(tech.strip())

        return sorted(list(normalized))

    async def extract_quantified_metrics(self,
                                        text_content: str,
                                        user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract quantified metrics from text using regex patterns.
        """
        metrics = []

        # Percentage patterns
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        for match in re.finditer(percentage_pattern, text_content):
            value = float(match.group(1))
            # Get context (words before percentage)
            start = max(0, match.start() - 50)
            context_text = text_content[start:match.start()].split()[-5:]
            context = ' '.join(context_text)

            metrics.append({
                'type': 'percentage',
                'value': value,
                'context': context.lower().replace(' ', '_')
            })

        # Count patterns (10k, 1M, 1000+)
        count_pattern = r'(\d+(?:\.\d+)?)\s*([kKmMbB])\+?'
        for match in re.finditer(count_pattern, text_content):
            value = float(match.group(1))
            multiplier = match.group(2).upper()

            if multiplier == 'K':
                value *= 1000
            elif multiplier == 'M':
                value *= 1000000
            elif multiplier == 'B':
                value *= 1000000000

            start = max(0, match.start() - 50)
            context_text = text_content[start:match.start()].split()[-5:]
            context = ' '.join(context_text)

            metrics.append({
                'type': 'count',
                'value': int(value),
                'context': context.lower().replace(' ', '_')
            })

        # Monetary patterns ($50k, $1M)
        money_pattern = r'\$(\d+(?:\.\d+)?)\s*([kKmMbB])?'
        for match in re.finditer(money_pattern, text_content):
            value = float(match.group(1))
            multiplier = match.group(2)

            if multiplier:
                multiplier = multiplier.upper()
                if multiplier == 'K':
                    value *= 1000
                elif multiplier == 'M':
                    value *= 1000000
                elif multiplier == 'B':
                    value *= 1000000000

            start = max(0, match.start() - 50)
            context_text = text_content[start:match.start()].split()[-5:]
            context = ' '.join(context_text)

            metrics.append({
                'type': 'monetary',
                'value': value,
                'context': context.lower().replace(' ', '_')
            })

        return metrics[:10]  # Limit to top 10 metrics

    async def _call_llm_for_extraction(self,
                                      prompt: str,
                                      user_id: Optional[int],
                                      task_type: str) -> Dict[str, Any]:
        """Call LLM for content extraction using the unified client manager"""
        # Use GPT-5 for better quality extraction (upgraded from gpt-4o)
        # The improved prompts should work well with the more capable model
        response = await self.client_manager.make_completion_call(
            model='gpt-5',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are an expert at extracting structured information from documents and code repositories. Extract only factual information without embellishment.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            max_tokens=2000,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "evidence_extraction",
                    "strict": False,  # ft-030: Allow flexible format for attribution
                    "schema": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "technologies": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {"type": "string"},  # Backward compatibility
                                        {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "source_attribution": {
                                                    "type": "object",
                                                    "properties": {
                                                        "source_quote": {"type": "string"},
                                                        "source_location": {"type": "string"},
                                                        "confidence": {"type": "number"},
                                                        "reasoning": {"type": "string"}
                                                    }
                                                }
                                            },
                                            "required": ["name"]
                                        }
                                    ]
                                }
                            },
                            "achievements": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {"type": "string"},  # Backward compatibility
                                        {
                                            "type": "object",
                                            "properties": {
                                                "text": {"type": "string"},
                                                "source_attribution": {
                                                    "type": "object",
                                                    "properties": {
                                                        "source_quote": {"type": "string"},
                                                        "source_location": {"type": "string"},
                                                        "confidence": {"type": "number"},
                                                        "reasoning": {"type": "string"}
                                                    }
                                                }
                                            },
                                            "required": ["text"]
                                        }
                                    ]
                                }
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        },
                        "required": ["summary", "technologies", "achievements"],
                        "additionalProperties": False
                    }
                }
            }
        )

        # Extract content from response
        content = ''
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
        elif isinstance(response, dict) and 'choices' in response:
            content = response['choices'][0]['message']['content']

        # Calculate cost (using gpt-5)
        cost = 0.0
        if hasattr(response, 'usage'):
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
            cost = self.registry.calculate_cost('gpt-5', prompt_tokens, completion_tokens)
        elif isinstance(response, dict) and 'usage' in response:
            usage = response['usage']
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            cost = self.registry.calculate_cost('gpt-5', prompt_tokens, completion_tokens)

        return {
            'content': content,
            'cost': cost
        }

    def _calculate_github_confidence(self,
                                     repo_stats: Dict[str, Any],
                                     has_readme: bool,
                                     has_code: bool,
                                     technologies_found: int) -> float:
        """Calculate confidence score for GitHub extraction"""
        confidence = 0.5  # Base confidence

        # Boost for stars
        stars = repo_stats.get('stars', 0)
        if stars > 100:
            confidence += 0.2
        elif stars > 10:
            confidence += 0.1

        # Boost for README
        if has_readme:
            confidence += 0.15

        # Boost for code samples
        if has_code:
            confidence += 0.1

        # Boost for technologies found
        if technologies_found > 3:
            confidence += 0.1
        elif technologies_found > 0:
            confidence += 0.05

        return min(1.0, confidence)

    def _calculate_pdf_confidence(self,
                                  has_achievements: bool,
                                  has_metrics: bool,
                                  has_technologies: bool,
                                  content_length: int) -> float:
        """
        Calculate confidence score for PDF extraction.

        ft-030: Penalizes empty extractions to reflect actual quality.
        """
        confidence = 0.4  # Base confidence

        if has_achievements:
            confidence += 0.2

        if has_metrics:
            confidence += 0.2

        if has_technologies:
            confidence += 0.1

        if content_length > 1000:
            confidence += 0.1

        # ft-030: Penalty for empty extractions (indicates poor extraction quality)
        if not has_achievements and not has_technologies:
            confidence *= 0.5  # Halve confidence if both core fields are empty

        return min(1.0, confidence)

    def _filter_by_confidence_threshold(
        self,
        items: List[Union[str, Dict[str, Any]]],
        threshold: float,
        item_type: str
    ) -> List[Union[str, Dict[str, Any]]]:
        """
        Filter items by confidence threshold (ft-030 HIGH-PRECISION MODE).

        Args:
            items: List of items (technologies or achievements)
            threshold: Minimum confidence required (e.g., 0.8)
            item_type: Type of items for logging ('technologies' or 'achievements')

        Returns:
            Filtered list containing only items with confidence >= threshold

        Note:
            - Legacy string items (no attribution) are REJECTED (treated as confidence 0.0)
            - Only attributed items with confidence >= threshold pass
        """
        if not items:
            return []

        filtered = []
        rejected_count = 0

        for item in items:
            # Legacy format (string) - NO attribution, reject in high-precision mode
            if isinstance(item, str):
                rejected_count += 1
                logger.debug(
                    f"[ft-030 HIGH-PRECISION] Rejected {item_type} (legacy string): '{item}' "
                    f"(no attribution, confidence unknown)"
                )
                continue

            # Attributed format (dict)
            if isinstance(item, dict):
                attribution = item.get('source_attribution', {})
                confidence = attribution.get('confidence', 0.0)

                if confidence >= threshold:
                    filtered.append(item)
                else:
                    rejected_count += 1
                    item_name = item.get('name') or item.get('text', str(item)[:50])
                    logger.info(
                        f"[ft-030 HIGH-PRECISION] Rejected {item_type}: '{item_name}' "
                        f"(confidence {confidence:.2f} < {threshold:.2f})"
                    )

        if rejected_count > 0:
            logger.info(
                f"[ft-030 HIGH-PRECISION] Filtered {rejected_count}/{len(items)} {item_type} "
                f"(threshold: {threshold:.2f})"
            )

        return filtered

    def _calculate_attribution_metrics(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate source attribution metrics (ft-030).

        Returns:
            Dict with 'coverage' and 'inferred_ratio':
            - coverage: Percentage of items with source attribution (0.0-1.0)
            - inferred_ratio: Percentage of items with confidence < 0.5 (0.0-1.0)
        """
        total_items = 0
        attributed_items = 0
        inferred_items = 0

        # Count technologies with attribution
        technologies = extracted.get('technologies', [])
        for tech in technologies:
            total_items += 1
            if isinstance(tech, dict):
                attribution = tech.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    # Check if confidence < 0.5 (inferred)
                    confidence = attribution.get('confidence', 0.0)
                    if confidence < 0.5:
                        inferred_items += 1
            # else: Legacy format without attribution (not attributed, fully inferred)
            else:
                inferred_items += 1

        # Count achievements with attribution
        achievements = extracted.get('achievements', [])
        for achievement in achievements:
            total_items += 1
            if isinstance(achievement, dict):
                attribution = achievement.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    # Check if confidence < 0.5 (inferred)
                    confidence = attribution.get('confidence', 0.0)
                    if confidence < 0.5:
                        inferred_items += 1
            # else: Legacy format without attribution (not attributed, fully inferred)
            else:
                inferred_items += 1

        # Calculate metrics
        if total_items == 0:
            return {'coverage': 0.0, 'inferred_ratio': 0.0}

        coverage = attributed_items / total_items
        inferred_ratio = inferred_items / total_items

        logger.info(
            f"[ft-030] Attribution metrics: "
            f"coverage={coverage:.2%} ({attributed_items}/{total_items}), "
            f"inferred_ratio={inferred_ratio:.2%} ({inferred_items}/{total_items})"
        )

        return {
            'coverage': coverage,
            'inferred_ratio': inferred_ratio
        }

    def _extract_technologies_regex(self, text: str) -> List[str]:
        """Fallback: Extract technologies using common keywords"""
        common_techs = [
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'Go', 'Rust',
            'React', 'Angular', 'Vue', 'Django', 'Flask', 'Node.js', 'Express',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
            'AWS', 'Azure', 'GCP', 'Git', 'Linux'
        ]

        found = []
        text_lower = text.lower()

        for tech in common_techs:
            if tech.lower() in text_lower:
                found.append(tech)

        return found

    def _extract_achievements_regex(self, text: str) -> List[str]:
        """Fallback: Extract achievements using sentence patterns"""
        achievements = []

        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            # Look for sentences with numbers/percentages
            if re.search(r'\d+', sentence) and len(sentence) > 20:
                achievements.append(sentence.strip())

        return achievements[:5]  # Top 5

    def _generate_summary_from_first_paragraph(self, text: str) -> str:
        """
        Extract first meaningful paragraph as fallback summary when LLM returns empty.

        ft-030: Added to handle cases where strict source attribution rules
        cause LLM to return empty content.
        """
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]

        if paragraphs:
            # Return first paragraph, truncated to 500 chars
            first_para = paragraphs[0]
            if len(first_para) > 500:
                # Find last sentence boundary within 500 chars
                truncated = first_para[:500]
                last_period = truncated.rfind('.')
                if last_period > 200:  # Only truncate at sentence if reasonable
                    return truncated[:last_period + 1]
                return truncated + '...'
            return first_para

        # Fallback: just take first 300 chars if no paragraphs found
        if len(text) > 300:
            return text[:300] + '...'
        return text

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response that might have preamble or explanation.

        Tries multiple strategies:
        1. Parse entire response as JSON
        2. Find JSON between markdown code blocks
        3. Find JSON between curly braces
        """
        # Strategy 1: Try parsing entire response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Look for JSON in markdown code blocks
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find first { to last } and try parsing that
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                return json.loads(response_text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        return None

    async def _track_extraction_performance(self,
                                           user_id: int,
                                           task_type: str,
                                           processing_time_ms: int,
                                           success: bool,
                                           cost: float):
        """Track extraction performance metrics using centralized tracker"""
        try:
            # Use centralized performance tracker for consistent error handling
            await self.performance_tracker.record_task(
                model='gpt-5',  # Upgraded model
                task_type=task_type,
                processing_time_ms=processing_time_ms,
                tokens_used=0,  # Token count not available for extraction tasks
                cost_usd=cost,
                success=success,
                user_id=user_id
            )
        except Exception as e:
            # Non-critical: Performance tracking failure should not break extraction
            logger.warning(
                f"Failed to track extraction performance for user {user_id}, "
                f"task {task_type}: {e}",
                exc_info=True
            )

    def _build_task_function(self, task_type: str):
        """Build task-specific functions for unified task executor"""
        # Not needed for extraction service
        pass

    # ===== Adaptive PDF Processing Helper Methods (ft-016) =====

    def _select_chunks_by_strategy(
        self,
        pdf_chunks: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Select chunks based on document processing strategy.

        Implements different sampling strategies:
        - 'full': Sequential chunk selection
        - 'section_aware': Priority sections (abstract, methodology, results)
        - 'adaptive': Heading-aware sampling
        - 'map_reduce': Handled separately
        """
        sampling = strategy.get('sampling', 'full')
        max_chunks = strategy.get('max_chunks', 50)

        logger.warning(f"[ft-016] Chunk selection: sampling={sampling}, max_chunks={max_chunks}")

        if sampling == 'full':
            # Sequential selection
            return pdf_chunks[:max_chunks]

        elif sampling == 'section_aware':
            # Section-aware selection for research papers
            return self._select_section_aware_chunks(pdf_chunks, strategy)

        elif sampling == 'adaptive':
            # Heading-aware selection for project reports
            return self._adaptive_chunk_selection(pdf_chunks, strategy)

        elif sampling == 'map_reduce':
            # Map-reduce handled separately in extract_pdf_content
            return pdf_chunks[:max_chunks]

        else:
            # Default: sequential
            return pdf_chunks[:max_chunks]

    def _select_section_aware_chunks(
        self,
        pdf_chunks: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Select chunks prioritizing key sections for research papers.

        Priority sections: abstract, methodology, results, conclusion
        """
        priority_sections = ['abstract', 'methodology', 'results', 'conclusion']
        max_chunks = strategy.get('max_chunks', 100)

        # Separate priority chunks from others
        priority_chunks = []
        other_chunks = []

        for chunk in pdf_chunks:
            section = chunk.get('metadata', {}).get('section', '').lower()
            content_lower = chunk.get('content', '').lower()

            # Check if chunk belongs to priority section
            is_priority = any(sec in section or sec in content_lower for sec in priority_sections)

            if is_priority:
                priority_chunks.append(chunk)
            else:
                other_chunks.append(chunk)

        # Combine: priority chunks first, then fill with others
        selected = priority_chunks + other_chunks
        result = selected[:max_chunks]

        logger.warning(
            f"[ft-016] Section-aware selection: "
            f"priority={len(priority_chunks)}, other={len(other_chunks)}, "
            f"selected={len(result)}/{len(pdf_chunks)}"
        )

        return result

    def _adaptive_chunk_selection(
        self,
        pdf_chunks: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Adaptive chunk selection preferring chunks with headings.

        Used for project reports with clear structure.
        """
        max_chunks = strategy.get('max_chunks', 150)

        # Separate chunks with headings from others
        heading_chunks = []
        other_chunks = []

        for chunk in pdf_chunks:
            has_heading = chunk.get('metadata', {}).get('has_heading', False)

            # Simple heuristic: look for heading patterns in content
            content = chunk.get('content', '')
            if has_heading or self._looks_like_heading(content):
                heading_chunks.append(chunk)
            else:
                other_chunks.append(chunk)

        # Combine: heading chunks first, then others
        selected = heading_chunks + other_chunks
        result = selected[:max_chunks]

        logger.warning(
            f"[ft-016] Adaptive selection: "
            f"heading_chunks={len(heading_chunks)}, other={len(other_chunks)}, "
            f"selected={len(result)}/{len(pdf_chunks)}"
        )

        return result

    def _looks_like_heading(self, text: str) -> bool:
        """Check if text looks like a heading."""
        if not text or len(text) > 100:
            return False

        # Headings are typically short, may be capitalized, may have numbers
        heading_patterns = [
            r'^\d+\.',  # Numbered headings (1. Introduction)
            r'^[IVX]+\.',  # Roman numerals (I. Introduction)
            r'^[A-Z][a-z]+:',  # Capitalized with colon (Introduction:)
        ]

        return any(re.match(pattern, text.strip()) for pattern in heading_patterns)

    def _combine_chunks(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int
    ) -> str:
        """
        Combine chunks into text respecting character limit.

        Args:
            chunks: List of chunks to combine
            max_chars: Maximum character limit

        Returns:
            Combined text string
        """
        combined = ""
        for chunk in chunks:
            content = chunk.get('content', '')
            separator = "\n\n" if combined else ""  # No separator for first chunk

            if len(combined) + len(separator) + len(content) <= max_chars:
                combined += separator + content
            else:
                # Add partial chunk to reach limit exactly
                remaining = max_chars - len(combined) - len(separator)
                if remaining > 100:  # Only add if meaningful amount remains
                    # Leave room for "..." (3 chars)
                    combined += separator + content[:remaining - 3] + "..."
                break

        return combined

    async def _map_reduce_extraction(
        self,
        pdf_chunks: List[Dict[str, Any]],
        strategy: Dict[str, Any],
        user_id: Optional[int],
        source_url: Optional[str]
    ) -> ExtractedContent:
        """
        Map-reduce extraction for large documents (theses).

        Phase 1 (MAP): Process sections independently
        Phase 2 (REDUCE): Aggregate section summaries
        """
        map_chunk_size = strategy.get('map_chunk_size', 50_000)

        # Phase 1: MAP - Process each section
        section_summaries = []
        chunk_groups = self._group_chunks_by_chapter(pdf_chunks)

        logger.warning(
            f"[ft-016] MAP phase: Processing {len(chunk_groups)} sections "
            f"(map_chunk_size: {map_chunk_size:,} chars)"
        )

        for idx, section_chunks in enumerate(chunk_groups, 1):
            section_text = self._combine_chunks(section_chunks, map_chunk_size)
            logger.warning(
                f"[ft-016] MAP section {idx}/{len(chunk_groups)}: "
                f"{len(section_text):,} chars from {len(section_chunks)} chunks"
            )

            # Extract from section
            section_result = await self._extract_section_content(
                section_text, user_id
            )
            section_summaries.append(section_result)

        logger.warning(
            f"[ft-016] MAP phase complete: Extracted {len(section_summaries)} section summaries"
        )

        # Phase 2: REDUCE - Aggregate summaries
        logger.warning(f"[ft-016] REDUCE phase: Aggregating {len(section_summaries)} summaries")
        final_result = await self._reduce_summaries(
            section_summaries, strategy, user_id
        )

        logger.warning(
            f"[ft-016] Map-reduce complete: "
            f"technologies={len(final_result.data.get('technologies', []))}, "
            f"achievements={len(final_result.data.get('achievements', []))}"
        )

        return final_result

    def _group_chunks_by_chapter(
        self,
        pdf_chunks: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group chunks by chapter boundaries."""
        # Check if any chunks have chapter metadata
        has_chapter_metadata = any(
            chunk.get('metadata', {}).get('chapter') is not None
            for chunk in pdf_chunks
        )

        if has_chapter_metadata:
            # Group by chapter metadata
            chapter_groups = {}
            for chunk in pdf_chunks:
                chapter = chunk.get('metadata', {}).get('chapter')
                if chapter is not None:
                    if chapter not in chapter_groups:
                        chapter_groups[chapter] = []
                    chapter_groups[chapter].append(chunk)

            # Return groups sorted by chapter number
            sorted_keys = sorted(chapter_groups.keys())
            return [chapter_groups[k] for k in sorted_keys]
        else:
            # No chapter metadata - use simple chunking (every 10 chunks)
            groups = []
            current_group = []
            for i, chunk in enumerate(pdf_chunks):
                current_group.append(chunk)
                if (i + 1) % 10 == 0:
                    groups.append(current_group)
                    current_group = []

            # Add remaining chunks
            if current_group:
                groups.append(current_group)

            return groups if groups else [[]]

    async def _extract_section_content(
        self,
        section_text: str,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Extract content from a single section."""
        prompt = f"""Extract structured information from this thesis section:

{section_text}

Return JSON with: technologies (array), achievements (array), summary (string)"""

        try:
            response = await self._call_llm_for_extraction(
                prompt=prompt,
                user_id=user_id,
                task_type='section_extraction'
            )

            extracted = self._extract_json_from_response(response['content'])
            return {
                'technologies': extracted.get('technologies', []),
                'achievements': extracted.get('achievements', []),
                'summary': extracted.get('summary', '')
            }

        except Exception as e:
            logger.error(f"Section extraction failed: {e}")
            return {'technologies': [], 'achievements': [], 'summary': ''}

    async def _reduce_summaries(
        self,
        section_summaries: List[Dict[str, Any]],
        strategy: Dict[str, Any],
        user_id: Optional[int]
    ) -> ExtractedContent:
        """Aggregate section summaries into final comprehensive summary."""
        # Combine all technologies and achievements
        all_technologies = []
        all_achievements = []
        section_texts = []

        for section in section_summaries:
            all_technologies.extend(section.get('technologies', []))
            all_achievements.extend(section.get('achievements', []))
            if section.get('summary'):
                section_texts.append(section['summary'])

        # Deduplicate and normalize
        technologies = list(set(all_technologies))
        achievements = all_achievements  # Keep all achievements

        # Create comprehensive summary
        combined_summary = "\n\n".join(section_texts)

        return ExtractedContent(
            source_type='pdf',
            source_url='',
            success=True,
            data={
                'technologies': technologies,
                'achievements': achievements,
                'summary': combined_summary,
                'metrics': [],
                'document_category': 'academic_thesis',
                'classification_confidence': 0.9
            },
            confidence=0.9,
            processing_cost=0.0
        )

    def _build_adaptive_prompt(self, content: str, category: str) -> str:
        """
        Build document-category-specific prompt for extraction.

        Different categories require different extraction approaches:
        - Certificates: Brief, focused on credential details
        - Resumes: Standard detail extraction
        - Papers: Emphasize methodology and results
        - Reports: Focus on implementation and architecture
        - Theses: Comprehensive multi-chapter synthesis
        """
        category_prompts = {
            'certificate': f"""Analyze this certificate document and extract key information.

Document Content:
{content}

Extract in JSON format:
- "technologies": Technologies or skills certified (if applicable)
- "achievements": Certification details, issuer, date
- "summary": Brief description of the credential

Be concise - this is a certificate document.""",

            'resume': f"""Analyze this resume/CV and extract structured information.

Document Content:
{content}

Extract in JSON format:
1. "technologies": Specific technologies, tools, frameworks mentioned
2. "achievements": Notable accomplishments with metrics
3. "metrics": Quantifiable results (percentages, amounts, timeframes)
4. "summary": Professional summary highlighting key qualifications""",

            'research_paper': f"""Analyze this research paper and extract structured information.

Document Content:
{content}

Extract in JSON format:
1. "technologies": Research tools, frameworks, platforms used
2. "achievements": Key findings, contributions, publications
3. "metrics": Performance metrics, accuracy, results
4. "summary": Research summary emphasizing methodology and results

Focus on academic contributions and research impact.""",

            'project_report': f"""Analyze this project report and extract structured information.

Document Content:
{content}

Extract in JSON format:
1. "technologies": Specific technologies, frameworks, architectures implemented
2. "achievements": Project deliverables, milestones, outcomes
3. "metrics": Performance metrics, scale, impact
4. "summary": Comprehensive project summary covering design, implementation, results

Focus on technical depth and implementation details.""",

            'academic_thesis': f"""Analyze this academic thesis section and extract structured information.

Document Content:
{content}

Extract in JSON format:
1. "technologies": Research tools, frameworks, platforms, methodologies
2. "achievements": Research contributions, publications, innovations
3. "metrics": Experimental results, performance metrics, accuracy
4. "summary": Comprehensive summary covering research problem, approach, findings, impact

Provide thorough detail appropriate for a major academic work."""
        }

        return category_prompts.get(category, category_prompts['resume'])