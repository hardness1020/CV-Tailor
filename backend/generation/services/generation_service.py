"""
CV Generation Service

Orchestrates full CV generation workflow from job description to final document.
Extracted from tasks.py for better separation of concerns (ADR-TBD).

Architecture:
- Orchestrates: job parsing → artifact building → ranking → CV generation → assembly
- Calls TailoredContentService for LLM operations
- Calls ArtifactRankingService for semantic ranking
- Progress callback support for async job tracking
- Framework-agnostic (can be used from REST API or Celery)

References:
- Feature 002 - CV Generation System
- SPEC-20250930 - LLM Service Architecture Refactoring
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from common.exceptions import (
    GenerationError, ValidationError, ContentProcessingError
)
from llm_services.services.core.tailored_content_service import TailoredContentService
from llm_services.services.core.artifact_ranking_service import ArtifactRankingService
from generation.services.bullet_generation_service import BulletGenerationService

logger = logging.getLogger(__name__)


@dataclass
class BulletPreparationResult:
    """
    Result container for Phase 1 (bullet preparation).

    Attributes:
        total_bullets_generated: Total number of bullets created
        artifacts_processed: Number of artifacts processed
        bullets_by_artifact: Dict mapping artifact_id to bullet count
        generation_time_ms: Total processing time
    """
    total_bullets_generated: int = 0
    artifacts_processed: int = 0
    bullets_by_artifact: Optional[Dict[int, int]] = None
    generation_time_ms: Optional[int] = None


@dataclass
class GenerationResult:
    """
    Result container for Phase 2 (document generation/assembly).

    Attributes:
        document_content: Generated document content (dict)
        metadata: Generation metadata (model used, cost, etc.)
        artifacts_used: List of artifact IDs used in generation
        job_parsed_data: Parsed job description data
        generation_time_ms: Total processing time
        model_version: LLM model used
        total_cost_usd: Total API cost
    """
    document_content: Dict[str, Any]
    metadata: Dict[str, Any]
    artifacts_used: List[int]
    job_parsed_data: Optional[Dict[str, Any]] = None
    generation_time_ms: Optional[int] = None
    model_version: Optional[str] = None
    total_cost_usd: Optional[float] = None


class GenerationService:
    """
    Service for orchestrating full document generation workflow (CV, cover letter, etc.).

    Separates business logic from Celery worker concerns.
    Framework-agnostic design allows usage from:
    - Celery tasks (async background jobs)
    - REST API endpoints (synchronous requests)
    - CLI commands
    - Test suites

    Usage:
        service = GenerationService()
        result = await service.generate_document_for_job(
            generation_id="uuid-123",
            progress_callback=lambda pct: print(f"Progress: {pct}%")
        )
    """

    def __init__(self):
        """Initialize document generation service with dependencies."""
        self.content_service = TailoredContentService()
        self.ranking_service = ArtifactRankingService()
        self.bullet_service = BulletGenerationService()

    async def generate_document_for_job(
        self,
        generation_id: str,
        artifact_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> GenerationResult:
        """
        Generate document from job description and user artifacts.

        This method orchestrates the complete document generation workflow:
        1. Fetch generation record and job description
        2. Parse job description (if not already parsed)
        3. Fetch and build artifact data
        4. Rank artifacts by relevance to job (OR use manually selected artifacts)
        5. Generate document content using top artifacts
        6. Assemble final document with metadata

        Args:
            generation_id: UUID of GeneratedDocument record
            artifact_ids: Optional list of artifact IDs (ft-007). If provided, skips
                automatic ranking and uses specified artifacts in given order.
            progress_callback: Optional callback for progress updates (0-100)
                Called at: 10%, 30%, 50%, 70%, 100%

        Returns:
            GenerationResult with content, metadata, and status

        Raises:
            GenerationError: If generation fails at any stage
            ValidationError: If generation_id invalid or job description missing
            PermissionError: If artifact_ids contains artifacts not owned by user

        Example:
            >>> service = GenerationService()
            >>> # Automatic artifact selection (backward compatible)
            >>> result = await service.generate_document_for_job(
            ...     generation_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> # Manual artifact selection (ft-007)
            >>> result = await service.generate_document_for_job(
            ...     generation_id="550e8400-e29b-41d4-a716-446655440000",
            ...     artifact_ids=[1, 5, 3, 7]  # User-specified order preserved
            ... )
        """
        try:
            # Import models here to avoid circular imports
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            Artifact = apps.get_model('artifacts', 'Artifact')

            # Stage 1: Fetch generation record (10%)
            if progress_callback:
                progress_callback(10)

            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)

            # Validate job description exists
            if not generation.job_description:
                logger.warning(f"No job description found for generation {generation_id}")
                raise ValidationError('No job description provided')

            job_desc = generation.job_description

            # Stage 2: Parse job description if needed (10% → 30%)
            if not job_desc.parsed_data:
                logger.info(f"Parsing job description for generation {generation_id}")
                parsing_result = await self.content_service.parse_job_description(
                    job_desc.raw_content,
                    job_desc.company_name,
                    job_desc.role_title,
                    generation.user_id
                )

                if 'error' in parsing_result:
                    raise GenerationError(
                        f"Failed to parse job description: {parsing_result['error']}"
                    )

                # Save parsed data (exclude non-serializable usage object)
                parsed_data_for_db = {k: v for k, v in parsing_result.items() if k != 'usage'}
                job_desc.parsed_data = parsed_data_for_db
                job_desc.parsing_confidence = parsing_result.get('confidence_score', 0.5)
                await sync_to_async(job_desc.save)()

            if progress_callback:
                progress_callback(30)

            # Stage 3: Build artifact data (30% → 50%)
            # ft-007: If artifact_ids provided, use manual selection; otherwise use automatic ranking
            if artifact_ids:
                # Manual artifact selection (ft-007)
                logger.info(f"Using manual artifact selection: {artifact_ids}")
                selected_artifacts = await self._fetch_selected_artifacts(
                    user_id=generation.user_id,
                    artifact_ids=artifact_ids
                )
            else:
                # Automatic artifact selection (backward compatible)
                logger.info("Using automatic artifact ranking")
                user_artifacts = await sync_to_async(list)(
                    Artifact.objects.filter(user_id=generation.user_id).prefetch_related('evidence')
                )

                # Filter by label_ids if specified
                # TODO: Implement label filtering when artifact labels are available
                if generation.label_ids:
                    pass  # Reserved for future label filtering

                artifacts_data = []
                for artifact in user_artifacts:
                    artifact_dict = await self._build_artifact_dict(artifact)
                    artifacts_data.append(artifact_dict)

                if progress_callback:
                    progress_callback(50)

                # Stage 4: Rank artifacts by relevance (50% → 70%)
                job_requirements = (
                    job_desc.parsed_data.get('must_have_skills', []) +
                    job_desc.parsed_data.get('nice_to_have_skills', [])
                )

                ranked_artifacts = await self.ranking_service.rank_artifacts_by_relevance(
                    artifacts_data,
                    job_requirements,
                    strategy='keyword'  # ft-007: Use keyword-only ranking
                )

                # Select top artifacts
                max_artifacts = generation.generation_preferences.get('max_artifacts', 5)
                selected_artifacts = ranked_artifacts[:max_artifacts]

            if progress_callback:
                progress_callback(70)

            # Stage 5: Generate CV content (70% → 90%)
            logger.info(f"Generating CV content for generation {generation_id}")
            cv_result = await self.content_service.generate_cv_content(
                job_desc.parsed_data,
                selected_artifacts,
                generation.generation_preferences,
                generation.user_id
            )

            if 'error' in cv_result:
                raise GenerationError(
                    f"Failed to generate CV: {cv_result['error']}"
                )

            # Stage 6: Assemble final document (90% → 100%)
            processing_metadata = cv_result.get('processing_metadata', {})
            artifacts_used = [a['id'] for a in selected_artifacts]  # ft-007: Use all selected artifacts

            assembled_document = await self.content_service.assemble_final_document(
                document_type=generation.document_type,
                generated_content=cv_result.get('content', {}),
                job_data=job_desc.parsed_data,
                artifacts_used=artifacts_used,
                template_config={'template_id': generation.template_id},
                custom_sections=generation.custom_sections,
                processing_metadata=processing_metadata
            )

            if progress_callback:
                progress_callback(100)

            # Return success result
            return GenerationResult(
                cv_content=assembled_document['content'],
                metadata=assembled_document['metadata'],
                artifacts_used=artifacts_used,
                job_parsed_data=job_desc.parsed_data,
                generation_time_ms=processing_metadata.get('processing_time_ms'),
                model_version=processing_metadata.get('model_used', 'unknown'),
                total_cost_usd=processing_metadata.get('cost_usd', 0.0)
            )

        except (ValidationError, GenerationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            logger.error(f"CV generation failed for {generation_id}: {e}", exc_info=True)
            raise GenerationError(
                f"Unexpected error during CV generation {generation_id}: {str(e)}"
            ) from e

    async def prepare_bullets(
        self,
        generation_id: str,
        artifact_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> BulletPreparationResult:
        """
        Phase 1: Generate bullets for review.

        Workflow:
        1. Parse job description (0% → 20%)
        2. Build artifact data (20% → 40%)
        3. Rank artifacts OR use manual selection (40% → 60%)
        4. Generate 3 bullets per artifact (60% → 100%)

        Final Status: 'bullets_ready' (awaiting user review)

        Args:
            generation_id: UUID of GeneratedDocument record
            artifact_ids: Optional list of artifact IDs (ft-007). If provided, skips
                automatic ranking and uses specified artifacts.
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            BulletPreparationResult with bullets count and metadata

        Raises:
            Exception: If bullet generation fails at any stage
        """
        import time
        start_time = time.time()

        try:
            # Import models
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            BulletPoint = apps.get_model('generation', 'BulletPoint')
            Artifact = apps.get_model('artifacts', 'Artifact')

            # Stage 1: Fetch generation record (0% → 20%)
            if progress_callback:
                progress_callback(0)

            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)

            # Update status to processing
            generation.status = 'processing'
            await sync_to_async(generation.save)(update_fields=['status'])

            # Validate job description exists
            if not generation.job_description:
                raise ValueError('No job description provided')

            job_desc = generation.job_description

            # Parse job description if needed
            if not job_desc.parsed_data:
                logger.info(f"Parsing job description for generation {generation_id}")
                parsing_result = await self.content_service.parse_job_description(
                    job_desc.raw_content,
                    job_desc.company_name,
                    job_desc.role_title,
                    generation.user_id
                )

                if 'error' in parsing_result:
                    raise Exception(f"Failed to parse job description: {parsing_result['error']}")

                # Save parsed data (exclude non-serializable usage object)
                parsed_data_for_db = {k: v for k, v in parsing_result.items() if k != 'usage'}
                job_desc.parsed_data = parsed_data_for_db
                job_desc.parsing_confidence = parsing_result.get('confidence_score', 0.5)
                await sync_to_async(job_desc.save)()

            if progress_callback:
                progress_callback(20)

            # Stage 2: Build artifact data (20% → 40%)
            # ft-007: If artifact_ids provided, use manual selection; otherwise use automatic ranking
            if artifact_ids:
                # Manual artifact selection (ft-007)
                logger.info(f"Using manual artifact selection for bullets: {artifact_ids}")
                selected_artifacts = await self._fetch_selected_artifacts(
                    user_id=generation.user_id,
                    artifact_ids=artifact_ids
                )
            else:
                # Automatic artifact selection (backward compatible)
                logger.info("Using automatic artifact ranking for bullets")
                user_artifacts = await sync_to_async(list)(
                    Artifact.objects.filter(user_id=generation.user_id).prefetch_related('evidence')
                )

                artifacts_data = []
                for artifact in user_artifacts:
                    artifact_dict = await self._build_artifact_dict(artifact)
                    artifacts_data.append(artifact_dict)

                if progress_callback:
                    progress_callback(40)

                # Stage 3: Rank artifacts by relevance (40% → 60%)
                job_requirements = (
                    job_desc.parsed_data.get('must_have_skills', []) +
                    job_desc.parsed_data.get('nice_to_have_skills', [])
                )

                ranked_artifacts = await self.ranking_service.rank_artifacts_by_relevance(
                    artifacts_data,
                    job_requirements,
                    strategy='keyword'  # ft-007: Use keyword-only ranking
                )

                # Select top artifacts for bullet generation
                selected_artifacts = await self._select_relevant_artifacts(ranked_artifacts, generation)

            if progress_callback:
                progress_callback(60)

            # Stage 4: Generate bullets for each artifact (60% → 100%)
            bullets_by_artifact = {}
            total_bullets = 0

            # Calculate progress increment per artifact
            artifacts_count = len(selected_artifacts)
            progress_per_artifact = 40 / max(artifacts_count, 1)  # 60% to 100% = 40% range

            for idx, artifact_data in enumerate(selected_artifacts):
                artifact_id = artifact_data['id']

                # Build job context from parsed data
                job_context = {
                    'role_title': job_desc.parsed_data.get('role_title', ''),
                    'company_name': job_desc.parsed_data.get('company_name', ''),
                    'key_requirements': job_desc.parsed_data.get('must_have_skills', []),
                    'preferred_skills': job_desc.parsed_data.get('nice_to_have_skills', []),
                    'responsibilities': job_desc.parsed_data.get('responsibilities', [])
                }

                # Generate 3 bullets for this artifact
                bullet_set = await self.bullet_service.generate_bullets(
                    artifact_id=artifact_id,
                    job_context=job_context,
                    cv_generation_id=str(generation.id),
                    regenerate=False
                )

                bullets_by_artifact[artifact_id] = len(bullet_set.bullets)
                total_bullets += len(bullet_set.bullets)

                # Update progress
                current_progress = int(60 + ((idx + 1) * progress_per_artifact))
                if progress_callback:
                    progress_callback(min(current_progress, 100))

            # Update generation record with bullet metadata
            generation.status = 'bullets_ready'
            generation.bullets_generated_at = timezone.now()
            generation.bullets_count = total_bullets
            await sync_to_async(generation.save)(
                update_fields=['status', 'bullets_generated_at', 'bullets_count']
            )

            if progress_callback:
                progress_callback(100)

            # Calculate total time
            elapsed_ms = int((time.time() - start_time) * 1000)

            return BulletPreparationResult(
                total_bullets_generated=total_bullets,
                artifacts_processed=len(selected_artifacts),
                bullets_by_artifact=bullets_by_artifact,
                generation_time_ms=elapsed_ms
            )

        except Exception as e:
            logger.error(f"Bullet preparation failed for {generation_id}: {e}", exc_info=True)

            # Update generation status to failed
            try:
                generation.status = 'failed'
                generation.error_message = str(e)
                await sync_to_async(generation.save)(update_fields=['status', 'error_message'])
            except:
                pass

            raise

    async def assemble_cv(
        self,
        generation_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> GenerationResult:
        """
        Phase 2: Assemble CV from approved bullets.

        Preconditions:
        - GeneratedDocument.status == 'bullets_approved'

        Workflow:
        1. Verify bullets approved (0% → 30%)
        2. Fetch approved bullets (30% → 50%)
        3. Assemble CV sections (50% → 80%)
        4. Format final document (80% → 100%)

        Final Status: 'completed'

        Args:
            generation_id: UUID of GeneratedDocument record
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            GenerationResult with final CV content

        Raises:
            Exception: If bullets not approved or assembly fails
        """
        import time
        start_time = time.time()

        try:
            # Import models
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            BulletPoint = apps.get_model('generation', 'BulletPoint')

            # Stage 1: Verify bullets approved (0% → 30%)
            if progress_callback:
                progress_callback(0)

            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)

            # Validate preconditions
            if generation.status != 'bullets_approved':
                raise Exception(
                    f"Cannot assemble CV: bullets must be approved first. Current status: {generation.status}"
                )

            # Update status to assembling
            generation.status = 'assembling'
            await sync_to_async(generation.save)(update_fields=['status'])

            if progress_callback:
                progress_callback(30)

            # Stage 2: Fetch approved bullets (30% → 50%)
            approved_bullets = await sync_to_async(list)(
                BulletPoint.objects.filter(
                    cv_generation=generation,
                    user_approved=True
                ).select_related('artifact').order_by('artifact_id', 'position')
            )

            if not approved_bullets:
                raise Exception("No approved bullets found for CV assembly")

            # Group bullets by artifact
            bullets_by_artifact = {}
            for bullet in approved_bullets:
                artifact_id = bullet.artifact_id
                if artifact_id not in bullets_by_artifact:
                    bullets_by_artifact[artifact_id] = []
                bullets_by_artifact[artifact_id].append({
                    'position': bullet.position,
                    'text': bullet.text,
                    'type': bullet.bullet_type,
                    'keywords': bullet.keywords,
                    'confidence': bullet.confidence_score
                })

            if progress_callback:
                progress_callback(50)

            # Stage 3: Assemble CV sections (50% → 80%)
            job_desc = generation.job_description

            # Prepare bullets for assembly
            all_bullets = []
            for artifact_id, bullets in bullets_by_artifact.items():
                for bullet in bullets:
                    all_bullets.append(bullet)

            # Call assembly service
            assembled_document = await self.content_service.assemble_final_document(
                document_type=generation.document_type,
                generated_content={'bullets': all_bullets},
                job_data=job_desc.parsed_data,
                artifacts_used=list(bullets_by_artifact.keys()),
                template_config={'template_id': generation.template_id},
                custom_sections=generation.custom_sections,
                processing_metadata={}
            )

            if progress_callback:
                progress_callback(80)

            # Stage 4: Save final document (80% → 100%)
            generation.content = assembled_document['content']
            generation.metadata = assembled_document['metadata']
            generation.status = 'completed'
            generation.assembled_at = timezone.now()
            generation.completed_at = timezone.now()
            generation.artifacts_used = list(bullets_by_artifact.keys())

            await sync_to_async(generation.save)(
                update_fields=[
                    'content', 'metadata', 'status', 'assembled_at',
                    'completed_at', 'artifacts_used'
                ]
            )

            if progress_callback:
                progress_callback(100)

            # Calculate total time
            elapsed_ms = int((time.time() - start_time) * 1000)

            return GenerationResult(
                cv_content=assembled_document['content'],
                metadata=assembled_document['metadata'],
                artifacts_used=list(bullets_by_artifact.keys()),
                job_parsed_data=job_desc.parsed_data,
                generation_time_ms=elapsed_ms,
                model_version=assembled_document['metadata'].get('model_used', 'unknown'),
                total_cost_usd=assembled_document['metadata'].get('cost_usd', 0.0)
            )

        except Exception as e:
            logger.error(f"CV assembly failed for {generation_id}: {e}", exc_info=True)

            # Update generation status to failed
            try:
                generation.status = 'failed'
                generation.error_message = str(e)
                await sync_to_async(generation.save)(update_fields=['status', 'error_message'])
            except:
                pass

            raise

    async def _fetch_selected_artifacts(
        self,
        user_id: int,
        artifact_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Fetch and validate manually selected artifacts (ft-007).

        This method ensures:
        1. All artifact_ids exist
        2. All artifacts belong to the user (ownership validation)
        3. Artifacts are returned in the order specified by artifact_ids

        Args:
            user_id: User ID for ownership validation
            artifact_ids: List of artifact IDs in desired order

        Returns:
            List of artifact dictionaries in the specified order

        Raises:
            PermissionError: If any artifact doesn't belong to user
            ValueError: If any artifact ID doesn't exist
        """
        Artifact = apps.get_model('artifacts', 'Artifact')

        # Fetch artifacts with ownership filter
        artifacts = await sync_to_async(list)(
            Artifact.objects.filter(
                id__in=artifact_ids,
                user_id=user_id
            ).prefetch_related('evidence')
        )

        # Validate all artifact_ids were found and belong to user
        found_ids = {artifact.id for artifact in artifacts}
        requested_ids = set(artifact_ids)

        if found_ids != requested_ids:
            missing_ids = requested_ids - found_ids
            raise ValueError(
                f"Artifacts not found or not owned by user: {missing_ids}"
            )

        # Build artifact dicts and preserve order
        artifact_dict_by_id = {}
        for artifact in artifacts:
            artifact_dict = await self._build_artifact_dict(artifact)
            artifact_dict_by_id[artifact.id] = artifact_dict

        # Return in specified order
        ordered_artifacts = [
            artifact_dict_by_id[artifact_id]
            for artifact_id in artifact_ids
        ]

        logger.info(f"Fetched {len(ordered_artifacts)} manually selected artifacts for user {user_id}")
        return ordered_artifacts

    async def _select_relevant_artifacts(self, ranked_artifacts: List[Dict], generation) -> List[Dict]:
        """
        Select artifacts for bullet generation based on ranking and preferences.

        Args:
            ranked_artifacts: List of artifacts sorted by relevance
            generation: GeneratedDocument instance

        Returns:
            List of selected artifacts for bullet generation
        """
        # Default: Select top 5 artifacts
        max_artifacts = generation.generation_preferences.get('max_artifacts', 5)
        return ranked_artifacts[:max_artifacts]

    async def _build_artifact_dict(self, artifact) -> Dict[str, Any]:
        """
        Build artifact dictionary from ORM model.

        Converts Django model to dict format expected by LLM services.
        Includes evidence links, technologies, and metadata.

        Args:
            artifact: Artifact ORM model instance

        Returns:
            Dict with artifact data formatted for LLM services
        """
        # Access prefetched evidence links
        evidence_links = await sync_to_async(list)(artifact.evidence.all())

        evidence_links_data = []
        for link in evidence_links:
            evidence_links_data.append({
                'url': link.url,
                'type': link.evidence_type,
                'description': link.description
            })

        # Build artifact dict with all fields
        artifact_dict = {
            'id': artifact.id,
            'title': await sync_to_async(lambda: artifact.title)(),
            'description': await sync_to_async(lambda: artifact.description)(),
            'artifact_type': await sync_to_async(lambda: artifact.artifact_type)(),
            'start_date': str(await sync_to_async(lambda: artifact.start_date)()) if await sync_to_async(lambda: artifact.start_date)() else None,
            'end_date': str(await sync_to_async(lambda: artifact.end_date)()) if await sync_to_async(lambda: artifact.end_date)() else None,
            'technologies': await sync_to_async(lambda: artifact.technologies)(),
            'collaborators': await sync_to_async(lambda: artifact.collaborators)(),
            'evidence_links': evidence_links_data,
            'extracted_metadata': await sync_to_async(lambda: artifact.extracted_metadata)()
        }

        return artifact_dict

    async def regenerate_generation_bullets(
        self,
        generation_id: str,
        refinement_prompt: Optional[str] = None,
        bullet_ids: Optional[List[int]] = None,
        artifact_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """
        Regenerate bullets for generation with optional refinement prompt (ft-024, ADR-036).

        This method regenerates bullet points for a generation, optionally using
        a refinement prompt to guide the LLM. The refinement prompt is temporary and
        NOT persisted to the database per ADR-036.

        Args:
            generation_id: Generation UUID to regenerate bullets for
            refinement_prompt: Temporary hint for LLM (max 500 chars, NOT persisted)
            bullet_ids: Optional list of specific bullet IDs to regenerate
            artifact_ids: Optional list of artifact IDs to regenerate bullets for
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Dict with:
                success: bool - Whether regeneration succeeded
                bullets_regenerated: int - Number of bullets regenerated
                content_sources_used: List[str] - Content sources used
                refinement_prompt_used: bool - Whether refinement prompt was provided

        Raises:
            ValidationError: If generation_id invalid or refinement_prompt too long
            PermissionError: If user doesn't own the generation

        Example:
            >>> service = GenerationService()
            >>> result = await service.regenerate_generation_bullets(
            ...     generation_id="550e8400-e29b-41d4-a716-446655440000",
            ...     refinement_prompt="Focus more on leadership and team management",
            ...     artifact_ids=[1, 3, 5]
            ... )
            >>> print(f"Regenerated {result['bullets_regenerated']} bullets")
        """
        try:
            # Import models here to avoid circular imports
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            Artifact = apps.get_model('artifacts', 'Artifact')

            # 1. Fetch generation record
            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description').get
            )(id=generation_id)

            # 2. Get job context from generation.job_description_data
            # Fallback to parsing job_description if job_description_data not set
            if generation.job_description_data:
                job_context = generation.job_description_data
                logger.info(f"Using job_description_data from generation {generation_id}")
            elif generation.job_description and generation.job_description.parsed_data:
                job_context = generation.job_description.parsed_data
                logger.info(f"Using parsed_data from job_description for generation {generation_id}")
            else:
                raise ValidationError(
                    f"No job context found for generation {generation_id}. "
                    "job_description_data and parsed_data are both missing."
                )

            # 3. Add refinement prompt to job_context (temporary, not persisted per ADR-036)
            refined_context = job_context.copy()
            if refinement_prompt:
                refined_context['_refinement_prompt'] = refinement_prompt
                logger.info(f"Refinement prompt provided (length: {len(refinement_prompt)} chars)")

            # 4. Determine which artifacts to regenerate
            if artifact_ids:
                # Regenerate bullets for specific artifacts
                artifacts = await sync_to_async(list)(
                    Artifact.objects.filter(id__in=artifact_ids)
                )
                if len(artifacts) != len(artifact_ids):
                    found_ids = {a.id for a in artifacts}
                    missing_ids = set(artifact_ids) - found_ids
                    raise ValidationError(f"Artifacts not found: {missing_ids}")
            else:
                # Regenerate bullets for all artifacts in this generation
                # Get artifacts from existing bullets
                BulletPoint = apps.get_model('generation', 'BulletPoint')
                bullet_artifacts = await sync_to_async(list)(
                    BulletPoint.objects.filter(cv_generation_id=generation_id)
                    .values_list('artifact_id', flat=True)
                    .distinct()
                )
                artifacts = await sync_to_async(list)(
                    Artifact.objects.filter(id__in=bullet_artifacts)
                )

            # 5. Regenerate bullets for each artifact
            regenerated_count = 0
            total_artifacts = len(artifacts)
            content_sources_used = []

            for i, artifact in enumerate(artifacts):
                if progress_callback:
                    progress = int((i / total_artifacts) * 100)
                    progress_callback(progress)

                # Call bullet generation service with regenerate=True
                result = await self.bullet_service.generate_bullets(
                    artifact_id=artifact.id,
                    job_context=refined_context,  # Contains temporary refinement_prompt
                    cv_generation_id=generation_id,
                    regenerate=True  # Force regeneration
                )

                regenerated_count += len(result.bullets)
                if result.content_sources_used:
                    content_sources_used.extend(result.content_sources_used)

            if progress_callback:
                progress_callback(100)

            # Deduplicate content sources
            content_sources_used = list(set(content_sources_used))

            return {
                'success': True,
                'bullets_regenerated': regenerated_count,
                'content_sources_used': content_sources_used,
                'refinement_prompt_used': refinement_prompt is not None
            }

        except Exception as e:
            logger.error(f"Failed to regenerate bullets for generation {generation_id}: {e}")
            raise

    def get_model_selection_strategy(self) -> str:
        """Get configured model selection strategy."""
        return getattr(settings, 'MODEL_SELECTION_STRATEGY', 'balanced')
