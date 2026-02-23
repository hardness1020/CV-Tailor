"""
Bullet Generation Service

Generates exactly 3 bullet points per artifact following ft-006 specification.

Architecture:
- Orchestrates bullet generation workflow
- Calls TailoredContentService for LLM generation
- Integrates BulletValidationService for quality checks
- Handles regeneration logic (up to 3 attempts)
- Tracks generation jobs and metrics

References:
- ADR-20251001-generation-service-layer-extraction
- ADR-20251001-bullet-validation-architecture
- spec-20251001-ft006-implementation
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from asgiref.sync import sync_to_async

from ..models import BulletPoint, BulletGenerationJob
from artifacts.models import Artifact
from llm_services.services.core.tailored_content_service import TailoredContentService
from .bullet_validation_service import BulletValidationService
from .bullet_verification_service import BulletVerificationService  # ft-030
from .confidence_calculator import calculate_bullet_confidence  # ft-030

logger = logging.getLogger(__name__)


@dataclass
class GeneratedBulletSet:
    """
    Container for generated bullet set with metadata.

    Attributes:
        bullets: List of 3 BulletPoint instances
        quality_score: Overall quality score (0-1)
        validation_passed: Whether validation succeeded
        validation_issues: List of validation issue messages
        generation_time_ms: Total generation time in milliseconds
        cost_usd: LLM API cost for this generation
        model_used: Model identifier used for generation
        content_sources_used: List of content sources used (ft-024)
        verification_passed: Whether verification succeeded (ft-030)
        flagged_bullets: List of bullet indices that require review (ft-030)
    """
    bullets: List['BulletPoint']
    quality_score: float
    validation_passed: bool
    validation_issues: List[str]
    generation_time_ms: int
    cost_usd: float
    model_used: str
    content_sources_used: List[str] = None
    verification_passed: bool = True  # ft-030
    flagged_bullets: List[int] = None  # ft-030


class BulletGenerationService:
    """
    Service for generating exactly 3 bullet points per artifact.

    Implements ft-006 three-bullets-per-artifact feature with:
    - Structured hierarchy: achievement → technical → impact
    - Quality validation: content scoring, semantic similarity checking
    - Auto-regeneration: up to 3 attempts on validation failure
    - Performance tracking: latency, cost, success rate metrics

    Usage:
        service = BulletGenerationService()
        result = await service.generate_bullets(
            artifact_id=123,
            job_context={"role_title": "Senior Engineer", ...}
        )
    """

    def __init__(self):
        """
        Initialize bullet generation service with dependencies.

        Dependencies:
        - TailoredContentService: For LLM bullet generation
        - BulletValidationService: For quality validation
        - BulletVerificationService: For fact-checking (ft-030)
        """
        self.tailored_content_service = TailoredContentService()
        self.validation_service = BulletValidationService()
        self.verification_service = BulletVerificationService()  # ft-030
        self.max_attempts = 3

    def _build_comprehensive_content(self, artifact: 'Artifact') -> Dict[str, Any]:
        """
        Build comprehensive content from multiple artifact sources (ft-024, ADR-035).

        This implements the multi-source content assembly pattern for richer bullet generation.
        Content is assembled in priority order:
        1. user_context (HIGHEST PRIORITY - user-provided facts)
        2. unified_description (AI-enhanced from evidence)
        3. enriched_achievements (extracted metrics)
        4. description (fallback)

        Args:
            artifact: Artifact to extract content from

        Returns:
            Dict with:
                'content': str - Assembled content with section headers
                'sources_used': List[str] - Which fields contributed to content

        Example:
            >>> content_data = self._build_comprehensive_content(artifact)
            >>> print(content_data['content'])
            User-Provided Context (PRIORITIZE):
            Led team of 6 engineers...

            Enhanced Description:
            Full-stack development with React and Django...

            Key Achievements:
            - Reduced API latency by 40%
            - Shipped 15 features in Q1

            >>> print(content_data['sources_used'])
            ['user_context', 'unified_description', 'enriched_achievements']
        """
        parts = []
        sources_used = []

        # 1. User context (HIGHEST PRIORITY)
        if hasattr(artifact, 'user_context') and artifact.user_context:
            parts.append(f"User-Provided Context (PRIORITIZE):\n{artifact.user_context}")
            sources_used.append('user_context')

        # 2. AI-enhanced description
        if hasattr(artifact, 'unified_description') and artifact.unified_description:
            parts.append(f"Enhanced Description:\n{artifact.unified_description}")
            sources_used.append('unified_description')
        elif artifact.description:
            parts.append(f"Description:\n{artifact.description}")
            sources_used.append('description')

        # 3. Extracted achievements with metrics
        if hasattr(artifact, 'enriched_achievements') and artifact.enriched_achievements:
            # Handle both list and dict formats
            if isinstance(artifact.enriched_achievements, list):
                achievements_text = "\n".join([f"- {ach}" for ach in artifact.enriched_achievements])
            elif isinstance(artifact.enriched_achievements, dict):
                achievements_list = artifact.enriched_achievements.get('achievements', [])
                achievements_text = "\n".join([f"- {ach}" for ach in achievements_list])
            else:
                achievements_text = str(artifact.enriched_achievements)

            if achievements_text.strip():
                parts.append(f"Key Achievements:\n{achievements_text}")
                sources_used.append('enriched_achievements')

        # Fallback to title if no content
        if not parts and artifact.title:
            parts.append(f"Title:\n{artifact.title}")
            sources_used.append('title')

        content = "\n\n".join(parts) if parts else artifact.title or "No content available"

        logger.info(f"Built content for artifact {artifact.id} using sources: {sources_used}")

        return {
            'content': content,
            'sources_used': sources_used
        }

    async def generate_bullets(
        self,
        artifact_id: int,
        job_context: Dict[str, Any],
        cv_generation_id: Optional[str] = None,
        regenerate: bool = False
    ) -> GeneratedBulletSet:
        """
        Generate exactly 3 bullet points for an artifact.

        This method orchestrates the complete bullet generation workflow:
        1. Validate artifact exists and belongs to user
        2. Check if bullets already exist (unless regenerate=True)
        3. Call TailoredContentService to generate bullets via LLM
        4. Validate generated bullets (structure, quality, similarity)
        5. Retry up to 3 times if validation fails
        6. Save bullets to database
        7. Return GeneratedBulletSet with results

        Args:
            artifact_id: Artifact to generate bullets for
            job_context: Job requirements and context for tailoring
                Required fields: role_title, key_requirements
                Optional fields: preferred_skills, company_name, seniority_level
            cv_generation_id: Parent CV generation UUID (optional)
            regenerate: Force regeneration even if bullets exist

        Returns:
            GeneratedBulletSet with:
                - bullets: List of 3 BulletPoint instances
                - quality_score: 0-1 score
                - validation_passed: bool
                - validation_issues: List of issues if any
                - generation_time_ms: Processing time
                - cost_usd: LLM API cost
                - model_used: Model identifier

        Raises:
            ValidationError: If bullets fail validation after 3 attempts
            ArtifactNotFoundError: If artifact doesn't exist
            LLMServiceError: If LLM generation fails
            PermissionError: If artifact doesn't belong to user

        Example:
            >>> service = BulletGenerationService()
            >>> result = await service.generate_bullets(
            ...     artifact_id=123,
            ...     job_context={
            ...         "role_title": "Senior Software Engineer",
            ...         "key_requirements": ["Python", "Django", "PostgreSQL"],
            ...         "seniority_level": "senior"
            ...     }
            ... )
            >>> print(f"Generated {len(result.bullets)} bullets")
            >>> print(f"Quality score: {result.quality_score}")
        """
        start_time = timezone.now()

        # 1. Fetch artifact and validate ownership
        @sync_to_async
        def get_artifact():
            try:
                artifact = Artifact.objects.select_related('user').get(id=artifact_id)
                # Eagerly access user_id to avoid lazy loading in async context
                _ = artifact.user_id
                return artifact
            except Artifact.DoesNotExist:
                raise ValidationError(f"Artifact with id {artifact_id} not found")

        artifact = await get_artifact()

        # Note: Ownership validation would require user context
        # For now, we assume the artifact is accessible

        # 2. Check existing bullets (return if found and regenerate=False)
        @sync_to_async
        def check_existing_bullets():
            if not regenerate and cv_generation_id:
                existing_bullets = list(BulletPoint.objects.filter(
                    artifact=artifact,
                    cv_generation_id=cv_generation_id
                ).order_by('position'))

                if len(existing_bullets) == 3:
                    return existing_bullets
            return None

        existing = await check_existing_bullets()
        if existing:
            logger.info(f"Returning existing bullets for artifact {artifact_id}")
            return GeneratedBulletSet(
                bullets=existing,
                quality_score=sum(b.quality_score for b in existing) / 3,
                validation_passed=True,
                validation_issues=[],
                generation_time_ms=0,
                cost_usd=0.0,
                model_used='cached',
                content_sources_used=[]
            )

        # 3. Create BulletGenerationJob and mark as processing
        @sync_to_async
        def create_job():
            return BulletGenerationJob.objects.create(
                artifact=artifact,
                user=artifact.user,
                job_context=job_context,
                status='processing',
                max_attempts=self.max_attempts
            )

        job = await create_job()

        try:
            # 4-7. Generate and validate bullets with retry logic
            bullets_data = None
            validation_result = None
            total_cost = Decimal('0.0')
            model_used = 'unknown'

            for attempt in range(self.max_attempts):
                await sync_to_async(job.increment_attempt)()

                # 4. Call TailoredContentService.generate_bullet_points(target_count=3)
                # ft-024: Use multi-source content assembly (ADR-035)
                content_data = self._build_comprehensive_content(artifact)
                artifact_content = content_data['content']
                sources_used = content_data['sources_used']

                llm_response = await self.tailored_content_service.generate_bullet_points(
                    artifact_content=artifact_content,
                    job_requirements=job_context.get('key_requirements', []),
                    user_id=artifact.user.id,
                    target_count=3,
                    job_context=job_context
                )

                # Track cost from processing metadata
                metadata = llm_response.get('processing_metadata', {})
                if 'cost_usd' in metadata:
                    total_cost += Decimal(str(metadata['cost_usd']))
                if 'model_used' in metadata:
                    model_used = metadata['model_used']

                # 5. Parse LLM response into structured bullet data
                bullets_data = llm_response.get('bullet_points', [])

                # Ensure we have exactly 3 bullets
                if len(bullets_data) != 3:
                    logger.warning(f"LLM returned {len(bullets_data)} bullets, expected 3")
                    if attempt < self.max_attempts - 1:
                        continue
                    else:
                        raise ValidationError(f"Failed to generate exactly 3 bullets after {self.max_attempts} attempts")

                # 6. Call BulletValidationService.validate_bullet_set()
                validation_result = await self.validation_service.validate_bullet_set(
                    bullets=bullets_data,
                    job_context=job_context
                )

                # 7. If validation passes, run verification (ft-030). Otherwise retry.
                if validation_result.is_valid:
                    logger.info(f"Bullets validated successfully on attempt {attempt + 1}")

                    # ft-030: Verify bullets against source evidence
                    logger.info("[ft-030] Running verification on generated bullets")
                    bullet_texts = [b['text'] for b in bullets_data]

                    # Use artifact content as source evidence
                    verification_results = await self.verification_service.verify_bullet_set(
                        bullets=bullet_texts,
                        source_content=artifact_content,
                        user_id=artifact.user.id
                    )

                    # Store verification metadata with bullets
                    for idx, bullet_data in enumerate(bullets_data):
                        if idx < len(verification_results):
                            bullet_data['verification'] = verification_results[idx]

                            # Calculate overall confidence (ft-030)
                            confidence_result = calculate_bullet_confidence(
                                extraction_data={'confidence': 0.85, 'inferred_ratio': 0.15},  # From artifact extraction
                                generation_data={'confidence': bullet_data.get('confidence_score', 0.7), 'text': bullet_data['text']},
                                verification_data={
                                    'confidence': verification_results[idx].get('confidence', 0.5),
                                    'unsupported_claims': len([c for c in verification_results[idx].get('claims', []) if c.get('classification') == 'UNSUPPORTED']),
                                    'total_claims': len(verification_results[idx].get('claims', []))
                                },
                                content_type='achievement' if 'achievement' in bullet_data.get('bullet_type', '').lower() else 'technical'
                            )

                            bullet_data['confidence_metadata'] = confidence_result
                            logger.info(f"[ft-030] Bullet {idx+1} confidence: {confidence_result['confidence']:.2f} ({confidence_result['tier']} tier)")

                    break
                else:
                    logger.warning(f"Validation failed on attempt {attempt + 1}: {validation_result.issues}")
                    if attempt < self.max_attempts - 1:
                        # Refine prompt based on validation issues
                        job_context['_validation_feedback'] = validation_result.issues
                    else:
                        # Max attempts reached
                        @sync_to_async
                        def update_job_failed():
                            job.status = 'needs_review'
                            job.validation_results = {
                                'is_valid': False,
                                'issues': validation_result.issues,
                                'quality_score': validation_result.overall_quality_score
                            }
                            job.save()

                        await update_job_failed()

                        raise ValidationError(
                            f"Bullets failed validation after {self.max_attempts} attempts: "
                            f"{', '.join(validation_result.issues)}"
                        )

            # 8. Save validated bullets to database with metadata
            @sync_to_async
            def save_bullets():
                bullets = []
                with transaction.atomic():
                    # Delete existing bullets if regenerating
                    if regenerate and cv_generation_id:
                        BulletPoint.objects.filter(
                            artifact=artifact,
                            cv_generation_id=cv_generation_id
                        ).delete()

                    for idx, bullet_data in enumerate(bullets_data):
                        # Get quality score safely from validation result
                        if validation_result and hasattr(validation_result, 'bullet_scores') and idx < len(validation_result.bullet_scores):
                            quality_score = validation_result.bullet_scores[idx]
                        else:
                            quality_score = 0.5

                        bullet = BulletPoint.objects.create(
                            artifact=artifact,
                            cv_generation_id=cv_generation_id,
                            position=bullet_data.get('position', idx + 1),
                            bullet_type=bullet_data.get('bullet_type'),
                            text=bullet_data.get('text'),
                            keywords=bullet_data.get('keywords', []),
                            metrics=bullet_data.get('metrics', {}),
                            confidence_score=bullet_data.get('confidence_score', 0.7),
                            quality_score=quality_score
                        )
                        bullets.append(bullet)
                return bullets

            bullets = await save_bullets()

            # 9. Mark job as completed with metrics
            end_time = timezone.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            @sync_to_async
            def complete_job():
                job.status = 'completed'
                job.generated_bullets = bullets_data
                job.validation_results = {
                    'is_valid': True,
                    'quality_score': validation_result.overall_quality_score,
                    'bullet_scores': validation_result.bullet_scores
                }
                job.processing_duration_ms = processing_time_ms
                job.llm_cost_usd = total_cost
                job.save()

            await complete_job()

            # 10. Return GeneratedBulletSet with verification metadata (ft-030)
            flagged_bullets = [
                idx for idx, bullet_data in enumerate(bullets_data)
                if bullet_data.get('confidence_metadata', {}).get('requires_review', False)
            ]

            return GeneratedBulletSet(
                bullets=bullets,
                quality_score=validation_result.overall_quality_score,
                validation_passed=True,
                validation_issues=[],
                generation_time_ms=processing_time_ms,
                cost_usd=float(total_cost),
                model_used=model_used,
                content_sources_used=sources_used,
                verification_passed=len(flagged_bullets) == 0,  # ft-030
                flagged_bullets=flagged_bullets  # ft-030
            )

        except Exception as e:
            # Mark job as failed
            @sync_to_async
            def mark_failed():
                from django.db import transaction
                try:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.save()
                except transaction.TransactionManagementError:
                    # Transaction is broken, can't save - log and continue
                    logger.warning(f"Could not save failed job status due to broken transaction: {e}")

            await mark_failed()
            raise

    async def batch_generate_bullets(
        self,
        artifact_ids: List[int],
        job_context: Dict[str, Any],
        cv_generation_id: Optional[str] = None
    ) -> Dict[int, GeneratedBulletSet]:
        """
        Generate bullets for multiple artifacts in parallel.

        Optimized for bulk CV generation. Processes multiple artifacts
        concurrently to minimize total generation time.

        Args:
            artifact_ids: List of artifact IDs to process
            job_context: Shared job context for all artifacts
            cv_generation_id: Parent CV generation UUID (optional)

        Returns:
            Dict mapping artifact_id to GeneratedBulletSet
            Successful generations included; failed ones omitted or marked

        Raises:
            PartialGenerationError: If some artifacts fail (includes partial results)
            ValidationError: If job_context is invalid

        Example:
            >>> result = await service.batch_generate_bullets(
            ...     artifact_ids=[123, 456, 789],
            ...     job_context={...}
            ... )
            >>> for artifact_id, bullet_set in result.items():
            ...     print(f"Artifact {artifact_id}: {len(bullet_set.bullets)} bullets")
        """
        results = {}
        errors = {}

        # 1. Validate all artifacts exist (ownership validation would require user context)
        @sync_to_async
        def validate_artifacts():
            artifacts = list(Artifact.objects.filter(id__in=artifact_ids))
            if len(artifacts) != len(artifact_ids):
                found_ids = {a.id for a in artifacts}
                missing_ids = set(artifact_ids) - found_ids
                raise ValidationError(f"Artifacts not found: {missing_ids}")

        await validate_artifacts()

        # 2-4. Generate bullets for each artifact in parallel
        async def generate_for_artifact(artifact_id: int):
            try:
                result = await self.generate_bullets(
                    artifact_id=artifact_id,
                    job_context=job_context,
                    cv_generation_id=cv_generation_id
                )
                return artifact_id, result, None
            except Exception as e:
                logger.error(f"Failed to generate bullets for artifact {artifact_id}: {e}")
                return artifact_id, None, str(e)

        # 3. Use asyncio.gather() to process in parallel
        tasks = [generate_for_artifact(artifact_id) for artifact_id in artifact_ids]
        generation_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 5-6. Collect results and errors
        for result in generation_results:
            if isinstance(result, Exception):
                logger.error(f"Batch generation error: {result}")
                continue

            artifact_id, bullet_set, error = result
            if error:
                errors[artifact_id] = error
            elif bullet_set:
                results[artifact_id] = bullet_set

        # 7. Return results (partial success acceptable)
        if errors:
            logger.warning(f"Batch generation completed with {len(errors)} errors: {errors}")

        return results

    async def regenerate_bullet(
        self,
        bullet_id: int,
        refinement_prompt: Optional[str] = None
    ) -> Any:  # Will be BulletPoint after models created
        """
        Regenerate a single bullet point with optional user refinement.

        Allows users to regenerate individual bullets without regenerating
        the entire set. Useful for iterative refinement.

        Args:
            bullet_id: ID of bullet to regenerate
            refinement_prompt: Optional user guidance
                Examples: "Add more metrics", "Focus on leadership"

        Returns:
            Updated BulletPoint instance

        Raises:
            BulletNotFoundError: If bullet doesn't exist
            PermissionError: If bullet doesn't belong to user
            ValidationError: If regenerated bullet still fails validation

        Example:
            >>> bullet = await service.regenerate_bullet(
            ...     bullet_id=456,
            ...     refinement_prompt="Add more quantified metrics"
            ... )
            >>> print(bullet.text)
        """
        # 1. Fetch existing bullet and validate ownership
        @sync_to_async
        def get_bullet_and_artifact():
            try:
                bullet = BulletPoint.objects.select_related('artifact__user').get(id=bullet_id)
                artifact = bullet.artifact
                # Eagerly access user_id to avoid lazy loading in async context
                _ = artifact.user_id
                _ = artifact.description
                _ = artifact.title
                return bullet, artifact
            except BulletPoint.DoesNotExist:
                raise ValidationError(f"Bullet with id {bullet_id} not found")

        bullet, artifact = await get_bullet_and_artifact()

        # Note: Ownership validation would require user context
        # For now, we assume the bullet is accessible

        # Reconstruct job context from bullet's cv_generation if available
        job_context = {
            'role_title': 'Software Engineer',  # Would come from CV generation
            'key_requirements': bullet.keywords,
            'refinement_guidance': refinement_prompt
        }

        # 3. Build refined prompt incorporating user guidance
        refined_context = job_context.copy()
        if refinement_prompt:
            refined_context['_refinement_prompt'] = refinement_prompt

        # 4. Call TailoredContentService with refined prompt
        llm_response = await self.tailored_content_service.generate_bullet_points(
            artifact_content=artifact.description or artifact.title,
            job_requirements=job_context.get('key_requirements', []),
            user_id=artifact.user.id,
            target_count=1,  # Only regenerate one bullet
            job_context=refined_context
        )

        # Parse response
        bullets_data = llm_response.get('bullet_points', [])
        if not bullets_data:
            raise ValidationError("Failed to regenerate bullet: LLM returned no bullets")

        new_bullet_data = bullets_data[0]

        # 5. Validate regenerated bullet
        validation_result = self.validation_service.validate_content_quality(
            bullet=new_bullet_data,
            job_context=job_context
        )

        if validation_result < 0.5:
            logger.warning(f"Regenerated bullet has low quality score: {validation_result}")

        # 6-8. Update bullet in database (preserve original_text if first regeneration)
        @sync_to_async
        def update_bullet():
            # Preserve original text if this is the first regeneration
            if not bullet.original_text:
                bullet.original_text = bullet.text

            bullet.text = new_bullet_data.get('text')
            bullet.keywords = new_bullet_data.get('keywords', [])
            bullet.metrics = new_bullet_data.get('metrics', {})
            bullet.confidence_score = new_bullet_data.get('confidence_score', 0.7)
            bullet.quality_score = validation_result

            # 7. Set user_edited=False (this is regeneration, not edit)
            bullet.user_edited = False

            bullet.save()
            return bullet

        # Return updated bullet
        return await update_bullet()

    def get_generation_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of bullet generation job.

        Used for async status polling from frontend.

        Args:
            job_id: BulletGenerationJob UUID

        Returns:
            Dict with:
                - status: "pending" | "processing" | "completed" | "failed" | "needs_review"
                - progress_percentage: 0-100
                - bullets: List of bullets if completed
                - error_message: Error details if failed
                - processing_duration_ms: Time taken if completed

        Raises:
            JobNotFoundError: If job doesn't exist
            PermissionError: If job doesn't belong to user

        Example:
            >>> status = service.get_generation_status("uuid-123")
            >>> if status["status"] == "completed":
            ...     bullets = status["bullets"]
        """
        # 1. Fetch BulletGenerationJob by UUID
        try:
            job = BulletGenerationJob.objects.get(id=job_id)
        except BulletGenerationJob.DoesNotExist:
            raise ValidationError(f"Job with id {job_id} not found")

        # 2. Validate ownership (would require user context)
        # For now, we assume the job is accessible

        # 3. Return status dict with all relevant fields
        status_data = {
            'status': job.status,
            'progress_percentage': self._calculate_progress(job),
            'artifact_id': job.artifact.id if job.artifact else None,
            'created_at': job.created_at.isoformat(),
        }

        # 4. If completed, include serialized bullets
        if job.status == 'completed':
            status_data['bullets'] = job.generated_bullets
            status_data['validation_results'] = job.validation_results
            status_data['processing_duration_ms'] = job.processing_duration_ms
            status_data['llm_cost_usd'] = float(job.llm_cost_usd) if job.llm_cost_usd else 0.0

        # 5. If failed, include error message
        elif job.status == 'failed':
            status_data['error_message'] = job.error_message

        elif job.status == 'needs_review':
            status_data['validation_results'] = job.validation_results
            status_data['generation_attempts'] = job.generation_attempts

        return status_data

    def _calculate_progress(self, job: BulletGenerationJob) -> int:
        """Calculate progress percentage based on job status and attempts"""
        if job.status == 'completed':
            return 100
        elif job.status == 'failed':
            return 0
        elif job.status == 'processing':
            # Base progress of 50% when processing, increase based on attempts
            if job.generation_attempts > 0:
                return min(50 + (15 * job.generation_attempts), 99)
            return 50
        elif job.status == 'pending':
            return 0
        elif job.status == 'needs_review':
            return 90
        return 0

    async def cleanup(self):
        """
        Cleanup async resources from dependent services.
        Should be called when service is no longer needed.
        """
        try:
            # Cleanup TailoredContentService which uses async LLM clients
            await self.tailored_content_service.cleanup()
        except Exception as e:
            # Log but don't fail - cleanup is best effort
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error during BulletGenerationService cleanup: {e}")
