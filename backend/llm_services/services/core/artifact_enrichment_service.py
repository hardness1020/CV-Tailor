"""
ArtifactEnrichmentService - Orchestrates multi-source artifact preprocessing.
Implements ft-005-multi-source-artifact-preprocessing.md

This is the top-level service that coordinates the entire preprocessing pipeline:
- Extract content from all sources (GitHub, PDF, video, web)
- Unify content with LLM
- Store in EnhancedEvidence

End-to-end pipeline from Artifact → EnhancedEvidence.

Error Handling:
- Raises EnrichmentError for all failure cases
- No longer returns {"success": False, "error": "..."} dicts
"""

import logging
import asyncio
import time
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter

from django.contrib.auth import get_user_model

from ..base.base_service import BaseLLMService
from .document_loader_service import DocumentLoaderService
from .evidence_content_extractor import EvidenceContentExtractor, ExtractedContent
from ...models import EnhancedEvidence
from common.exceptions import (
    EnrichmentError, ArtifactNotFoundError, InsufficientDataError,
    ContentProcessingError
)

logger = logging.getLogger(__name__)
User = get_user_model()

# GPT-5 token limits for reasoning model (ft-045, ADR-048)
# GPT-5 uses reasoning tokens - need higher max_tokens to allow for reasoning + text output
GPT5_UNIFICATION_MAX_TOKENS = 8000  # Supports reasoning + 400-word output


@dataclass
class EnrichedArtifactResult:
    """
    Result of artifact enrichment process (ft-007: embeddings removed).

    Note: No longer includes success/error_message fields.
    Services now raise EnrichmentError exceptions instead of returning failure results.
    """
    artifact_id: int
    unified_description: str = ""
    enriched_technologies: List[str] = field(default_factory=list)
    enriched_achievements: List[str] = field(default_factory=list)
    processing_confidence: float = 0.0
    total_cost_usd: float = 0.0
    processing_time_ms: int = 0
    sources_processed: int = 0
    sources_successful: int = 0

    # Aliases for backward compatibility
    @property
    def technologies(self):
        return self.enriched_technologies

    @property
    def achievements(self):
        return self.enriched_achievements


class ArtifactEnrichmentService(BaseLLMService):
    """
    Orchestrates multi-source artifact preprocessing pipeline (ft-005).
    """

    def __init__(self):
        super().__init__()
        self.doc_loader = DocumentLoaderService()
        self.content_extractor = EvidenceContentExtractor()

    def _get_service_config(self) -> Dict[str, Any]:
        """Get artifact enrichment specific configuration"""
        return self.settings_manager.get_llm_config()

    async def preprocess_multi_source_artifact(self,
                                              artifact_id: int,
                                              job_id: int,
                                              user_id: int) -> EnrichedArtifactResult:
        """
        Main orchestration for ft-005 multi-source preprocessing.
        """
        start_time = time.time()
        total_cost = 0.0

        try:
            # Import Django models
            from artifacts.models import Artifact, Evidence, ArtifactProcessingJob

            # Load artifact from database
            try:
                artifact = await Artifact.objects.select_related('user').aget(id=artifact_id)
            except Artifact.DoesNotExist:
                raise ArtifactNotFoundError(f"Artifact {artifact_id} not found")

            # Load evidence links
            evidence_links = []
            async for evidence in Evidence.objects.filter(artifact=artifact):
                evidence_links.append({
                    'id': evidence.id,
                    'url': evidence.url,
                    'evidence_type': evidence.evidence_type,
                    'file_path': evidence.file_path,
                    'description': evidence.description
                })

            if not evidence_links:
                logger.warning(f"Artifact {artifact_id} has no evidence links")
                raise InsufficientDataError(
                    f"Artifact {artifact_id} has no evidence sources - cannot enrich artifact"
                )

            # Extract content from all sources in parallel
            logger.info(f"Extracting content from {len(evidence_links)} sources for artifact {artifact_id}")
            extracted_contents = await self.extract_from_all_sources(
                evidence_links=evidence_links,
                user_id=user_id
            )

            # Calculate total cost
            for ec in extracted_contents:
                total_cost += ec.processing_cost

            # Count successful extractions
            successful_extractions = [ec for ec in extracted_contents if ec.success]
            logger.info(f"Successfully extracted {len(successful_extractions)}/{len(extracted_contents)} sources")

            # v1.2.1: Check if ANY sources succeeded - fail fast if all failed
            if len(successful_extractions) == 0:
                error_msg = f"All {len(extracted_contents)} evidence source(s) failed to extract content"
                logger.error(f"[Enrichment] {error_msg} for artifact {artifact_id}")
                raise InsufficientDataError(error_msg)

            # Unify content with LLM
            unified_description = await self.unify_content_with_llm(
                extracted_contents=successful_extractions,
                artifact_title=artifact.title,
                artifact_description=artifact.description,
                user_context=artifact.user_context,  # NEW (ft-018): Pass user-provided context
                user_id=user_id
            )

            # Extract and merge technologies
            technologies = await self.extract_and_merge_technologies(
                extracted_contents=successful_extractions,
                user_id=user_id
            )

            # Extract and rank achievements
            achievements_data = await self.extract_and_rank_achievements(
                extracted_contents=successful_extractions,
                user_id=user_id
            )
            achievements = [a['achievement'] for a in achievements_data]

            # Calculate overall confidence
            confidence = await self.calculate_overall_confidence(
                extracted_contents=extracted_contents,
                unified_description=unified_description
            )

            # NOTE (ft-007): Embedding generation removed - using keyword-only ranking
            # NOTE: Artifact saving removed - let task layer handle after quality validation
            # This prevents premature persistence of low-quality enrichment data

            # Create EnhancedEvidence records for each source
            for evidence_link in evidence_links:
                evidence_obj = await Evidence.objects.aget(id=evidence_link['id'])

                # Find matching extracted content
                # Match by URL (exact or contained) or by matching source types
                logger.debug(f"Looking for extraction match for evidence: {evidence_link['url']}")
                logger.debug(f"Available extractions: {[(ec.source_url, ec.source_type) for ec in extracted_contents]}")

                matching_extraction = next(
                    (ec for ec in extracted_contents
                     if evidence_link['url'] == ec.source_url or evidence_link['url'] in ec.source_url),
                    None
                )

                if matching_extraction:
                    logger.info(f"✅ Found matching extraction for {evidence_link['url']}: {matching_extraction.source_url}")
                else:
                    logger.warning(f"❌ No matching extraction found for {evidence_link['url']}")

                if matching_extraction and matching_extraction.success:
                    # Create or update EnhancedEvidence (ft-007: embeddings removed)
                    # This stores processed content for UI display (see artifacts/serializers.py)
                    # No longer stores embeddings - using keyword-only ranking instead
                    enhanced_evidence, created = await EnhancedEvidence.objects.aupdate_or_create(
                        evidence=evidence_obj,
                        defaults={
                            'user_id': user_id,
                            'title': evidence_link.get('description', evidence_link['url']),
                            'content_type': evidence_link['evidence_type'],
                            'raw_content': json.dumps(matching_extraction.data),
                            'processed_content': matching_extraction.data,
                            'processing_confidence': matching_extraction.confidence,
                            'llm_model_used': 'gpt-5',  # Upgraded for better quality
                            'accepted': False,  # ft-045: Default to not accepted (requires user review)
                        }
                    )

            processing_time = int((time.time() - start_time) * 1000)

            result = EnrichedArtifactResult(
                artifact_id=artifact_id,
                unified_description=unified_description,
                enriched_technologies=technologies,
                enriched_achievements=achievements,
                processing_confidence=confidence,
                total_cost_usd=total_cost,
                processing_time_ms=processing_time,
                sources_processed=len(evidence_links),
                sources_successful=len(successful_extractions)
            )

            logger.info(f"Artifact {artifact_id} preprocessing completed in {processing_time}ms")
            return result

        except (ArtifactNotFoundError, InsufficientDataError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            logger.error(f"Artifact enrichment failed for artifact {artifact_id}: {e}", exc_info=True)
            raise EnrichmentError(
                f"Unexpected error during artifact {artifact_id} enrichment: {str(e)}"
            ) from e

    async def extract_per_source_only(self,
                                     artifact_id: int,
                                     job_id: int,
                                     user_id: int) -> Dict[str, Any]:
        """
        Phase 1 enrichment: Extract content from each evidence source without unification.

        This is called during Step 5 (Processing) of the wizard flow (ft-045).
        It creates EnhancedEvidence records but does NOT generate unified_description.

        Phase 2 (reunify_from_accepted_evidence) is called after user acceptance in Step 6.

        Returns:
            Dict with extraction metrics (no artifact-level enrichment)
        """
        start_time = time.time()
        total_cost = 0.0

        try:
            # Import Django models
            from artifacts.models import Artifact, Evidence

            # Load artifact from database
            try:
                artifact = await Artifact.objects.select_related('user').aget(id=artifact_id)
            except Artifact.DoesNotExist:
                raise ArtifactNotFoundError(f"Artifact {artifact_id} not found")

            # Load evidence links
            evidence_links = []
            async for evidence in Evidence.objects.filter(artifact=artifact):
                evidence_links.append({
                    'id': evidence.id,
                    'url': evidence.url,
                    'evidence_type': evidence.evidence_type,
                    'file_path': evidence.file_path,
                    'description': evidence.description
                })

            if not evidence_links:
                logger.warning(f"Artifact {artifact_id} has no evidence links")
                raise InsufficientDataError(
                    f"Artifact {artifact_id} has no evidence sources - cannot extract content"
                )

            # Extract content from all sources in parallel (Phase 1 only)
            logger.info(f"[Phase 1] Extracting content from {len(evidence_links)} sources for artifact {artifact_id}")
            extracted_contents = await self.extract_from_all_sources(
                evidence_links=evidence_links,
                user_id=user_id
            )

            # Calculate total cost
            for ec in extracted_contents:
                total_cost += ec.processing_cost

            # Count successful extractions
            successful_extractions = [ec for ec in extracted_contents if ec.success]
            logger.info(f"[Phase 1] Successfully extracted {len(successful_extractions)}/{len(extracted_contents)} sources")

            # Check if ANY sources succeeded - fail fast if all failed
            if len(successful_extractions) == 0:
                error_msg = f"All {len(extracted_contents)} evidence source(s) failed to extract content"
                logger.error(f"[Phase 1] {error_msg} for artifact {artifact_id}")
                raise InsufficientDataError(error_msg)

            # Create EnhancedEvidence records for each source
            enhanced_count = 0
            for evidence_link in evidence_links:
                evidence_obj = await Evidence.objects.aget(id=evidence_link['id'])

                # Find matching extracted content
                matching_extraction = next(
                    (ec for ec in extracted_contents
                     if evidence_link['url'] == ec.source_url or evidence_link['url'] in ec.source_url),
                    None
                )

                if matching_extraction and matching_extraction.success:
                    # Create or update EnhancedEvidence
                    enhanced_evidence, created = await EnhancedEvidence.objects.aupdate_or_create(
                        evidence=evidence_obj,
                        defaults={
                            'user_id': user_id,
                            'title': evidence_link.get('description', evidence_link['url']),
                            'content_type': evidence_link['evidence_type'],
                            'raw_content': json.dumps(matching_extraction.data),
                            'processed_content': matching_extraction.data,
                            'processing_confidence': matching_extraction.confidence,
                            'llm_model_used': 'gpt-5',
                            'accepted': False,  # ft-045: Default to not accepted (requires user review)
                        }
                    )
                    enhanced_count += 1
                    action = "Created" if created else "Updated"
                    logger.info(f"[Phase 1] {action} EnhancedEvidence for {evidence_link['url']}")
                else:
                    logger.warning(f"[Phase 1] Skipping EnhancedEvidence creation for {evidence_link['url']} - extraction failed")

            processing_time = int((time.time() - start_time) * 1000)

            result = {
                'artifact_id': artifact_id,
                'phase': 1,
                'enhanced_evidence_created': enhanced_count,
                'sources_processed': len(evidence_links),
                'sources_successful': len(successful_extractions),
                'processing_time_ms': processing_time,
                'total_cost_usd': total_cost,
            }

            logger.info(f"[Phase 1] Artifact {artifact_id} per-source extraction completed in {processing_time}ms")
            logger.info(f"[Phase 1] Created {enhanced_count} EnhancedEvidence records - ready for Step 6 review")
            return result

        except (ArtifactNotFoundError, InsufficientDataError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            logger.error(f"[Phase 1] Per-source extraction failed for artifact {artifact_id}: {e}", exc_info=True)
            raise EnrichmentError(
                f"Unexpected error during Phase 1 extraction for artifact {artifact_id}: {str(e)}"
            ) from e

    async def extract_from_all_sources(self,
                                      evidence_links: List[Dict[str, Any]],
                                      user_id: Optional[int] = None) -> List[ExtractedContent]:
        """
        Process all evidence links in parallel.
        """
        extraction_tasks = []

        for evidence in evidence_links:
            evidence_type = evidence['evidence_type']
            url = evidence['url']

            if evidence_type == 'github':
                # Extract from GitHub repository
                task = self.content_extractor.extract_github_content(
                    repo_url=url,
                    user_id=user_id
                )
                extraction_tasks.append(task)

            elif evidence_type == 'document':
                # Extract from PDF
                if evidence.get('file_path'):
                    # Load PDF and extract
                    pdf_load_result = await self.doc_loader.load_and_chunk_document(
                        content=evidence['file_path'],
                        content_type='pdf',
                        metadata={'source_url': url}
                    )

                    if pdf_load_result.get('success'):
                        task = self.content_extractor.extract_pdf_content(
                            pdf_chunks=pdf_load_result.get('chunks', []),
                            user_id=user_id,
                            source_url=url  # Pass the actual evidence URL
                        )
                        extraction_tasks.append(task)
                    else:
                        # Create failed extraction
                        extraction_tasks.append(self._create_failed_extraction(
                            'pdf', url, "Failed to load PDF"
                        ))
                else:
                    extraction_tasks.append(self._create_failed_extraction(
                        'pdf', url, "No file path provided"
                    ))

            elif evidence_type == 'video':
                # Extract from video (placeholder for now)
                task = self.content_extractor.extract_video_transcription(
                    video_path=evidence.get('file_path', url),
                    metadata={'source_url': url},
                    user_id=user_id
                )
                extraction_tasks.append(task)

            elif evidence_type in ['website', 'portfolio', 'live_app']:
                # Web scraping (basic implementation)
                web_load_result = await self.doc_loader.load_and_chunk_document(
                    content=url,
                    content_type='html',
                    metadata={'source_url': url}
                )

                if web_load_result.get('success'):
                    # Use PDF extractor as fallback for web content
                    task = self.content_extractor.extract_pdf_content(
                        pdf_chunks=web_load_result.get('chunks', []),
                        user_id=user_id,
                        source_url=url  # Pass the actual evidence URL
                    )
                    extraction_tasks.append(task)
                else:
                    extraction_tasks.append(self._create_failed_extraction(
                        'web', url, "Failed to load web page"
                    ))

            else:
                # Unknown type
                extraction_tasks.append(self._create_failed_extraction(
                    evidence_type, url, f"Unsupported evidence type: {evidence_type}"
                ))

        # Run all extractions in parallel
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Handle exceptions
        extracted_contents = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Extraction task {i} failed with exception: {result}")
                evidence = evidence_links[i]
                extracted_contents.append(ExtractedContent(
                    source_type=evidence['evidence_type'],
                    source_url=evidence['url'],
                    success=False,
                    data={},
                    confidence=0.0,
                    error_message=str(result),
                    extraction_success=False
                ))
            else:
                extracted_contents.append(result)

        return extracted_contents

    async def _create_failed_extraction(self, source_type: str, url: str, error: str) -> ExtractedContent:
        """Create a failed extraction result"""
        return ExtractedContent(
            source_type=source_type,
            source_url=url,
            success=False,
            data={},
            confidence=0.0,
            error_message=error,
            extraction_success=False
        )

    async def unify_content_with_llm(self,
                                    extracted_contents: List[ExtractedContent],
                                    artifact_title: str,
                                    artifact_description: str,
                                    user_context: str = "",
                                    user_id: Optional[int] = None) -> str:
        """
        Generate unified description from all extracted content using LLM.

        Args:
            extracted_contents: Content extracted from evidence sources
            artifact_title: Title of artifact
            artifact_description: Brief description from user
            user_context: User-provided context (NEW ft-018 - treated as immutable ground truth)
            user_id: User ID for tracking

        Returns:
            Unified description incorporating user context and evidence
        """
        if not extracted_contents:
            # Fallback when no evidence
            if user_context and user_context.strip():
                return f"{artifact_title}. {user_context.strip()}"
            return f"{artifact_title}. {artifact_description}"

        # Build evidence summaries
        source_summaries = []
        for ec in extracted_contents:
            if ec.success:
                summary = f"Source: {ec.source_type} ({ec.source_url})\n"

                # ft-030: Extract technology names from attributed or string format
                tech_names = []
                if 'technologies' in ec.data:
                    for tech in ec.data['technologies']:
                        if isinstance(tech, str):
                            tech_names.append(tech)
                        elif isinstance(tech, dict) and 'name' in tech:
                            tech_names.append(tech['name'])
                if tech_names:
                    summary += f"Technologies: {', '.join(tech_names[:10])}\n"

                # ft-030: Extract achievement text from attributed or string format
                achievement_texts = []
                if 'achievements' in ec.data:
                    for ach in ec.data['achievements']:
                        if isinstance(ach, str):
                            achievement_texts.append(ach)
                        elif isinstance(ach, dict) and 'text' in ach:
                            achievement_texts.append(ach['text'])
                if achievement_texts:
                    summary += f"Achievements: {', '.join(achievement_texts[:5])}\n"

                if ec.data.get('description'):
                    summary += f"Description: {ec.data['description']}\n"
                source_summaries.append(summary)

        # NEW (ft-018): Restructured prompt with user context as immutable ground truth
        # Separate user facts from evidence to prevent LLM from overriding user input

        has_user_context = user_context and user_context.strip()
        has_description = artifact_description and artifact_description.strip()

        if has_user_context:
            # User context exists - treat as IMMUTABLE
            unification_prompt = f"""You are creating a professional CV/resume description. You MUST follow this strict hierarchy:

**GROUND TRUTH (User-Provided Facts - IMMUTABLE):**
{user_context.strip()}

**EVIDENCE FROM SOURCES (Use to enhance, NOT contradict):**
{chr(10).join(source_summaries)}

**CRITICAL RULES:**
1. User-provided FACTS are ABSOLUTE TRUTH - preserve all numbers, team sizes, metrics, roles EXACTLY
2. User-provided LANGUAGE can be improved - fix grammar, enhance flow, make professional
3. INTEGRATE facts naturally into flowing narrative - DO NOT copy-paste user text as standalone sentences
4. If user says "team of 5", output must say "team of 5" (not "team of 3" or "small team")
5. User metrics (percentages, dollar amounts, timeframes) are SACRED - preserve exactly
6. If evidence conflicts with user facts, ALWAYS trust the user
7. Create ONE cohesive narrative - not "user section + evidence section"

**INTEGRATION EXAMPLES:**

✅ CORRECT (Natural integration):
User: "I led a team of 5. I cooperate with physician, genomic expert, and data scientist."
Output: "Led a cross-functional team of 5, collaborating closely with physicians, genomic experts, and data scientists to design an ensemble machine learning framework..."
(Facts preserved: team of 5, specific roles. Language improved: professional tone, natural flow, integrated into narrative)

❌ INCORRECT (Standalone copy-paste):
User: "I led a team of 5. I cooperate with physician, genomic expert, and data scientist."
Output: "I led a team of 5. I cooperate with physician, genomic expert, and data scientist. [newline] On the AML project, I directed..."
(Too literal, awkward grammar, not integrated, separate sections)

**Your Task:**
Create a unified description (200-400 words) for "{artifact_title}" that:
- WEAVES user-provided facts naturally throughout the narrative (preserve numbers/metrics exactly, but improve grammar and flow)
- INTEGRATES them seamlessly with technical details from evidence
- Creates ONE flowing, professional paragraph - NOT separate user + evidence sections
- NEVER contradicts or dilutes user-stated achievements
- Maintains professional CV/resume tone

Return ONLY the unified description, no preamble or explanation."""
        else:
            # No user context - use traditional evidence-based generation
            description_section = ""
            if has_description:
                description_section = f"\nOriginal Description: {artifact_description}\n"

            unification_prompt = f"""Create a comprehensive, professional description for this project/artifact by unifying information from multiple sources.

Artifact Title: {artifact_title}{description_section}
Content from {len(extracted_contents)} sources:

{chr(10).join(source_summaries)}

Generate a unified, coherent description (200-400 words) that:
1. Combines insights from all evidence sources
2. Highlights key technologies and frameworks used
3. Emphasizes quantifiable achievements and impact
4. Maintains a professional tone
5. Is optimized for CV/resume use

Return ONLY the unified description, no preamble."""
        
        # # Log unification attempt
        # logger.info(
        #     f"[Unification] Starting content unification for artifact '{artifact_title}' "
        #     f"with {len(source_summaries)} successful sources, prompt length: {len(unification_prompt)} chars"
        # )
        # logger.warning(f"[Unification] Full prompt: {unification_prompt[:500]}...")

        # Call LLM using base service method
        response = await self._execute_llm_task(
            task_type='content_unification',
            context={
                'model_name': 'gpt-5',
                'max_tokens': GPT5_UNIFICATION_MAX_TOKENS,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a professional content unification assistant. Create comprehensive descriptions from multiple data sources.'
                    },
                    {
                        'role': 'user',
                        'content': unification_prompt
                    }
                ]
            },
            user_id=user_id
        )

        # Check response and handle errors
        logger.info(f"[Unification] Response type: {type(response)}, keys: {response.keys() if isinstance(response, dict) else 'N/A'}")

        if 'error' in response:
            error_msg = response.get('error', 'Unknown error')
            error_details = response.get('error_details', {})
            logger.error(
                f"[Unification] LLM call failed for artifact '{artifact_title}': {error_msg}. "
                f"Details: {error_details.get('original_error', 'No details')}"
            )
            # Use fallback description
            unified_description = f"{artifact_title}. {artifact_description or 'A professional project'}"
            logger.warning(f"[Unification] Using fallback description: {unified_description[:100]}...")
        else:
            unified_description = response.get('content', '').strip()

            if not unified_description:
                logger.warning(
                    f"[Unification] Empty content returned for artifact '{artifact_title}'. "
                    f"Response: {response}"
                )
                # Create fallback from artifact metadata
                unified_description = f"{artifact_title}. {artifact_description or 'A professional project'}"
                logger.info(f"[Unification] Using fallback: {unified_description[:100]}...")
            else:
                logger.info(
                    f"[Unification] Successfully unified content for '{artifact_title}'. "
                    f"Length: {len(unified_description)} chars"
                )

        return unified_description.strip()

    async def extract_and_merge_technologies(self,
                                           extracted_contents: List[ExtractedContent],
                                           user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Deduplicate and normalize technologies from all sources using LLM-based semantic grouping.

        ft-030 HIGH-PRECISION: Preserves confidence scores and filters by confidence >= 0.8.

        Returns:
            List of dicts with format: [{"name": "Django", "confidence": 0.95}, ...]
        """
        # Dict to track highest confidence per technology name
        tech_confidence_map: Dict[str, float] = {}

        for ec in extracted_contents:
            if ec.success and 'technologies' in ec.data:
                technologies = ec.data['technologies']
                # ft-030 HIGH-PRECISION: Preserve confidence scores
                for tech in technologies:
                    if isinstance(tech, str):
                        # Legacy format (no attribution) - treat as low confidence (0.0)
                        # Will be filtered out by >= 0.8 threshold
                        tech_name = tech
                        confidence = 0.0
                        logger.debug(f"[ft-030] Legacy tech string '{tech}' has no confidence (0.0)")
                    elif isinstance(tech, dict) and 'name' in tech:
                        # AttributedTechnology format: {"name": "Django", "source_attribution": {...}}
                        tech_name = tech['name']
                        attribution = tech.get('source_attribution', {})
                        confidence = attribution.get('confidence', 0.0)
                    else:
                        logger.warning(f"Unexpected technology format: {type(tech)}")
                        continue

                    # Keep highest confidence per technology name
                    if tech_name in tech_confidence_map:
                        tech_confidence_map[tech_name] = max(tech_confidence_map[tech_name], confidence)
                    else:
                        tech_confidence_map[tech_name] = confidence

        if not tech_confidence_map:
            return []

        # ft-030 HIGH-PRECISION: Filter by confidence >= 0.8
        high_confidence_techs = {
            name: conf for name, conf in tech_confidence_map.items() if conf >= 0.8
        }

        if not high_confidence_techs:
            logger.warning(
                f"[ft-030 HIGH-PRECISION] No technologies passed confidence >= 0.8 threshold "
                f"(filtered {len(tech_confidence_map)}/{len(tech_confidence_map)})"
            )
            return []

        logger.info(
            f"[ft-030 HIGH-PRECISION] {len(high_confidence_techs)}/{len(tech_confidence_map)} "
            f"technologies passed confidence >= 0.8 threshold"
        )

        # First pass: basic normalization using mapping
        tech_names = list(high_confidence_techs.keys())
        normalized = await self.content_extractor.normalize_technologies(tech_names)

        # Build normalized confidence map
        normalized_confidence_map: Dict[str, float] = {}
        for original, normalized_name in zip(tech_names, normalized):
            original_conf = high_confidence_techs[original]
            if normalized_name in normalized_confidence_map:
                # Keep highest confidence for duplicates
                normalized_confidence_map[normalized_name] = max(
                    normalized_confidence_map[normalized_name],
                    original_conf
                )
            else:
                normalized_confidence_map[normalized_name] = original_conf

        # Get top 30 candidates by confidence (we'll deduplicate these with LLM)
        sorted_techs = sorted(
            normalized_confidence_map.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_candidates = [name for name, conf in sorted_techs[:30]]
        top_confidences = {name: conf for name, conf in sorted_techs[:30]}

        # If we have few technologies, no need for LLM deduplication
        if len(top_candidates) <= 10:
            return [
                {"name": name, "confidence": top_confidences[name]}
                for name in top_candidates
            ]

        # Second pass: Use LLM to deduplicate semantic variants
        deduplicated_names = await self._llm_deduplicate_technologies(top_candidates, user_id)

        # Return top 20 with confidence scores preserved
        result = []
        for name in deduplicated_names[:20]:
            confidence = top_confidences.get(name, 0.8)  # Default to threshold if missing
            result.append({"name": name, "confidence": confidence})

        return result

    async def _llm_deduplicate_technologies(self,
                                           technologies: List[str],
                                           user_id: Optional[int] = None) -> List[str]:
        """
        Use LLM to identify and merge duplicate/variant technology names.

        Examples:
        - "React", "React.js", "ReactJS" → "React"
        - "PostgreSQL", "Postgres" → "PostgreSQL"
        - "Node.js", "NodeJS" → "Node.js"
        """
        if len(technologies) <= 5:
            return technologies

        dedup_prompt = f"""Given this list of technologies extracted from multiple sources, identify and remove duplicates/variants.

Technologies: {', '.join(technologies)}

Rules:
1. Merge semantic variants (e.g., "React", "React.js", "ReactJS" → "React")
2. Keep the most common/official name (e.g., "PostgreSQL" not "Postgres")
3. Preserve version numbers if present (e.g., "React 18")
4. Don't merge different technologies (e.g., "React" and "React Native" are different)

Return ONLY a JSON array of deduplicated technology names, ordered by importance/commonality:
["tech1", "tech2", "tech3", ...]"""

        try:
            # Use _execute_llm_task for circuit breaker, retries, and performance tracking
            context = {
                'prompt': dedup_prompt,
                'task_type': 'tech_deduplication'
            }

            result = await self._execute_llm_task(
                task_type='tech_deduplication',
                context=context,
                user_id=user_id
            )

            # Extract content from result
            content = result.get('content', '')

            # Parse JSON
            try:
                # Try direct JSON parse
                deduplicated = json.loads(content)
                if isinstance(deduplicated, list):
                    return deduplicated
            except json.JSONDecodeError:
                # Try extracting from markdown code blocks
                match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
                if match:
                    deduplicated = json.loads(match.group(1))
                    return deduplicated

                # Try finding array
                start_idx = content.find('[')
                end_idx = content.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    deduplicated = json.loads(content[start_idx:end_idx + 1])
                    return deduplicated

        except Exception as e:
            logger.warning(f"LLM deduplication failed: {e}, returning original list")

        # Fallback: return original list
        return technologies

    async def extract_and_rank_achievements(self,
                                          extracted_contents: List[ExtractedContent],
                                          user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract achievements from all sources and rank by impact using LLM-based quality assessment.

        ft-030: Handles both old format (strings) and new format (attributed objects).
        """
        all_achievements = []

        for ec in extracted_contents:
            if ec.success and 'achievements' in ec.data:
                achievements = ec.data['achievements']
                quantified_metrics = ec.data.get('metrics', [])

                for achievement in achievements:
                    # ft-030: Extract achievement text from attributed or string format
                    if isinstance(achievement, str):
                        achievement_text = achievement
                    elif isinstance(achievement, dict) and 'text' in achievement:
                        # AttributedAchievement format
                        achievement_text = achievement['text']
                    else:
                        logger.warning(f"Unexpected achievement format: {type(achievement)}")
                        continue

                    all_achievements.append({
                        'achievement': achievement_text,
                        'source': ec.source_type,
                        'metrics': quantified_metrics
                    })

        if not all_achievements:
            return []

        # If we have few achievements, use simple heuristic
        if len(all_achievements) <= 5:
            return await self._heuristic_rank_achievements(all_achievements)

        # Use LLM to rank achievements by impact
        ranked_achievements = await self._llm_rank_achievements(all_achievements, user_id)

        # Return top 10
        return ranked_achievements[:10]

    async def _heuristic_rank_achievements(self,
                                          achievements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback heuristic ranking when LLM ranking isn't needed or fails.
        """
        for item in achievements:
            achievement = item['achievement']

            # Calculate impact score based on presence of metrics
            impact_score = 0.5

            # Boost if contains percentages
            if '%' in achievement:
                impact_score += 0.2

            # Boost if contains numbers (more flexible pattern)
            if re.search(r'\d{2,}', achievement):  # 2+ digit numbers
                impact_score += 0.15

            # Boost if contains k/M/B multipliers
            if re.search(r'\d+[kKmMbB]', achievement):
                impact_score += 0.2

            # Boost if contains monetary values
            if '$' in achievement:
                impact_score += 0.1

            item['impact_score'] = min(1.0, impact_score)

        # Sort by impact score
        achievements.sort(key=lambda x: x['impact_score'], reverse=True)
        return achievements

    async def _llm_rank_achievements(self,
                                    achievements: List[Dict[str, Any]],
                                    user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Use LLM to rank achievements by CV impact and quality.

        Filters out non-achievements (features) and ranks by measurable impact.
        """
        # Extract just the achievement text for ranking
        achievement_texts = [item['achievement'] for item in achievements]

        ranking_prompt = f"""You are a professional resume writer. Rank these achievements by their impact and quality for a CV/resume.

Achievements to rank:
{chr(10).join([f"{i+1}. {ach}" for i, ach in enumerate(achievement_texts)])}

Ranking criteria (in order of importance):
1. Has specific, quantified metrics (percentages, numbers, scale)
2. Shows clear business/technical impact
3. Is an achievement, not a feature or task
4. Uses strong action verbs and clear outcomes
5. Is specific and concrete, not vague

Return a JSON array of achievement indices in ranked order (best first), with quality scores:
[
  {{"index": 0, "score": 0.95, "reason": "Strong quantified impact"}},
  {{"index": 3, "score": 0.80, "reason": "Good metrics but less impact"}},
  ...
]

Include ALL achievements. Score range: 0.0-1.0. Exclude any that are clearly features/tasks (not achievements) by giving them score < 0.3."""

        try:
            # Use _execute_llm_task for circuit breaker, retries, and performance tracking
            context = {
                'prompt': ranking_prompt,
                'task_type': 'achievement_ranking'
            }

            result = await self._execute_llm_task(
                task_type='achievement_ranking',
                context=context,
                user_id=user_id
            )

            # Extract content from result
            content = result.get('content', '')

            # Parse JSON
            ranked_list = None
            try:
                ranked_list = json.loads(content)
            except json.JSONDecodeError:
                # Try extracting from markdown code blocks
                match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
                if match:
                    ranked_list = json.loads(match.group(1))
                else:
                    # Try finding array
                    start_idx = content.find('[')
                    end_idx = content.rfind(']')
                    if start_idx != -1 and end_idx != -1:
                        ranked_list = json.loads(content[start_idx:end_idx + 1])

            if ranked_list and isinstance(ranked_list, list):
                # Reconstruct achievements in ranked order with scores
                ranked_achievements = []
                for item in ranked_list:
                    if isinstance(item, dict) and 'index' in item and 'score' in item:
                        idx = item['index']
                        score = item['score']

                        # Filter out low-quality (< 0.3 means it's a feature, not achievement)
                        if score >= 0.3 and 0 <= idx < len(achievements):
                            achievement_data = achievements[idx].copy()
                            achievement_data['impact_score'] = score
                            ranked_achievements.append(achievement_data)

                return ranked_achievements

        except Exception as e:
            logger.warning(f"LLM achievement ranking failed: {e}, falling back to heuristic")

        # Fallback to heuristic ranking
        return await self._heuristic_rank_achievements(achievements)

    async def calculate_overall_confidence(self,
                                         extracted_contents: List[ExtractedContent],
                                         unified_description: str) -> float:
        """
        Calculate overall preprocessing confidence score.
        """
        if not extracted_contents:
            return 0.3

        # Count successful extractions
        successful = [ec for ec in extracted_contents if ec.success]
        success_rate = len(successful) / len(extracted_contents)

        # Calculate average confidence from successful extractions
        if successful:
            avg_confidence = sum(ec.confidence for ec in successful) / len(successful)
        else:
            avg_confidence = 0.0

        # Boost if unified description is substantial
        description_boost = 0.1 if len(unified_description) > 200 else 0.0

        # Weighted calculation
        overall_confidence = (success_rate * 0.4) + (avg_confidence * 0.5) + description_boost

        return min(1.0, overall_confidence)

    async def generate_unified_embedding(self,
                                       unified_description: str,
                                       technologies: List[str],
                                       user_id: Optional[int] = None) -> Optional[List[float]]:
        """
        DEPRECATED (ft-007): Embedding generation removed.

        Returns None as we're using keyword-only ranking now.
        This method is kept for backward compatibility but does nothing.
        """
        # ft-007: Embeddings removed, using keyword-only ranking
        return None

    async def reunify_from_accepted_evidence(
        self,
        artifact_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Re-unify artifact content from user-accepted and edited evidence (ft-045).

        Reads from EnhancedEvidence.processed_content (user-edited) instead of
        ExtractedContent, uses LLM to generate professional narrative, updates
        Artifact fields with unified content.

        Args:
            artifact_id: Artifact ID to re-unify
            user_id: User ID for tracking

        Returns:
            {
                'artifact_id': int,
                'unified_description': str,
                'enriched_technologies': List[str],
                'enriched_achievements': List[str],
                'processing_confidence': float,
                'evidence_acceptance_summary': AcceptanceStatus
            }

        Raises:
            ArtifactNotFoundError: If artifact does not exist
            LLMError: If re-unification fails (fallback to concatenation)
        """
        from artifacts.models import Artifact
        from asgiref.sync import sync_to_async

        # 1. Fetch artifact and accepted evidence
        try:
            artifact = await sync_to_async(Artifact.objects.get)(id=artifact_id)
        except Artifact.DoesNotExist:
            raise ArtifactNotFoundError(f"Artifact {artifact_id} not found")

        accepted_evidence = await sync_to_async(list)(
            EnhancedEvidence.objects.filter(
                evidence__artifact=artifact,
                accepted=True
            ).select_related('evidence')
        )

        if not accepted_evidence:
            logger.warning(f"[reunify] No accepted evidence for artifact {artifact_id}")
            # Return artifact fields unchanged
            return {
                'artifact_id': artifact.id,
                'unified_description': artifact.description or f"{artifact.title}. No accepted evidence.",
                'enriched_technologies': artifact.enriched_technologies or [],
                'enriched_achievements': artifact.enriched_achievements or [],
                'processing_confidence': 0.5,
                'evidence_acceptance_summary': {
                    'total_evidence': 0,
                    'accepted': 0,
                    'rejected': 0,
                    'pending': 0,
                    'can_finalize': True
                }
            }

        # 2. Build source summaries from user-edited processed_content
        source_summaries = []
        for enhanced_ev in accepted_evidence:
            summary = f"Source: {enhanced_ev.title} ({enhanced_ev.content_type})\n"

            # Use user-edited processed_content (not raw_content)
            pc = enhanced_ev.processed_content or {}

            if pc.get('technologies'):
                techs = pc['technologies'][:10]  # Limit to 10
                summary += f"Technologies: {', '.join(techs)}\n"

            if pc.get('achievements'):
                achs = pc['achievements'][:5]  # Limit to 5
                summary += f"Achievements: {', '.join(achs)}\n"

            if pc.get('summary'):
                summary += f"Summary: {pc['summary']}\n"

            source_summaries.append(summary)

        # 3. Call LLM with similar prompt to unify_content_with_llm
        # Reuse ft-018 prompt pattern (user_context as immutable ground truth)
        has_user_context = artifact.user_context and artifact.user_context.strip()

        if has_user_context:
            # User context exists - treat as IMMUTABLE (same as unify_content_with_llm)
            unification_prompt = f"""You are creating a professional CV/resume description. You MUST follow this strict hierarchy:

**GROUND TRUTH (User-Provided Facts - IMMUTABLE):**
{artifact.user_context.strip()}

**USER-ACCEPTED EVIDENCE (Already reviewed and corrected by user):**
{chr(10).join(source_summaries)}

**CRITICAL RULES:**
1. User-provided FACTS are ABSOLUTE TRUTH - preserve all numbers, team sizes, metrics, roles EXACTLY
2. Evidence has been reviewed and corrected by user - trust this content
3. INTEGRATE facts naturally into flowing narrative - DO NOT copy-paste as standalone sentences
4. Create ONE cohesive narrative - not "user section + evidence section"
5. Maintain professional CV/resume tone

**Your Task:**
Create a unified description (200-400 words) for "{artifact.title}" that:
- WEAVES user-provided facts naturally throughout the narrative
- INTEGRATES them seamlessly with user-corrected evidence details
- Creates ONE flowing, professional paragraph
- Maintains professional CV/resume tone

Return ONLY the unified description, no preamble or explanation."""
        else:
            # No user context - use traditional evidence-based generation
            description_section = ""
            if artifact.description and artifact.description.strip():
                description_section = f"\nOriginal Description: {artifact.description}\n"

            unification_prompt = f"""Create a comprehensive, professional description for this project/artifact from USER-ACCEPTED EVIDENCE.

Artifact Title: {artifact.title}{description_section}

USER-ACCEPTED EVIDENCE (Already reviewed and corrected):
{chr(10).join(source_summaries)}

Generate a unified, coherent description (200-400 words) that:
1. Combines insights from all user-accepted evidence
2. Highlights key technologies and frameworks
3. Emphasizes quantifiable achievements and impact
4. Maintains professional tone
5. Is optimized for CV/resume use

Return ONLY the unified description, no preamble."""

        # Call LLM using base service method
        try:
            response = await self._execute_llm_task(
                task_type='content_unification',
                context={
                    'model_name': 'gpt-5',
                    'max_tokens': GPT5_UNIFICATION_MAX_TOKENS,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a professional content unification assistant. Create comprehensive descriptions from multiple data sources.'
                        },
                        {
                            'role': 'user',
                            'content': unification_prompt
                        }
                    ]
                },
                user_id=user_id
            )

            if 'error' in response:
                # LLM failed - use fallback
                logger.error(f"[reunify] LLM failed for artifact {artifact_id}: {response.get('error')}")
                unified_description = self._fallback_concatenation(accepted_evidence, artifact.title)
            else:
                unified_description = response.get('content', '').strip()
                if not unified_description:
                    logger.warning(f"[reunify] Empty LLM response for artifact {artifact_id}")
                    unified_description = self._fallback_concatenation(accepted_evidence, artifact.title)

        except Exception as e:
            logger.error(f"[reunify] Exception during LLM call for artifact {artifact_id}: {e}")
            unified_description = self._fallback_concatenation(accepted_evidence, artifact.title)

        # 4. Extract technologies and achievements
        technologies = self._extract_reunified_technologies(accepted_evidence)
        achievements = self._extract_reunified_achievements(accepted_evidence)
        confidence = self._calculate_reunification_confidence(accepted_evidence)

        # 5. Update artifact fields
        artifact.unified_description = unified_description
        artifact.enriched_technologies = technologies
        artifact.enriched_achievements = achievements
        artifact.processing_confidence = confidence
        await sync_to_async(artifact.save)()

        logger.info(f"[reunify] Successfully re-unified artifact {artifact_id} from {len(accepted_evidence)} accepted evidence")

        # 6. Build acceptance summary
        total_evidence_count = await sync_to_async(
            EnhancedEvidence.objects.filter(evidence__artifact=artifact).count
        )()

        return {
            'artifact_id': artifact.id,
            'unified_description': unified_description,
            'enriched_technologies': technologies,
            'enriched_achievements': achievements,
            'processing_confidence': confidence,
            'evidence_acceptance_summary': {
                'total_evidence': total_evidence_count,
                'accepted': len(accepted_evidence),
                'rejected': 0,  # Calculated by view
                'pending': total_evidence_count - len(accepted_evidence),
                'can_finalize': True  # If we got here, it means all evidence was accepted
            }
        }

    def _extract_reunified_technologies(self, accepted_evidence: List[EnhancedEvidence]) -> List[str]:
        """
        Extract unique technologies from user-edited processed_content.

        Args:
            accepted_evidence: List of accepted EnhancedEvidence records

        Returns:
            Deduplicated list of technology names
        """
        tech_set = set()
        for evidence in accepted_evidence:
            pc = evidence.processed_content or {}
            if pc.get('technologies'):
                tech_set.update(pc['technologies'])

        return sorted(list(tech_set))

    def _extract_reunified_achievements(self, accepted_evidence: List[EnhancedEvidence]) -> List[str]:
        """
        Extract unique achievements from user-edited processed_content.

        Args:
            accepted_evidence: List of accepted EnhancedEvidence records

        Returns:
            List of achievement strings (max 10)
        """
        achievements = []
        for evidence in accepted_evidence:
            pc = evidence.processed_content or {}
            if pc.get('achievements'):
                achievements.extend(pc['achievements'])

        return achievements[:10]  # Limit to top 10

    def _calculate_reunification_confidence(self, accepted_evidence: List[EnhancedEvidence]) -> float:
        """
        Calculate processing confidence from user-accepted evidence.

        User acceptance implies high confidence (user verified content).
        Formula: average original processing_confidence + 0.1 user acceptance bonus

        Args:
            accepted_evidence: List of accepted EnhancedEvidence records

        Returns:
            Confidence score (0.0-1.0)
        """
        if not accepted_evidence:
            return 0.0

        # Average original processing_confidence scores
        avg_confidence = sum(e.processing_confidence for e in accepted_evidence) / len(accepted_evidence)

        # Add 0.1 bonus for user acceptance (users verified content)
        user_acceptance_bonus = 0.1

        # Cap at 1.0
        return min(1.0, avg_confidence + user_acceptance_bonus)

    def _fallback_concatenation(self, accepted_evidence: List[EnhancedEvidence], title: str) -> str:
        """
        Fallback concatenation when LLM re-unification fails.

        Args:
            accepted_evidence: List of accepted EnhancedEvidence records
            title: Artifact title

        Returns:
            Concatenated description from evidence summaries
        """
        if not accepted_evidence:
            return f"{title}. No accepted evidence available."

        summaries = []
        for evidence in accepted_evidence:
            pc = evidence.processed_content or {}
            if pc.get('summary'):
                summaries.append(pc['summary'])

        if summaries:
            return f"{title}. " + " ".join(summaries)
        else:
            return f"{title}. Evidence content available but no summaries extracted."

    def _build_task_function(self, task_type: str):
        """Build task-specific functions for unified task executor"""

        if task_type == 'content_unification':
            async def unification_task(model: str, context: Dict[str, Any]):
                """Execute content unification with LLM"""
                # Extract parameters from context
                messages = context['messages']
                max_tokens = context.get('max_tokens', 2000)

                # Build kwargs for API call
                call_kwargs = {'max_tokens': max_tokens}

                # Pass through GPT-5 specific parameters if present
                if 'reasoning_effort' in context:
                    call_kwargs['reasoning_effort'] = context['reasoning_effort']
                if 'verbosity' in context:
                    call_kwargs['verbosity'] = context['verbosity']

                # Make LLM call
                response = await self.client_manager.make_completion_call(
                    model=model,
                    messages=messages,
                    **call_kwargs
                )

                # Extract content from response
                content = ''
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                elif isinstance(response, dict) and 'choices' in response:
                    content = response['choices'][0]['message']['content']

                # Build result with usage metadata
                result = {
                    'content': content.strip()
                }

                # Add usage information for cost tracking
                if hasattr(response, 'usage'):
                    result['usage'] = response.usage
                elif isinstance(response, dict) and 'usage' in response:
                    result['usage'] = response['usage']

                return result

            return unification_task

        elif task_type == 'tech_deduplication':
            async def tech_dedup_task(model: str, context: Dict[str, Any]):
                """Execute technology deduplication with LLM"""
                prompt = context['prompt']

                response = await self.client_manager.make_completion_call(
                    model=model,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You are an expert at normalizing technology names and identifying duplicates.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    temperature=0.1,  # Very low for consistency
                    max_tokens=500
                )

                # Extract content from response
                content = ''
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                elif isinstance(response, dict) and 'choices' in response:
                    content = response['choices'][0]['message']['content']

                # Build result with usage metadata
                result = {
                    'content': content
                }

                # Add usage information for cost tracking
                if hasattr(response, 'usage'):
                    result['usage'] = response.usage
                elif isinstance(response, dict) and 'usage' in response:
                    result['usage'] = response['usage']

                return result

            return tech_dedup_task

        elif task_type == 'achievement_ranking':
            async def achievement_ranking_task(model: str, context: Dict[str, Any]):
                """Execute achievement ranking with LLM"""
                prompt = context['prompt']

                response = await self.client_manager.make_completion_call(
                    model=model,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You are an expert resume writer who evaluates achievement quality and impact.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    temperature=0.2,  # Low temperature for consistency
                    max_tokens=1000
                )

                # Extract content from response
                content = ''
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                elif isinstance(response, dict) and 'choices' in response:
                    content = response['choices'][0]['message']['content']

                # Build result with usage metadata
                result = {
                    'content': content
                }

                # Add usage information for cost tracking
                if hasattr(response, 'usage'):
                    result['usage'] = response.usage
                elif isinstance(response, dict) and 'usage' in response:
                    result['usage'] = response['usage']

                return result

            return achievement_ranking_task

        # Return None for unknown task types (default behavior)
        return None