"""
Celery tasks for artifact processing.
"""

import os
import requests
import logging
import asyncio
from datetime import timedelta
from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone
from PyPDF2 import PdfReader
from .models import Artifact, ArtifactProcessingJob, Evidence
import json

logger = logging.getLogger(__name__)


def _check_processing_idempotency(artifact_id, job_type, force=False):
    """
    Check if an artifact processing job is already in progress or completed.

    Prevents duplicate task triggers and handles stale jobs (>15 min).

    Args:
        artifact_id: ID of the artifact being processed
        job_type: Type of job ('phase1_extraction' or 'phase2_reunification')
        force: If True, bypass idempotency checks (for manual debugging)

    Returns:
        dict or None: If duplicate detected, returns skip notification dict.
                     If job can proceed, returns None.
    """
    if force:
        return None  # Bypass idempotency checks

    existing_job = ArtifactProcessingJob.objects.filter(
        artifact_id=artifact_id,
        job_type=job_type,
        status__in=['processing', 'completed']
    ).order_by('-created_at').first()

    if not existing_job:
        return None  # No existing job, proceed

    # Check if job is stale (>15 minutes old and still "processing")
    if existing_job.status == 'processing':
        job_age = timezone.now() - existing_job.created_at
        if job_age > timedelta(minutes=15):
            logger.warning(
                f"Stale {job_type} job {existing_job.id} detected for artifact {artifact_id} "
                f"(age: {job_age.seconds // 60} minutes), marking as failed and allowing retry"
            )
            existing_job.status = 'failed'
            existing_job.error_message = 'Timeout: Processing exceeded 15 minutes'
            existing_job.save()
            return None  # Allow retry
        else:
            logger.warning(
                f"{job_type} already processing for artifact {artifact_id}, "
                f"skipping duplicate trigger (existing job: {existing_job.id})"
            )
            return {
                'skipped': True,
                'reason': 'already_processing',
                'artifact_id': artifact_id,
                'existing_job_id': str(existing_job.id),
                'existing_job_status': existing_job.status,
                'created_at': existing_job.created_at.isoformat()
            }
    else:  # status == 'completed'
        logger.warning(
            f"{job_type} already completed for artifact {artifact_id}, "
            f"skipping duplicate trigger (existing job: {existing_job.id})"
        )
        return {
            'skipped': True,
            'reason': 'already_completed',
            'artifact_id': artifact_id,
            'existing_job_id': str(existing_job.id),
            'existing_job_status': existing_job.status,
            'created_at': existing_job.created_at.isoformat()
        }


# REMOVED (ft-023): process_artifact_upload() task was never called (dead code)
# Originally intended to auto-trigger enrichment (lines 100-103), but never invoked.
# Backend now auto-triggers enrichment via transaction.on_commit() in views.py (ft-010)


@shared_task
def enrich_artifact(artifact_id, user_id, processing_job_id=None, force=False):
    """
    LLM-powered enrichment of artifact using ArtifactEnrichmentService.
    This task can be triggered independently for re-enrichment.

    NEW (ft-023): Idempotency protection - skips if already processing/completed.

    Args:
        artifact_id: ID of the artifact to enrich
        user_id: ID of the user (for LLM tracking/costs)
        processing_job_id: Optional processing job ID for tracking
        force: If True, bypass idempotency checks (for manual debugging only)

    Returns:
        dict: Enrichment results including success status, enriched fields, and metadata
              OR skip notification with reason if duplicate detected
    """
    try:
        from llm_services.services.core.artifact_enrichment_service import ArtifactEnrichmentService

        # Idempotency guard - check if already processing or completed (ft-023)
        skip_result = _check_processing_idempotency(
            artifact_id=artifact_id,
            job_type='phase1_extraction',
            force=force
        )
        if skip_result:
            return skip_result

        # Get artifact object (needed throughout the task)
        artifact = Artifact.objects.get(id=artifact_id)

        # Create or get processing job for tracking
        if processing_job_id:
            try:
                processing_job = ArtifactProcessingJob.objects.get(id=processing_job_id)
            except ArtifactProcessingJob.DoesNotExist:
                processing_job = ArtifactProcessingJob.objects.create(
                    artifact=artifact,
                    status='processing',
                    job_type='phase1_extraction'
                )
        else:
            processing_job = ArtifactProcessingJob.objects.create(
                artifact=artifact,
                status='processing',
                job_type='phase1_extraction'
            )

        # Update status to enriching
        processing_job.status = 'processing'
        processing_job.progress_percentage = 0
        processing_job.save()

        # Set artifact status to 'processing' (idempotent - API endpoint may have already set this)
        artifact.status = 'processing'
        artifact.last_wizard_step = 5  # Step 5: Processing
        artifact.save()

        logger.info(f"Starting Phase 1 enrichment (per-source extraction) for artifact {artifact_id}")

        # PRE-FLIGHT CHECK: Verify artifact has evidence sources
        evidence_count = Evidence.objects.filter(artifact_id=artifact_id).count()
        if evidence_count == 0:
            logger.warning(f"Cannot enrich artifact {artifact_id}: No evidence sources available")
            processing_job.status = 'failed'
            processing_job.error_message = 'Cannot enrich artifact with no evidence sources. Please add GitHub links or upload documents.'
            processing_job.progress_percentage = 0
            processing_job.metadata_extracted = {
                'enrichment_success': False,
                'validation_failed': True,
                'error_type': 'no_evidence_sources'
            }
            processing_job.save()

            # Revert artifact status to draft (matching exception handler behavior)
            artifact.status = 'draft'
            artifact.save()

            return {
                'success': False,
                'artifact_id': artifact_id,
                'processing_job_id': str(processing_job.id),
                'error': 'No evidence sources available for enrichment'
            }

        # Run async Phase 1 enrichment service (per-source extraction only)
        from common.exceptions import EnrichmentError, ArtifactNotFoundError, InsufficientDataError

        service = ArtifactEnrichmentService()

        # Create event loop for async execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Phase 1: Extract content from each source WITHOUT unification (ft-045)
            result = loop.run_until_complete(
                service.extract_per_source_only(
                    artifact_id=artifact_id,
                    job_id=processing_job.id,
                    user_id=user_id
                )
            )
        except (ArtifactNotFoundError, InsufficientDataError, EnrichmentError) as e:
            # Service raised an exception - Phase 1 extraction failed
            processing_job.status = 'failed'
            processing_job.error_message = str(e)
            processing_job.metadata_extracted = {
                'enrichment_success': False,
                'error_type': type(e).__name__,
                'phase': 1,
            }
            processing_job.save()

            # Revert artifact status to draft
            artifact = Artifact.objects.get(id=artifact_id)
            artifact.status = 'draft'
            artifact.save()

            logger.error(f"[Phase 1] Extraction failed for artifact {artifact_id}: {e}")

            return {
                'success': False,
                'artifact_id': artifact_id,
                'processing_job_id': str(processing_job.id),
                'error': str(e)
            }
        finally:
            loop.close()

        # Phase 1 extraction succeeded - update artifact status to 'review_pending'
        # Do NOT save unified_description yet (deferred to Phase 2 after user acceptance)
        logger.info(
            f"[Phase 1] Extraction completed for artifact {artifact_id}: "
            f"{result['enhanced_evidence_created']} EnhancedEvidence records created, "
            f"{result['sources_successful']}/{result['sources_processed']} sources successful"
        )

        # Update artifact status to 'review_pending' (ready for Step 5 Phase 2: user review)
        artifact = Artifact.objects.get(id=artifact_id)
        artifact.status = 'review_pending'
        artifact.last_wizard_step = 5  # Step 5 Phase 1 complete: awaiting user evidence review
        artifact.save()

        processing_job.status = 'completed'
        processing_job.progress_percentage = 100
        processing_job.metadata_extracted = {
            'enrichment_success': True,
            'phase': 1,  # Phase 1 complete
            'enhanced_evidence_created': result['enhanced_evidence_created'],
            'sources_processed': result['sources_processed'],
            'sources_successful': result['sources_successful'],
            'total_cost_usd': result['total_cost_usd'],
            'processing_time_ms': result['processing_time_ms'],
        }
        processing_job.completed_at = timezone.now()
        processing_job.save()

        logger.info(
            f"[Phase 1] Successfully completed per-source extraction for artifact {artifact_id}: "
            f"{result['sources_successful']}/{result['sources_processed']} sources, "
            f"cost=${result['total_cost_usd']:.4f}, "
            f"time={result['processing_time_ms']}ms - artifact status set to 'review_pending'"
        )

        return {
            'success': True,
            'artifact_id': artifact_id,
            'processing_job_id': str(processing_job.id),
            'phase': 1,
            'enrichment_metadata': processing_job.metadata_extracted
        }

    except Exception as e:
        logger.error(f"Error enriching artifact {artifact_id}: {e}", exc_info=True)

        # Update processing job if available
        try:
            if processing_job_id:
                processing_job = ArtifactProcessingJob.objects.get(id=processing_job_id)
                processing_job.status = 'failed'
                processing_job.error_message = str(e)
                processing_job.save()
        except:
            pass

        return {
            'success': False,
            'artifact_id': artifact_id,
            'error': str(e)
        }


@shared_task
def reunify_artifact_evidence(artifact_id, user_id, processing_job_id=None, force=False):
    """
    LLM-powered finalization of accepted evidence (Phase 2 of ft-045).

    Combines user-accepted and edited evidence into unified artifact description.
    This task is triggered when user finalizes evidence review.

    Args:
        artifact_id: ID of the artifact to reunify
        user_id: ID of the user (for LLM tracking/costs)
        processing_job_id: Optional processing job ID for tracking
        force: If True, bypass idempotency checks (for manual debugging only)

    Returns:
        dict: Finalization results including success status, unified fields, and metadata
              OR skip notification with reason if duplicate detected
    """
    try:
        from llm_services.services.core.artifact_enrichment_service import ArtifactEnrichmentService
        from llm_services.models import EnhancedEvidence
        from common.exceptions import EnrichmentError, ArtifactNotFoundError, InsufficientDataError

        # Idempotency guard - check if already reunifying or completed
        skip_result = _check_processing_idempotency(
            artifact_id=artifact_id,
            job_type='phase2_reunification',
            force=force
        )
        if skip_result:
            return skip_result

        # Get artifact object (needed throughout the task)
        artifact = Artifact.objects.get(id=artifact_id)

        # Create or get processing job for tracking
        if processing_job_id:
            try:
                processing_job = ArtifactProcessingJob.objects.get(id=processing_job_id)
            except ArtifactProcessingJob.DoesNotExist:
                processing_job = ArtifactProcessingJob.objects.create(
                    artifact=artifact,
                    status='processing',
                    job_type='phase2_finalization'
                )
        else:
            processing_job = ArtifactProcessingJob.objects.create(
                artifact=artifact,
                status='processing',
                job_type='phase2_finalization'
            )

        # Update status to 'reunifying'
        processing_job.status = 'processing'
        processing_job.progress_percentage = 0
        processing_job.save()

        # Set artifact status to 'reunifying' (idempotent - API endpoint may have already set this)
        artifact.status = 'reunifying'
        artifact.last_wizard_step = 5  # Step 5: User finalized evidence review, Phase 2 reunification starting
        artifact.save()

        logger.info(f"Starting Phase 2 finalization for artifact {artifact_id}")

        # PRE-FLIGHT CHECK: Verify all evidence accepted
        enhanced_evidence_qs = EnhancedEvidence.objects.filter(
            evidence__artifact=artifact,
            user_id=user_id
        )
        total_evidence = enhanced_evidence_qs.count()
        accepted = enhanced_evidence_qs.filter(accepted=True).count()

        if total_evidence == 0:
            logger.warning(f"Cannot reunify artifact {artifact_id}: No evidence sources")
            processing_job.status = 'failed'
            processing_job.error_message = 'No evidence sources found for finalization'
            processing_job.save()

            artifact.status = 'review_pending'
            artifact.save()

            return {
                'success': False,
                'artifact_id': artifact_id,
                'processing_job_id': str(processing_job.id),
                'error': 'No evidence sources available'
            }

        if accepted != total_evidence:
            logger.warning(f"Cannot reunify: {accepted}/{total_evidence} accepted")
            processing_job.status = 'failed'
            processing_job.error_message = f'All evidence must be accepted. {accepted}/{total_evidence} accepted.'
            processing_job.save()

            artifact.status = 'review_pending'
            artifact.save()

            return {
                'success': False,
                'artifact_id': artifact_id,
                'processing_job_id': str(processing_job.id),
                'error': f'All evidence must be accepted. {accepted}/{total_evidence} accepted.'
            }

        # Run async Phase 2 finalization service
        service = ArtifactEnrichmentService()

        # Create event loop for async execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Phase 2: Reunify accepted evidence
            result = loop.run_until_complete(
                service.reunify_from_accepted_evidence(
                    artifact_id=artifact_id,
                    user_id=user_id
                )
            )
        except (ArtifactNotFoundError, InsufficientDataError, EnrichmentError) as e:
            # Service raised exception - Phase 2 failed
            processing_job.status = 'failed'
            processing_job.error_message = str(e)
            processing_job.metadata_extracted = {
                'finalization_success': False,
                'error_type': type(e).__name__,
                'phase': 2,
            }
            processing_job.save()

            # Revert artifact status to review_pending
            artifact = Artifact.objects.get(id=artifact_id)
            artifact.status = 'review_pending'
            artifact.save()

            logger.error(f"[Phase 2] Finalization failed for artifact {artifact_id}: {e}")

            return {
                'success': False,
                'artifact_id': artifact_id,
                'processing_job_id': str(processing_job.id),
                'error': str(e)
            }
        finally:
            loop.close()

        # Phase 2 succeeded - update to 'review_finalized' (awaiting user acceptance at Step 9)
        logger.info(
            f"[Phase 2] Finalization completed for artifact {artifact_id}: "
            f"unified_description updated, "
            f"confidence={result.get('processing_confidence', 0.0)}"
        )

        # Update artifact status to 'review_finalized' (Step 6 Phase 1: awaiting user acceptance)
        artifact = Artifact.objects.get(id=artifact_id)
        artifact.status = 'review_finalized'
        artifact.last_wizard_step = 6  # Step 6 Phase 1: Reunification complete, awaiting user acceptance
        artifact.save()

        processing_job.status = 'completed'
        processing_job.progress_percentage = 100
        processing_job.metadata_extracted = {
            'finalization_success': True,
            'phase': 2,  # Phase 2 complete
            'processing_confidence': result.get('processing_confidence', 0.0),
            'total_cost_usd': result.get('total_cost_usd', 0.0),
            'processing_time_ms': result.get('processing_time_ms', 0),
        }
        processing_job.completed_at = timezone.now()
        processing_job.save()

        logger.info(
            f"[Phase 2] Successfully completed reunification for artifact {artifact_id}: "
            f"status set to 'review_finalized', awaiting user acceptance at Step 6 Phase 2"
        )

        return {
            'success': True,
            'artifact_id': artifact_id,
            'processing_job_id': str(processing_job.id),
            'phase': 2,
            'finalization_metadata': processing_job.metadata_extracted
        }

    except Exception as e:
        logger.error(f"Error reunifying artifact {artifact_id}: {e}", exc_info=True)

        # Update processing job if available
        try:
            if processing_job_id:
                processing_job = ArtifactProcessingJob.objects.get(id=processing_job_id)
                processing_job.status = 'failed'
                processing_job.error_message = str(e)
                processing_job.save()
        except:
            pass

        return {
            'success': False,
            'artifact_id': artifact_id,
            'error': str(e)
        }


@shared_task
def mark_abandoned_artifacts():
    """
    Periodic task to mark stale artifacts as 'abandoned' (ft-045).

    Marks artifacts as abandoned if they've been stuck in:
    - 'draft', 'processing', or 'review_pending' status
    - For more than 24 hours (based on updated_at timestamp)

    Runs every 6 hours via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta

    # Define abandonment threshold (24 hours)
    abandonment_threshold = timezone.now() - timedelta(hours=24)

    # Find stale artifacts
    stale_artifacts = Artifact.objects.filter(
        status__in=['draft', 'processing', 'review_pending'],
        updated_at__lt=abandonment_threshold
    )

    count = stale_artifacts.count()

    if count == 0:
        logger.info("[Cleanup] No abandoned artifacts found")
        return {
            'abandoned_count': 0,
            'threshold': abandonment_threshold.isoformat()
        }

    # Mark as abandoned
    abandoned_ids = list(stale_artifacts.values_list('id', flat=True))
    stale_artifacts.update(status='abandoned')

    logger.info(f"[Cleanup] Marked {count} artifacts as abandoned: {abandoned_ids}")

    return {
        'abandoned_count': count,
        'artifact_ids': abandoned_ids,
        'threshold': abandonment_threshold.isoformat()
    }


def extract_pdf_metadata(file_path):
    """Extract metadata from PDF file."""
    try:
        if default_storage.exists(file_path):
            with default_storage.open(file_path, 'rb') as file:
                reader = PdfReader(file)
                metadata = reader.metadata

                extracted = {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': str(metadata.get('/CreationDate', '')),
                    'modification_date': str(metadata.get('/ModDate', '')),
                    'page_count': len(reader.pages)
                }

                # Extract text from first page for analysis
                if reader.pages:
                    first_page_text = reader.pages[0].extract_text()
                    extracted['first_page_text'] = first_page_text[:1000]  # First 1000 chars

                return extracted
    except Exception as e:
        logger.error(f"Error extracting PDF metadata from {file_path}: {e}")
    return {}


def validate_evidence_link(evidence_link):
    """Validate that an evidence link is accessible."""
    try:
        response = requests.head(evidence_link.url, timeout=10, allow_redirects=True)
        is_accessible = response.status_code == 200

        # Update evidence link
        evidence_link.is_accessible = is_accessible
        evidence_link.last_validated = timezone.now()
        evidence_link.validation_metadata = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'final_url': response.url
        }
        evidence_link.save()

        return {
            'status': 'success' if is_accessible else 'failed',
            'status_code': response.status_code,
            'accessible': is_accessible
        }

    except requests.RequestException as e:
        evidence_link.is_accessible = False
        evidence_link.last_validated = timezone.now()
        evidence_link.validation_metadata = {
            'error': str(e)
        }
        evidence_link.save()

        return {
            'status': 'error',
            'error': str(e),
            'accessible': False
        }


def analyze_github_repository(github_url):
    """Analyze GitHub repository and extract metadata."""
    try:
        # Parse GitHub URL
        parts = github_url.strip('/').split('/')
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1]

            # GitHub API call (requires token for higher rate limits)
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {}

            # Add GitHub token if available
            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f"token {github_token}"

            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                repo_data = response.json()

                # Get languages
                languages_url = repo_data.get('languages_url')
                languages = {}
                if languages_url:
                    lang_response = requests.get(languages_url, headers=headers, timeout=10)
                    if lang_response.status_code == 200:
                        languages = lang_response.json()

                # Get recent commits
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
                commits = []
                commits_response = requests.get(f"{commits_url}?per_page=5", headers=headers, timeout=10)
                if commits_response.status_code == 200:
                    commits_data = commits_response.json()
                    commits = [
                        {
                            'sha': commit['sha'][:7],
                            'message': commit['commit']['message'],
                            'date': commit['commit']['author']['date'],
                            'author': commit['commit']['author']['name']
                        }
                        for commit in commits_data
                    ]

                return {
                    'name': repo_data.get('name'),
                    'description': repo_data.get('description'),
                    'language': repo_data.get('language'),
                    'languages': languages,
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'created_at': repo_data.get('created_at'),
                    'updated_at': repo_data.get('updated_at'),
                    'topics': repo_data.get('topics', []),
                    'recent_commits': commits,
                    'default_branch': repo_data.get('default_branch'),
                    'size': repo_data.get('size'),
                    'open_issues': repo_data.get('open_issues_count', 0)
                }

    except Exception as e:
        logger.error(f"Error analyzing GitHub repository {github_url}: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_old_uploaded_files():
    """Cleanup uploaded files older than 24 hours."""
    from datetime import timedelta
    from .models import UploadedFile

    cutoff_time = timezone.now() - timedelta(hours=24)
    old_files = UploadedFile.objects.filter(created_at__lt=cutoff_time)

    deleted_count = 0
    for uploaded_file in old_files:
        try:
            # Delete file from storage
            if uploaded_file.file:
                default_storage.delete(uploaded_file.file.name)

            # Delete database record
            uploaded_file.delete()
            deleted_count += 1

        except Exception as e:
            logger.error(f"Error deleting old file {uploaded_file.id}: {e}")

    logger.info(f"Cleaned up {deleted_count} old uploaded files")
    return deleted_count