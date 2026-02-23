"""
Generation Status Service - Unified status endpoint for generation operations

Provides comprehensive status aggregation for:
- GeneratedDocument (primary status)
- BulletGenerationJob instances (per-artifact progress)
- BulletPoint instances (quality metrics)

Matches artifact enrichment-status pattern for consistency (ft-026, ADR-040).
"""

from typing import Dict, List, Any, Optional
from django.db.models import Avg, Sum, Q
from django.utils import timezone

from generation.models import GeneratedDocument, BulletGenerationJob, BulletPoint


class GenerationStatusService:
    """
    Service for retrieving comprehensive generation status.

    Aggregates status from multiple models to provide unified view of:
    - Overall generation progress
    - Phase-level tracking (bullet generation, assembly)
    - Per-artifact job statuses
    - Processing and quality metrics
    """

    @staticmethod
    def get_generation_status(generation_id: str) -> Dict[str, Any]:
        """
        Get unified status for generation and all related jobs.

        Args:
            generation_id: UUID of the GeneratedDocument

        Returns:
            Dict containing comprehensive status information

        Raises:
            GeneratedDocument.DoesNotExist: If generation not found
        """
        generation = GeneratedDocument.objects.get(id=generation_id)

        # Fetch related jobs with prefetching for efficiency
        bullet_jobs = BulletGenerationJob.objects.filter(
            cv_generation_id=generation_id
        ).select_related('artifact').order_by('created_at')

        bullet_points = BulletPoint.objects.filter(
            cv_generation_id=generation_id
        )

        return {
            # Core status fields
            'generation_id': str(generation.id),
            'status': generation.status,
            'progress_percentage': generation.progress_percentage,
            'error_message': generation.error_message or None,
            'created_at': generation.created_at.isoformat(),
            'completed_at': generation.completed_at.isoformat() if generation.completed_at else None,

            # Job information from related JobDescription
            'job_title': generation.job_description.role_title if generation.job_description else None,
            'company_name': generation.job_description.company_name if generation.job_description else None,

            # Phase tracking
            'current_phase': GenerationStatusService._determine_current_phase(generation),
            'phase_details': GenerationStatusService._build_phase_details(generation, bullet_jobs),

            # Sub-job aggregation
            'bullet_generation_jobs': GenerationStatusService._build_job_summaries(bullet_jobs),

            # Processing metrics
            'processing_metrics': GenerationStatusService._aggregate_processing_metrics(
                generation, bullet_jobs
            ),

            # Quality metrics
            'quality_metrics': GenerationStatusService._aggregate_quality_metrics(bullet_points)
        }

    @staticmethod
    def _determine_current_phase(generation: GeneratedDocument) -> str:
        """Determine current workflow phase based on status."""
        phase_map = {
            'pending': 'bullet_generation',
            'processing': 'bullet_generation',
            'bullets_ready': 'bullet_review',
            'bullets_approved': 'assembly',
            'assembling': 'assembly',
            'completed': 'completed',
            'failed': 'completed'  # Terminal state
        }
        return phase_map.get(generation.status, 'bullet_generation')

    @staticmethod
    def _build_phase_details(
        generation: GeneratedDocument,
        bullet_jobs
    ) -> Dict[str, Any]:
        """Build phase-specific status details."""

        # Bullet generation phase metrics
        total_jobs = bullet_jobs.count()
        completed_jobs = bullet_jobs.filter(status='completed').count()

        # Count actual BulletPoint instances created for this generation
        bullets_generated = BulletPoint.objects.filter(
            cv_generation_id=generation.id
        ).count()

        # Determine bullet generation phase status
        bullet_phase_status = 'pending'
        if generation.status in ['processing', 'bullets_ready']:
            if completed_jobs == 0 and total_jobs > 0:
                bullet_phase_status = 'pending'
            elif 0 < completed_jobs < total_jobs:
                bullet_phase_status = 'in_progress'
            elif completed_jobs == total_jobs and total_jobs > 0:
                bullet_phase_status = 'completed'
        elif generation.status in ['bullets_approved', 'assembling', 'completed']:
            bullet_phase_status = 'completed'

        # Assembly phase status
        assembly_status = 'not_started'
        if generation.status == 'assembling':
            assembly_status = 'in_progress'
        elif generation.status == 'completed':
            assembly_status = 'completed'
        elif generation.status == 'failed' and generation.assembled_at:
            assembly_status = 'failed'

        return {
            'bullet_generation': {
                'status': bullet_phase_status,
                'artifacts_total': total_jobs,
                'artifacts_processed': completed_jobs,
                'bullets_generated': bullets_generated,
                'started_at': generation.created_at.isoformat() if total_jobs > 0 else None,
                'completed_at': generation.bullets_generated_at.isoformat() if generation.bullets_generated_at else None
            },
            'assembly': {
                'status': assembly_status,
                'started_at': generation.bullets_generated_at.isoformat()
                    if generation.status in ['assembling', 'completed'] and generation.bullets_generated_at else None,
                'completed_at': generation.assembled_at.isoformat() if generation.assembled_at else None
            }
        }

    @staticmethod
    def _build_job_summaries(bullet_jobs) -> List[Dict[str, Any]]:
        """Build per-job status summaries."""
        summaries = []
        for job in bullet_jobs:
            # Count actual BulletPoint instances for this job
            # (more reliable than job.generated_bullets JSONField)
            bullets_count = BulletPoint.objects.filter(
                artifact_id=job.artifact_id,
                cv_generation_id=job.cv_generation_id
            ).count()

            summaries.append({
                'job_id': str(job.id),
                'artifact_id': job.artifact_id,
                'artifact_title': job.artifact.title,
                'status': job.status,
                'bullets_generated': bullets_count,
                'processing_duration_ms': job.processing_duration_ms,
                'error_message': job.error_message or None
            })

        return summaries

    @staticmethod
    def _aggregate_processing_metrics(
        generation: GeneratedDocument,
        bullet_jobs
    ) -> Dict[str, Any]:
        """Aggregate processing metrics from all jobs."""

        aggregates = bullet_jobs.aggregate(
            total_duration=Sum('processing_duration_ms'),
            total_cost=Sum('llm_cost_usd'),
            total_tokens=Sum('tokens_used')
        )

        return {
            'total_duration_ms': aggregates['total_duration'],
            'total_cost_usd': float(aggregates['total_cost']) if aggregates['total_cost'] else None,
            'total_tokens_used': aggregates['total_tokens'],
            'model_version': generation.model_version
        }

    @staticmethod
    def _aggregate_quality_metrics(bullet_points) -> Dict[str, Any]:
        """Aggregate quality metrics from bullet points."""

        if not bullet_points.exists():
            return {
                'average_bullet_quality': None,
                'average_keyword_relevance': None,
                'bullets_approved': 0,
                'bullets_rejected': 0,
                'bullets_edited': 0
            }

        aggregates = bullet_points.aggregate(
            avg_quality=Avg('quality_score'),
            avg_relevance=Avg('keyword_relevance_score')
        )

        approved_count = bullet_points.filter(user_approved=True).count()
        rejected_count = bullet_points.filter(user_rejected=True).count()
        edited_count = bullet_points.filter(user_edited=True).count()

        return {
            'average_bullet_quality': float(aggregates['avg_quality']) if aggregates['avg_quality'] else None,
            'average_keyword_relevance': float(aggregates['avg_relevance']) if aggregates['avg_relevance'] else None,
            'bullets_approved': approved_count,
            'bullets_rejected': rejected_count,
            'bullets_edited': edited_count
        }
