"""
Enhanced Celery tasks for CV generation with new LLM services.
Integrates ft-llm-001, ft-llm-002, ft-llm-003, and ft-005 implementations.

Updated to use refactored services (SPEC-20250930):
- GenerationService (orchestrates full workflow)
- TailoredContentService (LLM I/O)
- ArtifactRankingService (keyword-based ranking, ft-007)
"""

import asyncio
import logging
from celery import shared_task
from django.utils import timezone
from django.apps import apps
from asgiref.sync import sync_to_async

from common.exceptions import (
    GenerationError, ValidationError, EnrichmentError,
    ArtifactNotFoundError, InsufficientDataError
)
from llm_services.services.core.artifact_enrichment_service import ArtifactEnrichmentService
from .services.generation_service import GenerationService

logger = logging.getLogger(__name__)


@shared_task
def prepare_generation_bullets_task(generation_id):
    """
    Phase 1: Generate bullets for review (ft-009 two-phase workflow).

    Synchronous Celery task wrapper that executes async bullet preparation.
    """
    return asyncio.run(_prepare_generation_bullets_async(generation_id))


async def _prepare_generation_bullets_async(generation_id):
    """
    Async implementation of Phase 1: Generate bullets for review.

    NEW (ft-023): Status validation to prevent duplicate processing.
    Final status: 'bullets_ready' (awaiting user approval)
    """
    try:
        # Import models here to avoid circular imports
        GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')

        # Fetch generation record
        generation = await sync_to_async(
            GeneratedDocument.objects.select_related('job_description', 'user').get
        )(id=generation_id)

        # NEW (ft-023): Validate status before processing
        if generation.status not in ['pending', 'failed']:
            logger.warning(
                f"Cannot prepare bullets for generation {generation_id}: "
                f"status is {generation.status}, expected 'pending' or 'failed'"
            )
            return {
                'skipped': True,
                'reason': 'invalid_status',
                'current_status': generation.status,
                'expected_status': ['pending', 'failed']
            }

        # Mark as processing
        generation.status = 'processing'
        generation.progress_percentage = 0
        await sync_to_async(generation.save)()

        # Initialize CV generation service
        cv_service = GenerationService()

        # Progress callback updates database
        async def update_progress(percentage: int):
            generation.progress_percentage = percentage
            await sync_to_async(generation.save)()

        # ft-007: Extract artifact_ids from generation_preferences if provided
        artifact_ids = generation.generation_preferences.get('artifact_ids', None)
        if artifact_ids:
            logger.info(f"Using manually selected artifacts: {artifact_ids}")

        # Execute Phase 1: Bullet preparation
        result = await cv_service.prepare_bullets(
            generation_id=generation_id,
            artifact_ids=artifact_ids,
            progress_callback=update_progress
        )

        # Result already saved by service (status='bullets_ready')
        # Just update progress to 100%
        generation.progress_percentage = 100
        await sync_to_async(generation.save)(update_fields=['progress_percentage'])

        logger.info(
            f"Successfully prepared {result.total_bullets_generated} bullets "
            f"for generation {generation_id}"
        )

        return {
            'success': True,
            'total_bullets': result.total_bullets_generated,
            'artifacts_processed': result.artifacts_processed
        }

    except Exception as e:
        logger.error(f"Error preparing bullets for {generation_id}: {e}", exc_info=True)
        try:
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)
            generation.status = 'failed'
            generation.error_message = str(e)
            await sync_to_async(generation.save)()
        except Exception as save_error:
            logger.error(f"Failed to save error status for {generation_id}: {save_error}")

        return {'success': False, 'error': str(e)}


@shared_task
def assemble_generation_task(generation_id):
    """
    Phase 2: Assemble CV from approved bullets (ft-009 two-phase workflow).

    Synchronous Celery task wrapper that executes async CV assembly.
    """
    return asyncio.run(_assemble_generation_async(generation_id))


async def _assemble_generation_async(generation_id):
    """
    Async implementation of Phase 2: Assemble CV from approved bullets.

    Precondition: status='bullets_approved'
    Final status: 'completed'
    """
    try:
        # Import models here to avoid circular imports
        GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')

        # Fetch generation record
        generation = await sync_to_async(
            GeneratedDocument.objects.select_related('job_description', 'user').get
        )(id=generation_id)

        # Validate preconditions
        if generation.status != 'bullets_approved':
            error_msg = (
                f"Cannot assemble CV: bullets must be approved first. "
                f"Current status: {generation.status}"
            )
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

        # Mark as assembling
        generation.status = 'assembling'
        generation.progress_percentage = 0
        await sync_to_async(generation.save)()

        # Initialize CV generation service
        cv_service = GenerationService()

        # Progress callback updates database
        async def update_progress(percentage: int):
            generation.progress_percentage = percentage
            await sync_to_async(generation.save)()

        # Execute Phase 2: CV assembly
        result = await cv_service.assemble_cv(
            generation_id=generation_id,
            progress_callback=update_progress
        )

        # Result already saved by service (status='completed')
        # Just update progress to 100%
        generation.progress_percentage = 100
        await sync_to_async(generation.save)(update_fields=['progress_percentage'])

        logger.info(f"Successfully assembled CV for generation {generation_id}")

        return {
            'success': True,
            'artifacts_used': result.artifacts_used,
            'generation_time_ms': result.generation_time_ms
        }

    except Exception as e:
        logger.error(f"Error assembling CV for {generation_id}: {e}", exc_info=True)
        try:
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)
            generation.status = 'failed'
            generation.error_message = str(e)
            await sync_to_async(generation.save)()
        except Exception as save_error:
            logger.error(f"Failed to save error status for {generation_id}: {save_error}")

        return {'success': False, 'error': str(e)}


@shared_task
def generate_document_task(generation_id):
    """
    DEPRECATED: Legacy single-phase CV generation task.

    Synchronous Celery task wrapper for backward compatibility.
    Will be removed in a future version.
    """
    return asyncio.run(_generate_document_async(generation_id))


async def _generate_document_async(generation_id):
    """
    Async implementation of legacy single-phase CV generation.

    This is deprecated in favor of the two-phase workflow:
    1. prepare_generation_bullets_task() - Generate bullets for review
    2. assemble_generation_task() - Assemble CV from approved bullets
    """
    logger.warning(
        f"Using deprecated generate_document_task for {generation_id}. "
        "Please migrate to two-phase workflow: prepare_generation_bullets_task + assemble_generation_task"
    )

    try:
        # Import models here to avoid circular imports
        GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')

        # Fetch generation record
        generation = await sync_to_async(
            GeneratedDocument.objects.select_related('job_description', 'user').get
        )(id=generation_id)

        # Mark as processing
        generation.status = 'processing'
        generation.progress_percentage = 0
        await sync_to_async(generation.save)()

        # Initialize CV generation service
        cv_service = GenerationService()

        # Progress callback updates database
        async def update_progress(percentage: int):
            generation.progress_percentage = percentage
            await sync_to_async(generation.save)()

        # ft-007: Extract artifact_ids from generation_preferences if provided
        artifact_ids = generation.generation_preferences.get('artifact_ids', None)
        if artifact_ids:
            logger.info(f"Using manually selected artifacts: {artifact_ids}")

        # Execute CV generation workflow (all business logic in service)
        # Service will raise exceptions on failure (no success flag)
        result = await cv_service.generate_document_for_job(
            generation_id=generation_id,
            artifact_ids=artifact_ids,
            progress_callback=update_progress
        )

        # If we got here, generation succeeded
        # Save successful result
        generation.content = result.cv_content
        generation.metadata = result.metadata
        generation.artifacts_used = result.artifacts_used
        generation.model_version = result.model_version
        generation.generation_time_ms = result.generation_time_ms
        generation.model_selection_strategy = cv_service.get_model_selection_strategy()

        # Mark as completed
        generation.status = 'completed'
        generation.progress_percentage = 100
        generation.completed_at = timezone.now()
        await sync_to_async(generation.save)()

        logger.info(f"Successfully generated CV for generation {generation_id}")

    except (ValidationError, GenerationError) as e:
        # Service raised a custom exception - generation failed
        logger.error(f"CV generation failed for {generation_id}: {e}", exc_info=True)
        try:
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)
            generation.status = 'failed'
            generation.error_message = str(e)
            await sync_to_async(generation.save)()
        except Exception as save_error:
            logger.error(f"Failed to save error status for {generation_id}: {save_error}")
    except Exception as e:
        logger.error(f"Error generating CV for {generation_id}: {e}", exc_info=True)
        try:
            GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')
            generation = await sync_to_async(
                GeneratedDocument.objects.select_related('job_description', 'user').get
            )(id=generation_id)
            generation.status = 'failed'
            generation.error_message = str(e)
            await sync_to_async(generation.save)()
        except Exception as save_error:
            logger.error(f"Failed to save error status for {generation_id}: {save_error}")


# NOTE: calculate_skill_match_score() and find_missing_skills() have been moved
# to TailoredContentService for better separation of concerns (SPEC-20250930)


# REMOVED (ft-023): enhance_artifact_with_llm() task was never called (dead code, legacy ft-005)
# Active enrichment implementation is enrich_artifact() in artifacts/tasks.py


@shared_task
def cleanup_expired_generations():
    """Cleanup expired generated documents."""
    GeneratedDocument = apps.get_model('generation', 'GeneratedDocument')

    expired_count = GeneratedDocument.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()

    logger.info(f"Cleaned up {expired_count[0]} expired generated documents")
    return expired_count[0]


@shared_task
def cleanup_old_performance_metrics():
    """Cleanup old performance metrics."""
    from llm_services.services.reliability.performance_tracker import ModelPerformanceTracker

    performance_tracker = ModelPerformanceTracker()

    # Cleanup old performance metrics (keep 30 days)
    metrics_cleaned = performance_tracker.cleanup_old_metrics(days_to_keep=30)

    logger.info(f"Cleaned up {metrics_cleaned} old performance metrics")
    return {
        'metrics_cleaned': metrics_cleaned
    }