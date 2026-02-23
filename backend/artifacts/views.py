from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
# from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import Artifact, ArtifactProcessingJob, UploadedFile, Evidence
from .serializers import (
    ArtifactSerializer, ArtifactCreateSerializer, ArtifactUpdateSerializer,
    ArtifactProcessingJobSerializer, UploadedFileSerializer,
    EvidenceCreateSerializer, EvidenceUpdateSerializer,
    EnrichedContentUpdateSerializer
)
from .tasks import enrich_artifact  # process_artifact_upload removed (ft-023, dead code)
from .utils import FileValidator
from django.core.exceptions import ValidationError as DjangoValidationError
import uuid
import os
import logging

logger = logging.getLogger(__name__)


class ArtifactListCreateView(generics.ListCreateAPIView):
    """
    List user's artifacts or create a new one.

    Optimized with prefetch_related to avoid N+1 queries when loading
    evidence links and their enhanced content.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Prefetch
        from llm_services.models import EnhancedEvidence

        queryset = Artifact.objects.filter(user=self.request.user)

        # Show all artifacts regardless of status - users can resume incomplete wizards
        # Status filtering can be added via query param if needed: ?status=complete

        return queryset.prefetch_related(
            'evidence',  # Prefetch all evidence links in one query
            Prefetch(
                'evidence__enhanced_version',  # Prefetch enhanced evidence for each evidence
                queryset=EnhancedEvidence.objects.all()
            )
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ArtifactCreateSerializer
        return ArtifactSerializer

    # @method_decorator(ratelimit(key='user', rate='50/h', method='POST'))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ArtifactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific artifact."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'  # Model field to lookup by
    lookup_url_kwarg = 'artifact_id'  # URL parameter name (ADR-039)

    def get_queryset(self):
        return Artifact.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ArtifactUpdateSerializer
        return ArtifactSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def artifact_processing_status(request, artifact_id):
    """
    Get processing status for an artifact.
    Implements the status checking from Feature 001.
    """
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)
        processing_job = artifact.processing_jobs.order_by('-created_at').first()

        if not processing_job:
            return Response({
                'error': 'No processing job found for this artifact'
            }, status=status.HTTP_404_NOT_FOUND)

        # Count evidence links
        total_evidence_count = artifact.evidence.count()
        processed_evidence_count = artifact.evidence.filter(
            last_validated__isnull=False
        ).count()

        return Response({
            'artifact_id': artifact_id,
            'status': processing_job.status,
            'progress_percentage': processing_job.progress_percentage,
            'error_message': processing_job.error_message,
            'processed_evidence_count': processed_evidence_count,
            'total_evidence_count': total_evidence_count,
            'created_at': processing_job.created_at,
            'completed_at': processing_job.completed_at
        })

    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@transaction.atomic  # Ensure atomic transaction for Evidence creation
def upload_artifact_files(request, artifact_id):
    """
    Upload files to a specific artifact.

    NEW (ft-010): Implements file verification and transaction coordination
    to prevent race conditions where enrichment runs before Evidence is committed.
    """
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)
    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)

    files = request.FILES.getlist('files')
    if not files:
        return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_files = []
    for file in files:
        serializer = UploadedFileSerializer(data={'file': file}, context={'request': request})
        if serializer.is_valid():
            uploaded_file = serializer.save()

            # NEW: Verify file accessibility (Layer 3 validation from ADR)
            full_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.file.name)
            if not os.path.exists(full_path):
                logger.error(f"File not accessible after upload: {full_path}")
                logger.error(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
                logger.error(f"Current working directory: {os.getcwd()}")
                return Response({
                    'error': f'File not accessible: {file.name}',
                    'details': 'Uploaded file could not be verified on server'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create Evidence entry so uploaded files appear in artifact.evidence_links
            Evidence.objects.create(
                artifact=artifact,
                url=f"/media/{uploaded_file.file.name}",
                evidence_type='document',
                description=uploaded_file.original_filename,
                file_path=uploaded_file.file.name,
                file_size=uploaded_file.file_size,
                mime_type=uploaded_file.mime_type
            )

            uploaded_files.append({
                'file_id': uploaded_file.id,
                'filename': uploaded_file.original_filename,
                'size': uploaded_file.file_size,
                'mime_type': uploaded_file.mime_type
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Enrichment is now auto-triggered by Evidence post_save signal (ft-025, ADR-030)
    # No need for explicit trigger here - the signal handler in artifacts/signals.py
    # automatically triggers enrichment whenever Evidence is created, regardless of source type.
    # This eliminates code duplication and ensures consistent behavior across all evidence sources.
    # Related: ft-025 (GitHub enrichment fix), ft-010 (original auto-enrichment), ADR-030 (signal-based trigger)

    return Response({'uploaded_files': uploaded_files}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser])
# @ratelimit(key='user', rate='100/h', method='POST')
def upload_file(request):
    """
    Simple file upload endpoint for individual files.
    """
    serializer = UploadedFileSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        uploaded_file = serializer.save()
        return Response({
            'file_id': uploaded_file.id,
            'filename': uploaded_file.original_filename,
            'size': uploaded_file.file_size,
            'mime_type': uploaded_file.mime_type,
            'url': uploaded_file.file.url if uploaded_file.file else None
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def artifact_suggestions(request):
    """
    Get technology suggestions based on common skills taxonomy.
    """
    # Common technology suggestions
    technology_suggestions = [
        'Python', 'JavaScript', 'TypeScript', 'React', 'Node.js', 'Django',
        'Flask', 'FastAPI', 'Vue.js', 'Angular', 'HTML', 'CSS', 'SASS',
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
        'AWS', 'Azure', 'GCP', 'Git', 'Jenkins', 'GitHub Actions',
        'Machine Learning', 'Data Science', 'TensorFlow', 'PyTorch',
        'REST API', 'GraphQL', 'Microservices', 'Agile', 'Scrum'
    ]

    # Filter based on query parameter
    query = request.GET.get('q', '').lower()
    if query:
        filtered_suggestions = [
            tech for tech in technology_suggestions
            if query in tech.lower()
        ]
        return Response({
            'suggestions': filtered_suggestions[:10]
        })

    return Response({
        'suggestions': technology_suggestions[:20]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def trigger_artifact_enrichment(request, artifact_id):
    """
    Trigger LLM-powered enrichment for an existing artifact (Phase 1 extraction).
    This can be used to re-enrich artifacts after adding new evidence.

    Note:
        Sets artifact.status='processing' BEFORE triggering async task to prevent
        race condition where frontend polls and sees old status.

    Returns:
        202: Enrichment task started successfully
        404: Artifact not found
        400: No evidence sources
        500: Failed to start enrichment
    """
    try:
        # Verify artifact exists and user owns it
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # VALIDATE: Check artifact has at least one evidence source (v1.2.0)
        evidence_count = Evidence.objects.filter(artifact=artifact).count()
        if evidence_count == 0:
            return Response({
                'error': 'Cannot enrich artifact with no evidence sources. Please add GitHub links or upload files.',
                'validation_error': 'no_evidence_sources',
                'evidence_count': 0
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update artifact status to 'processing' BEFORE triggering task (prevents race condition)
        artifact.status = 'processing'
        artifact.last_wizard_step = 5  # Step 5: Processing
        artifact.save()

        # Trigger enrichment task (Phase 1: Per-source extraction)
        task = enrich_artifact.delay(
            artifact_id=artifact_id,
            user_id=request.user.id
        )

        return Response({
            'status': 'processing',
            'artifact_id': artifact_id,
            'task_id': str(task.id),
            'message': 'Enrichment task started successfully'
        }, status=status.HTTP_202_ACCEPTED)

    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Failed to start enrichment',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def artifact_enrichment_status(request, artifact_id):
    """
    Get the status of artifact enrichment processing.

    Returns enrichment-specific information including:
    - Processing status (pending/processing/completed/failed)
    - Sources processed/successful counts
    - Processing confidence
    - Cost and timing metrics

    Returns:
        200: Status retrieved successfully
        404: Artifact not found
    """
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get the most recent processing job
        processing_job = artifact.processing_jobs.order_by('-created_at').first()

        # Check if artifact has enrichment data (regardless of processing job status)
        has_enrichment = bool(artifact.unified_description)

        if not processing_job:
            # No processing job exists - determine status from enrichment data
            if has_enrichment:
                # Artifact has enrichment (manual or from deleted job) - show as completed
                return Response({
                    'artifact_id': artifact_id,
                    'status': 'completed',
                    'progress_percentage': 100,
                    'has_enrichment': True,
                    'enrichment': {
                        'technologies_count': len(artifact.enriched_technologies or []),
                        'achievements_count': len(artifact.enriched_achievements or []),
                        'unified_description_length': len(artifact.unified_description or ''),
                    }
                })
            else:
                # No enrichment and no job - truly not started
                return Response({
                    'artifact_id': artifact_id,
                    'status': 'not_started',
                    'progress_percentage': 0,
                    'has_enrichment': False,
                    'message': 'No enrichment has been performed yet'
                })

        # Extract enrichment metadata if available
        enrichment_metadata = processing_job.metadata_extracted or {}

        response_data = {
            'artifact_id': artifact_id,
            'status': processing_job.status,
            'progress_percentage': processing_job.progress_percentage,
            'error_message': processing_job.error_message,
            'created_at': processing_job.created_at,
            'completed_at': processing_job.completed_at,
            'has_enrichment': has_enrichment,
        }

        # Add enrichment-specific metadata if available
        # NEW: Include enrichment metadata for both success and failure cases (for quality warnings)
        if enrichment_metadata.get('enrichment_success') or enrichment_metadata.get('validation_failed'):
            response_data['enrichment'] = {
                'sources_processed': enrichment_metadata.get('sources_processed', 0),
                'sources_successful': enrichment_metadata.get('sources_successful', 0),
                'processing_confidence': enrichment_metadata.get('processing_confidence', 0.0),
                'total_cost_usd': enrichment_metadata.get('total_cost_usd', 0.0),
                'processing_time_ms': enrichment_metadata.get('processing_time_ms', 0),
                'unified_description_length': enrichment_metadata.get('unified_description_length', 0),
                'technologies_count': enrichment_metadata.get('technologies_count', 0),
                'achievements_count': enrichment_metadata.get('achievements_count', 0),
                'quality_warnings': enrichment_metadata.get('quality_warnings', []),  # NEW: Include quality warnings
            }

        return Response(response_data)

    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_enriched_content(request, artifact_id):
    """
    Update enriched content fields for an artifact.
    Allows users to manually edit LLM-generated enriched content.

    Request body:
        {
            "unified_description": "...",  # Optional
            "enriched_technologies": [...],  # Optional
            "enriched_achievements": [...]  # Optional
        }

    Returns:
        200: Enriched content updated successfully
        400: Invalid data
        404: Artifact not found
    """
    try:
        # Verify artifact exists and user owns it
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Validate and update enriched content
        serializer = EnrichedContentUpdateSerializer(
            artifact,
            data=request.data,
            partial=True  # Allow partial updates
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                'message': 'Enriched content updated successfully',
                'artifact_id': artifact_id,
                'updated_fields': list(request.data.keys()),
                'enriched_content': {
                    'unified_description': artifact.unified_description,
                    'enriched_technologies': artifact.enriched_technologies,
                    'enriched_achievements': artifact.enriched_achievements,
                    'processing_confidence': artifact.processing_confidence
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def suggest_artifacts_for_job(request):
    """
    Suggest artifacts ranked by relevance to a job description.

    Implements ft-007: Manual Artifact Selection with Keyword Ranking

    Request body:
        {
            "job_description": "Looking for a full-stack developer...",  # Required
            "limit": 10  # Optional, default 10
        }

    Returns:
        200: Ranked artifacts with relevance scores
        400: Invalid request (missing job_description, invalid limit, job_description too short)
    """
    from llm_services.services.core.artifact_ranking_service import ArtifactRankingService
    import asyncio

    # Validate job_description
    job_description = request.data.get('job_description', '').strip()
    if not job_description:
        return Response({
            'error': 'job_description is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if len(job_description) < 10:
        return Response({
            'error': 'job_description must be at least 10 characters'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate limit parameter
    limit = request.data.get('limit', 10)
    try:
        limit = int(limit)
        if limit < 1 or limit > 50:
            return Response({
                'error': 'limit must be between 1 and 50'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError):
        return Response({
            'error': 'limit must be a valid integer'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get user's artifacts
    user_artifacts = Artifact.objects.filter(user=request.user).values(
        'id', 'title', 'description', 'technologies', 'enriched_technologies',
        'start_date', 'end_date', 'artifact_type'
    )

    if not user_artifacts:
        return Response({
            'artifacts': [],
            'total_artifacts': 0,
            'returned_count': 0
        })

    # Extract keywords from job description (simple split for now)
    # TODO: Use LLM or NLP for better keyword extraction
    job_keywords = []
    for word in job_description.split():
        word_clean = word.strip('.,!?;:()[]{}"\'-').lower()
        if len(word_clean) >= 2:  # Skip very short words
            # Capitalize first letter for display
            job_keywords.append(word_clean.capitalize())

    # Rank artifacts using ArtifactRankingService
    ranking_service = ArtifactRankingService()

    # Convert QuerySet to list of dicts
    artifacts_list = list(user_artifacts)

    # Run async ranking
    ranked_artifacts = asyncio.run(
        ranking_service.rank_artifacts_by_relevance(
            artifacts_list,
            job_keywords,
            strategy='keyword'
        )
    )

    # Limit results
    ranked_artifacts = ranked_artifacts[:limit]

    return Response({
        'artifacts': ranked_artifacts,
        'total_artifacts': len(user_artifacts),
        'returned_count': len(ranked_artifacts)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def artifact_enrichment_debug(request, artifact_id):
    """
    Diagnostic endpoint for debugging enrichment issues.

    Returns detailed enrichment metadata including:
    - Evidence sources and their extraction status
    - Quality validation results (errors + warnings)
    - Individual source extraction details
    - Processing metadata and costs

    Returns:
        200: Debug information retrieved successfully
        404: Artifact not found
    """
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get evidence sources
        evidence_sources = []
        for evidence in Evidence.objects.filter(artifact=artifact):
            evidence_sources.append({
                'id': evidence.id,
                'url': evidence.url,
                'evidence_type': evidence.evidence_type,
                'description': evidence.description,
                'file_path': evidence.file_path,
                'is_accessible': evidence.is_accessible,
                'validation_metadata': evidence.validation_metadata,
            })

        # Get most recent processing job
        processing_job = artifact.processing_jobs.order_by('-created_at').first()

        debug_info = {
            'artifact_id': artifact_id,
            'artifact_title': artifact.title,
            'evidence_count': len(evidence_sources),
            'evidence_sources': evidence_sources,
        }

        if processing_job:
            metadata = processing_job.metadata_extracted or {}

            debug_info['processing_job'] = {
                'id': str(processing_job.id),
                'status': processing_job.status,
                'created_at': processing_job.created_at,
                'completed_at': processing_job.completed_at,
                'error_message': processing_job.error_message,
            }

            debug_info['enrichment_metrics'] = {
                'sources_processed': metadata.get('sources_processed', 0),
                'sources_successful': metadata.get('sources_successful', 0),
                'processing_confidence': metadata.get('processing_confidence', 0.0),
                'total_cost_usd': metadata.get('total_cost_usd', 0.0),
                'processing_time_ms': metadata.get('processing_time_ms', 0),
            }

            debug_info['quality_validation'] = {
                'validation_failed': metadata.get('validation_failed', False),
                'quality_score': metadata.get('quality_score', 0.0),
                'quality_warnings': metadata.get('quality_warnings', []),
            }

            debug_info['enrichment_results'] = {
                'unified_description_length': metadata.get('unified_description_length', 0),
                'technologies_count': metadata.get('technologies_count', 0),
                'achievements_count': metadata.get('achievements_count', 0),
            }

            # Get individual source extractions from EnhancedEvidence
            from llm_services.models import EnhancedEvidence
            source_extractions = []
            for evidence in artifact.evidence.all():
                try:
                    enhanced = evidence.enhanced_version
                    source_extractions.append({
                        'source_url': evidence.url,
                        'success': True,
                        'confidence': enhanced.processing_confidence,
                        'error_message': '',
                        'data_keys': list(enhanced.processed_content.keys()) if enhanced.processed_content else [],
                        'accepted': enhanced.accepted,
                    })
                except EnhancedEvidence.DoesNotExist:
                    # Evidence exists but no EnhancedEvidence created (extraction failed)
                    source_extractions.append({
                        'source_url': evidence.url,
                        'success': False,
                        'confidence': 0.0,
                        'error_message': 'Extraction failed or not yet processed',
                        'data_keys': [],
                        'accepted': False,
                    })
            debug_info['source_extractions'] = source_extractions
        else:
            debug_info['processing_job'] = None
            debug_info['message'] = 'No enrichment has been performed yet'

        # Current artifact state
        debug_info['current_artifact_state'] = {
            'has_unified_description': bool(artifact.unified_description),
            'unified_description_length': len(artifact.unified_description),
            'processing_confidence': artifact.processing_confidence,
            'technologies_count': len(artifact.enriched_technologies),
            'achievements_count': len(artifact.enriched_achievements),
        }

        return Response(debug_info)

    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# Evidence Review & Acceptance API Endpoints (ft-045)
# ============================================================================


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_evidence(request, artifact_id, evidence_id):
    """
    Mark an EnhancedEvidence as accepted by the user (ft-045).

    POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/accept/

    Request Body:
        {
            "review_notes": "Optional notes about acceptance"
        }

    Returns:
        200: Evidence accepted successfully
        404: Artifact or evidence not found
    """
    from llm_services.models import EnhancedEvidence
    from llm_services.serializers import EnhancedEvidenceSerializer
    from django.utils import timezone

    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get the EnhancedEvidence for this artifact's evidence
        enhanced_evidence = EnhancedEvidence.objects.get(
            id=evidence_id,
            evidence__artifact=artifact,
            user=request.user
        )

        # Mark as accepted
        enhanced_evidence.accepted = True
        enhanced_evidence.accepted_at = timezone.now()

        # Optional review notes
        review_notes = request.data.get('review_notes')
        if review_notes:
            enhanced_evidence.review_notes = review_notes

        enhanced_evidence.save()

        serializer = EnhancedEvidenceSerializer(enhanced_evidence)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)
    except EnhancedEvidence.DoesNotExist:
        return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_evidence(request, artifact_id, evidence_id):
    """
    Mark an EnhancedEvidence as rejected by the user (ft-045).

    POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/reject/

    Returns:
        200: Evidence rejected successfully
        404: Artifact or evidence not found
    """
    from llm_services.models import EnhancedEvidence
    from llm_services.serializers import EnhancedEvidenceSerializer

    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get the EnhancedEvidence
        enhanced_evidence = EnhancedEvidence.objects.get(
            id=evidence_id,
            evidence__artifact=artifact,
            user=request.user
        )

        # Mark as rejected (reviewed but not accepted)
        # Keep/set timestamp to distinguish from pending (never reviewed)
        enhanced_evidence.accepted = False
        if enhanced_evidence.accepted_at is None:
            from django.utils import timezone
            enhanced_evidence.accepted_at = timezone.now()
        enhanced_evidence.save()

        serializer = EnhancedEvidenceSerializer(enhanced_evidence)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)
    except EnhancedEvidence.DoesNotExist:
        return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def edit_evidence_content(request, artifact_id, evidence_id):
    """
    Update the processed_content of an EnhancedEvidence (inline editing, ft-045).

    PATCH /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/content/

    Request Body:
        {
            "processed_content": {
                "summary": "User-edited summary",
                "technologies": ["React", "Django"],
                "achievements": ["Built X", "Improved Y"]
            }
        }

    Returns:
        200: Content updated successfully
        400: Invalid content structure
        404: Artifact or evidence not found
    """
    from llm_services.models import EnhancedEvidence
    from llm_services.serializers import EnhancedEvidenceUpdateSerializer

    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get the EnhancedEvidence
        enhanced_evidence = EnhancedEvidence.objects.get(
            id=evidence_id,
            evidence__artifact=artifact,
            user=request.user
        )

        # Use serializer for validation
        serializer = EnhancedEvidenceUpdateSerializer(
            enhanced_evidence,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)
    except EnhancedEvidence.DoesNotExist:
        return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_evidence_acceptance_status(request, artifact_id):
    """
    Get acceptance status summary for all evidence in an artifact (ft-045).

    GET /api/v1/artifacts/{artifact_id}/evidence-acceptance-status/

    Returns:
        {
            "can_finalize": true/false,
            "total_evidence": 5,
            "accepted": 3,
            "rejected": 1,
            "pending": 1,
            "evidence_details": [
                {
                    "id": 1,
                    "title": "repo-name",
                    "content_type": "github",
                    "processed_content": {...},
                    "processing_confidence": 0.85,
                    "accepted": true,
                    "accepted_at": "2025-01-15T10:30:00Z"
                },
                ...
            ]
        }

    Returns:
        200: Status retrieved successfully
        404: Artifact not found
    """
    from llm_services.models import EnhancedEvidence
    from llm_services.serializers import EnhancedEvidenceSerializer

    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Get all EnhancedEvidence for this artifact
        enhanced_evidence_qs = EnhancedEvidence.objects.filter(
            evidence__artifact=artifact,
            user=request.user
        ).select_related('evidence')

        total_evidence = enhanced_evidence_qs.count()
        accepted = enhanced_evidence_qs.filter(accepted=True).count()
        rejected = enhanced_evidence_qs.filter(accepted=False, accepted_at__isnull=False).count()
        pending = total_evidence - accepted - rejected

        # Can finalize only if ALL evidence is accepted
        can_finalize = (total_evidence > 0) and (accepted == total_evidence)

        # Serialize evidence details
        serializer = EnhancedEvidenceSerializer(enhanced_evidence_qs, many=True)

        return Response({
            'can_finalize': can_finalize,
            'total_evidence': total_evidence,
            'accepted': accepted,
            'rejected': rejected,
            'pending': pending,
            'evidence_details': serializer.data
        }, status=status.HTTP_200_OK)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def finalize_evidence_review(request, artifact_id):
    """
    Finalize evidence review and trigger async LLM reunification (ft-045).

    POST /api/v1/artifacts/{artifact_id}/finalize-evidence-review/

    Preconditions:
        - ALL EnhancedEvidence must be accepted=True
        - Artifact must have at least one evidence source

    Returns:
        200: Reunification task triggered successfully
        403: Not all evidence accepted
        404: Artifact not found
        400: Bad request (validation failed)

    Note:
        Sets artifact.status='reunifying' BEFORE triggering async task to prevent
        race condition where frontend polls and sees old status.
    """
    from llm_services.models import EnhancedEvidence
    from .tasks import reunify_artifact_evidence

    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Check that ALL evidence is accepted
        enhanced_evidence_qs = EnhancedEvidence.objects.filter(
            evidence__artifact=artifact,
            user=request.user
        )

        total_evidence = enhanced_evidence_qs.count()
        accepted = enhanced_evidence_qs.filter(accepted=True).count()

        if total_evidence == 0:
            return Response({
                'error': 'No evidence sources found for this artifact'
            }, status=status.HTTP_400_BAD_REQUEST)

        if accepted != total_evidence:
            return Response({
                'error': f'All evidence must be accepted before finalization. {accepted}/{total_evidence} accepted.',
                'accepted': accepted,
                'total': total_evidence
            }, status=status.HTTP_403_FORBIDDEN)

        # Update artifact status to 'reunifying' BEFORE triggering task (prevents race condition)
        artifact.status = 'reunifying'
        artifact.last_wizard_step = 5  # Step 5: Evidence review finalized, reunification starting
        artifact.save()

        # Create processing job for tracking
        processing_job = ArtifactProcessingJob.objects.create(
            artifact=artifact,
            status='pending',
            job_type='phase2_reunification'
        )

        # Trigger async reunification task (Phase 2)
        reunify_artifact_evidence.delay(
            artifact_id=artifact_id,
            user_id=request.user.id,
            processing_job_id=processing_job.id
        )

        logger.info(
            f"[Phase 2] Reunification task triggered for artifact {artifact_id}, "
            f"job {processing_job.id}, status set to 'reunifying'"
        )

        return Response({
            'message': 'Evidence reunification task started',
            'artifactId': artifact_id,
            'processingJobId': str(processing_job.id),
            'phase': 2
        }, status=status.HTTP_200_OK)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def accept_artifact(request, artifact_id):
    """
    Accept final artifact after reunification (Step 6 Phase 2 of 6-step wizard).

    POST /api/v1/artifacts/{artifact_id}/accept-artifact/

    Preconditions:
        - Artifact must have status='review_finalized'
        - Artifact must belong to the requesting user

    Returns:
        200: Artifact accepted successfully (status='complete')
        400: Bad request (artifact not in review_finalized state)
        404: Artifact not found

    Note:
        Sets artifact.status='complete' and wizard_completed_at timestamp atomically.
    """
    try:
        # Verify artifact ownership
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)

        # Verify artifact is in review_finalized state
        if artifact.status != 'review_finalized':
            return Response({
                'error': f'Artifact must be in review_finalized state to accept. Current status: {artifact.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Accept artifact - set status to complete
        artifact.status = 'complete'
        artifact.wizard_completed_at = timezone.now()
        artifact.last_wizard_step = 6  # Step 6 Phase 2: Artifact accepted (6-step wizard complete)
        artifact.save()

        logger.info(
            f"[Step 6] Artifact {artifact_id} accepted by user, "
            f"status set to 'complete', 6-step wizard finalized"
        )

        return Response({
            'message': 'Artifact accepted successfully',
            'artifactId': artifact_id,
            'status': 'complete'
        }, status=status.HTTP_200_OK)

    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)