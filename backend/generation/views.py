from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
# from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from asgiref.sync import async_to_sync
from .models import GeneratedDocument, JobDescription, CVTemplate, GenerationFeedback, BulletPoint, BulletGenerationJob
from artifacts.models import Artifact
from .serializers import (
    GenerationRequestSerializer, GeneratedDocumentSerializer,
    GeneratedDocumentListSerializer, GeneratedDocumentDetailSerializer,
    CVTemplateSerializer, GenerationFeedbackSerializer, DocumentRatingSerializer,
    JobContextSerializer, BulletGenerationRequestSerializer,
    BulletPointSerializer, BulletApprovalSerializer,
    BulletValidationSerializer
)
from .services import BulletGenerationService, BulletValidationService, GenerationService
from .services.generation_status_service import GenerationStatusService
from .tasks import generate_document_task, prepare_generation_bullets_task, assemble_generation_task


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
# @ratelimit(key='user', rate='10/h', method='POST')
def create_generation(request):
    """
    Create a new document generation (CV, cover letter, etc.) based on job description and user artifacts.
    Implements ft-009 two-phase workflow:
    - Phase 1: Generate bullets for review (this endpoint)
    - Phase 2: Assemble document from approved bullets (separate endpoint)
    """
    serializer = GenerationRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = serializer.validated_data

        # Get or create job description
        job_desc, created = JobDescription.get_or_create_from_content(
            data['job_description'],
            data.get('company_name', ''),
            data.get('role_title', '')
        )

        # Set expiration (90 days from now)
        expires_at = timezone.now() + timedelta(days=90)

        # Prepare generation preferences (ft-007: include artifact_ids if provided)
        generation_preferences = data.get('generation_preferences', {})
        if 'artifact_ids' in data:
            # Store artifact_ids in preferences for task to retrieve
            generation_preferences['artifact_ids'] = data['artifact_ids']

        # Create generation document with initial status='pending'
        generation = GeneratedDocument.objects.create(
            user=request.user,
            document_type='cv',
            job_description_hash=job_desc.content_hash,
            job_description=job_desc,
            label_ids=data.get('label_ids', []),
            template_id=data.get('template_id', 1),
            custom_sections=data.get('custom_sections', {}),
            generation_preferences=generation_preferences,
            status='pending',
            expires_at=expires_at
        )

        # Start Phase 1: Bullet preparation (async)
        prepare_generation_bullets_task.delay(str(generation.id))

        return Response({
            'generation_id': str(generation.id),
            'status': 'pending',
            'workflow': 'two_phase',
            'next_step': 'Review bullets at GET /api/v1/generations/{generation_id}/bullets/',
            'estimated_bullet_completion': timezone.now() + timedelta(seconds=20),
            'job_description_hash': job_desc.content_hash
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response({
            'error': 'Failed to initiate document generation',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
# @ratelimit(key='user', rate='10/h', method='POST')
def generate_cover_letter(request):
    """
    Generate cover letter based on job description and user artifacts.
    Similar to document generation but for cover letters.
    """
    serializer = GenerationRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = serializer.validated_data

        # Get or create job description
        job_desc, created = JobDescription.get_or_create_from_content(
            data['job_description'],
            data.get('company_name', ''),
            data.get('role_title', '')
        )

        # Set expiration (90 days from now)
        expires_at = timezone.now() + timedelta(days=90)

        # Create generation document for cover letter
        generation = GeneratedDocument.objects.create(
            user=request.user,
            document_type='cover_letter',
            job_description_hash=job_desc.content_hash,
            job_description=job_desc,
            label_ids=data.get('label_ids', []),
            template_id=data.get('template_id', 1),
            custom_sections=data.get('custom_sections', {}),
            generation_preferences=data.get('generation_preferences', {}),
            expires_at=expires_at
        )

        # Start async generation (same task handles both types)
        generate_document_task.delay(str(generation.id))

        return Response({
            'generation_id': str(generation.id),
            'status': 'processing',
            'estimated_completion_time': timezone.now() + timedelta(seconds=30),
            'job_description_hash': job_desc.content_hash
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response({
            'error': 'Failed to initiate cover letter generation',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def generation_status(request, generation_id):
    """
    Get generation status and content when completed.
    Also supports PATCH to update CV metadata.
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Handle PATCH requests for updating CV metadata
        if request.method == 'PATCH':
            from .serializers import CVMetadataUpdateSerializer
            serializer = CVMetadataUpdateSerializer(
                generation,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                # Return full detail after update
                detail_serializer = GeneratedDocumentDetailSerializer(generation)
                return Response(detail_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Handle GET requests
        if generation.status == 'completed':
            serializer = GeneratedDocumentDetailSerializer(generation)
        else:
            serializer = GeneratedDocumentSerializer(generation)

        return Response(serializer.data)

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unified_generation_status(request, generation_id):
    """
    Get comprehensive unified status for generation and all related jobs.

    Implements ft-026: Unified Generation Status Endpoint (ADR-040).
    Matches artifact enrichment-status pattern for consistency.

    Returns:
        - Overall generation status and progress
        - Phase-level tracking (bullet generation, bullet review, assembly)
        - Per-artifact bullet generation job statuses
        - Aggregated processing and quality metrics

    This endpoint should be used for frontend polling during generation.
    Use GET /api/v1/generations/{generation_id}/ for retrieving final document content.
    """
    try:
        # Verify ownership
        GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Get comprehensive status from service
        status_data = GenerationStatusService.get_generation_status(generation_id)

        return Response(status_data, status=status.HTTP_200_OK)

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


class GenerationListView(generics.ListAPIView):
    """
    List user's generated documents (optimized for list view).

    Uses lightweight serializer (excludes heavy 'content' field) and
    prefetches related job_description for optimal performance.
    """

    serializer_class = GeneratedDocumentListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GeneratedDocument.objects.filter(
            user=self.request.user
        ).select_related('job_description').order_by('-created_at')


class GenerationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific generation (ADR-038)."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'  # Model field to lookup by
    lookup_url_kwarg = 'generation_id'  # URL parameter name

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.request.method == 'PATCH':
            from .serializers import CVMetadataUpdateSerializer
            return CVMetadataUpdateSerializer
        from .serializers import GeneratedDocumentDetailSerializer
        return GeneratedDocumentDetailSerializer

    def get_queryset(self):
        return GeneratedDocument.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def rate_generation(request, generation_id):
    """
    Rate a generated document and provide feedback.
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        serializer = DocumentRatingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update generation rating
        generation.user_rating = serializer.validated_data['rating']
        generation.user_feedback = serializer.validated_data.get('feedback', '')
        generation.save()

        # Create feedback record
        GenerationFeedback.objects.create(
            generation=generation,
            feedback_type='rating',
            feedback_data={
                'rating': serializer.validated_data['rating'],
                'feedback': serializer.validated_data.get('feedback', '')
            }
        )

        return Response({
            'message': 'Rating submitted successfully',
            'rating': generation.user_rating
        })

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ===== Two-Phase CV Workflow Endpoints (ft-009) =====

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def generation_bullets(request, generation_id):
    """
    Consolidated generation-scoped bullet endpoint (ADR-038).

    GET: Fetch bullets for generation (optionally filtered by artifact)
    POST: Generate bullets for an artifact in this generation

    GET /api/v1/generations/{generation_id}/bullets/?artifact_id=42
    POST /api/v1/generations/{generation_id}/bullets/
         Body: { "artifact_id": 42, "job_context": {...}, "regenerate": false }
    """
    if request.method == 'GET':
        return _get_generation_bullets(request, generation_id)
    elif request.method == 'POST':
        return _generate_generation_bullets(request, generation_id)


def _get_generation_bullets(request, generation_id):
    """
    GET handler: Fetch bullets for generation (optionally filtered by artifact).

    Query params:
        - artifact_id (int, optional): Filter bullets by specific artifact

    Returns bullets grouped by artifact for user review and approval.
    Status must be 'bullets_ready' or later to access.
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Check status
        if generation.status not in ['bullets_ready', 'bullets_approved', 'assembling', 'completed']:
            return Response({
                'error': f'Bullets not ready yet. Current status: {generation.status}',
                'status': generation.status,
                'progress_percentage': generation.progress_percentage
            }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch bullets (optionally filtered by artifact)
        bullets_query = BulletPoint.objects.filter(cv_generation=generation)

        # ADR-038: Support artifact_id filter
        artifact_id_filter = request.query_params.get('artifact_id')
        if artifact_id_filter:
            try:
                artifact_id = int(artifact_id_filter)
                bullets_query = bullets_query.filter(artifact_id=artifact_id)
            except ValueError:
                return Response({
                    'error': 'Invalid artifact_id parameter'
                }, status=status.HTTP_400_BAD_REQUEST)

        bullets = bullets_query.select_related('artifact').order_by('artifact_id', 'position')

        # Group by artifact
        bullets_by_artifact = {}
        for bullet in bullets:
            artifact_id = bullet.artifact_id
            if artifact_id not in bullets_by_artifact:
                bullets_by_artifact[artifact_id] = {
                    'artifact_id': artifact_id,
                    'artifact_title': bullet.artifact.title,
                    'bullets': []
                }
            bullets_by_artifact[artifact_id]['bullets'].append(
                BulletPointSerializer(bullet).data
            )

        return Response({
            'generation_id': str(generation.id),
            'status': generation.status,
            'bullets_count': generation.bullets_count,
            'bullets_generated_at': generation.bullets_generated_at,
            'artifacts': list(bullets_by_artifact.values())
        })

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


def _generate_generation_bullets(request, generation_id):
    """
    POST handler: Generate bullets for an artifact in this generation.

    Body (BulletGenerationRequestSerializer):
        - artifact_id (int): Artifact to generate bullets for
        - job_context (object): Job requirements and context
        - regenerate (bool, default=False): Force regeneration
        - optimization_level (str, default='standard'): Optimization level

    Returns: 202 Accepted with status_endpoint for polling (ft-026)
    """
    # Validate generation exists and belongs to user
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )
    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Validate request data
    serializer = BulletGenerationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    artifact_id = data['artifact_id']  # ADR-038: Now from body
    job_context = data['job_context']
    regenerate = data.get('regenerate', False)

    # Validate artifact exists and belongs to user
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)
    except Artifact.DoesNotExist:
        return Response({
            'error': 'Artifact not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Check for existing bullets if regenerate=False
    if not regenerate:
        existing_bullets = BulletPoint.objects.filter(
            artifact=artifact,
            cv_generation_id=generation_id
        ).order_by('position')

        if existing_bullets.count() == 3:
            # Return existing bullets
            bullet_serializer = BulletPointSerializer(existing_bullets, many=True)
            return Response({
                'bullet_points': bullet_serializer.data,
                'metadata': {
                    'artifact_id': artifact.id,
                    'cached': True,
                    'generation_time_ms': 0
                }
            }, status=status.HTTP_200_OK)

    # Initiate async bullet generation with proper cleanup
    async def generate_with_cleanup():
        service = BulletGenerationService()
        try:
            result = await service.generate_bullets(
                artifact_id=artifact.id,
                job_context=job_context,
                cv_generation_id=generation_id,  # From URL path
                regenerate=regenerate
            )
            return result
        finally:
            # Cleanup within same event loop
            await service.cleanup()

    try:
        # Execute async operation with cleanup in same event loop
        result = async_to_sync(generate_with_cleanup)()

        # Return 202 Accepted (using async API pattern)
        # ft-026: Client should poll unified generation status endpoint:
        # GET /api/v1/generations/{generation_id}/generation-status/

        return Response({
            'status': 'processing',
            'artifact_id': artifact.id,
            'generation_id': str(generation_id),
            'estimated_completion_time': timezone.now() + timedelta(seconds=1),
            'status_endpoint': f'/api/v1/generations/{generation_id}/generation-status/'
        }, status=status.HTTP_202_ACCEPTED)

    except ValidationError as e:
        return Response({
            'error': 'Bullet generation failed',
            'detail': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Internal server error during bullet generation',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def edit_generation_bullet(request, generation_id, bullet_id):
    """
    Edit a specific bullet point before approval.

    Allows user to modify bullet text while preserving original for tracking.
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Check status
        if generation.status != 'bullets_ready':
            return Response({
                'error': f'Cannot edit bullets. Status must be "bullets_ready", currently: {generation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        bullet = BulletPoint.objects.get(
            id=bullet_id,
            cv_generation=generation
        )

        # Validate new text
        new_text = request.data.get('text')
        if not new_text:
            return Response({
                'error': 'Text field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(new_text) < 60 or len(new_text) > 150:
            return Response({
                'error': f'Bullet text must be 60-150 characters, got {len(new_text)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save original if not already saved
        if not bullet.original_text:
            bullet.original_text = bullet.text

        # Update bullet
        bullet.text = new_text
        bullet.user_edited = True
        bullet.save()

        return Response({
            'message': 'Bullet updated successfully',
            'bullet': BulletPointSerializer(bullet).data
        })

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except BulletPoint.DoesNotExist:
        return Response({
            'error': 'Bullet not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_generation_bullets(request, generation_id):
    """
    Approve/reject/edit individual bullets (ft-024 enhanced).

    ENHANCED: Now supports individual bullet actions instead of just "approve all".

    Body (backward compatible):
        Option 1 (old): No body = approve all bullets (backward compatible)
        Option 2 (new): bullet_actions = [
            {bullet_id: int, action: 'approve' | 'reject' | 'edit', edited_text?: string}
        ]

    Returns:
        200 OK with updated bullets and counts

    Example:
        POST /api/v1/generations/{generation_id}/bullets/approve/
        {
            "bullet_actions": [
                {"bullet_id": 1, "action": "approve"},
                {"bullet_id": 2, "action": "reject"},
                {"bullet_id": 3, "action": "edit", "edited_text": "Led team of 6 engineers..."}
            ]
        }
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Check status
        if generation.status != 'bullets_ready':
            return Response({
                'error': f'Cannot modify bullets. Status must be "bullets_ready", currently: {generation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get bullet actions from request (ft-024 individual actions)
        bullet_actions = request.data.get('bullet_actions', [])

        # Backward compatibility: If no bullet_actions provided, approve all bullets
        if not bullet_actions:
            bullets = BulletPoint.objects.filter(cv_generation=generation)

            if bullets.count() == 0:
                return Response({
                    'error': 'No bullets found to approve'
                }, status=status.HTTP_400_BAD_REQUEST)

            bullets.update(
                user_approved=True,
                approved_at=timezone.now(),
                approved_by=request.user
            )

            # Update generation status
            generation.status = 'bullets_approved'
            generation.save(update_fields=['status'])

            return Response({
                'message': 'All bullets approved successfully (legacy mode)',
                'generation_id': str(generation.id),
                'status': 'bullets_approved',
                'bullets_approved': bullets.count(),
                'bullets_rejected': 0,
                'bullets_edited': 0
            })

        # ft-024: Individual bullet actions
        approved_count = 0
        rejected_count = 0
        edited_count = 0
        updated_bullets = []

        for action_data in bullet_actions:
            try:
                bullet = BulletPoint.objects.get(
                    id=action_data['bullet_id'],
                    cv_generation=generation
                )
            except BulletPoint.DoesNotExist:
                return Response({
                    'error': f"Bullet {action_data['bullet_id']} not found in this generation"
                }, status=status.HTTP_404_NOT_FOUND)

            action = action_data['action']

            if action == 'approve':
                bullet.user_approved = True
                bullet.user_rejected = False
                bullet.approved_at = timezone.now()
                bullet.approved_by = request.user
                approved_count += 1

            elif action == 'reject':
                bullet.user_approved = False
                bullet.user_rejected = True
                rejected_count += 1

            elif action == 'edit':
                # Preserve original text before editing
                if not bullet.original_text:
                    bullet.original_text = bullet.text

                edited_text = action_data.get('edited_text')
                if not edited_text:
                    return Response({
                        'error': f'edited_text required for action "edit" on bullet {bullet.id}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validate edited text length (60-150 chars)
                if not (60 <= len(edited_text) <= 150):
                    return Response({
                        'error': f'Edited text must be 60-150 characters, got {len(edited_text)}',
                        'bullet_id': bullet.id
                    }, status=status.HTTP_400_BAD_REQUEST)

                bullet.text = edited_text
                bullet.user_edited = True
                edited_count += 1

            bullet.save()
            updated_bullets.append(bullet)

        # Check if all bullets are now approved or rejected
        all_bullets = BulletPoint.objects.filter(cv_generation=generation)
        all_decided = all(b.user_approved or b.user_rejected for b in all_bullets)

        if all_decided:
            generation.status = 'bullets_approved'
            generation.save(update_fields=['status'])

        # Serialize updated bullets
        serializer = BulletPointSerializer(updated_bullets, many=True)

        return Response({
            'generation_id': str(generation.id),
            'status': generation.status,
            'bullets_approved': approved_count,
            'bullets_rejected': rejected_count,
            'bullets_edited': edited_count,
            'all_bullets_decided': all_decided,
            'updated_bullets': serializer.data
        })

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def regenerate_generation_bullets(request, generation_id):
    """
    Regenerate bullets for document generation with optional refinement prompt (ft-024, ADR-036).

    Body:
        refinement_prompt (optional): Temporary hint for LLM (max 500 chars, NOT persisted)
        bullet_ids_to_regenerate (optional): List of bullet IDs to regenerate
        artifact_ids (optional): List of artifact IDs to regenerate bullets for

    Returns:
        202 Accepted with job status and estimated completion time

    Example:
        POST /api/v1/generations/{generation_id}/bullets/regenerate/
        {
            "refinement_prompt": "Focus more on leadership and team management",
            "artifact_ids": [1, 3, 5]
        }
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Validate refinement_prompt length (ADR-036: max 500 chars)
        refinement_prompt = request.data.get('refinement_prompt')
        if refinement_prompt and len(refinement_prompt) > 500:
            return Response({
                'error': 'Refinement prompt must be 500 characters or less',
                'max_length': 500,
                'provided_length': len(refinement_prompt)
            }, status=status.HTTP_400_BAD_REQUEST)

        bullet_ids = request.data.get('bullet_ids_to_regenerate')
        artifact_ids = request.data.get('artifact_ids')

        # Call service layer asynchronously
        service = GenerationService()

        # Use async_to_sync since views are synchronous
        result = async_to_sync(service.regenerate_generation_bullets)(
            generation_id=str(generation_id),
            refinement_prompt=refinement_prompt,  # Temporary only, NOT saved (ADR-036)
            bullet_ids=bullet_ids,
            artifact_ids=artifact_ids
        )

        return Response({
            'generation_id': str(generation_id),
            'status': 'completed',
            'message': 'Bullet regeneration completed',
            'bullets_regenerated': result['bullets_regenerated'],
            'content_sources_used': result['content_sources_used'],
            'refinement_prompt_used': result['refinement_prompt_used']
        }, status=status.HTTP_200_OK)

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Regeneration failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assemble_generation(request, generation_id):
    """
    Phase 2: Assemble final document from approved bullets.

    Precondition: status='bullets_approved'
    Triggers async assembly task.
    """
    try:
        generation = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user
        )

        # Check status
        if generation.status != 'bullets_approved':
            return Response({
                'error': f'Cannot assemble document. Bullets must be approved first. Current status: {generation.status}',
                'current_status': generation.status
            }, status=status.HTTP_400_BAD_REQUEST)

        # Start Phase 2: Document assembly (async)
        assemble_generation_task.delay(str(generation.id))

        return Response({
            'generation_id': str(generation.id),
            'status': 'assembling',
            'message': 'Document assembly started',
            'estimated_completion': timezone.now() + timedelta(seconds=10),
            'poll_status_at': f'GET /api/v1/generations/{generation_id}/status/'
        }, status=status.HTTP_202_ACCEPTED)

    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generation not found'
        }, status=status.HTTP_404_NOT_FOUND)


class GenerationTemplateListView(generics.ListAPIView):
    """List available document generation templates."""

    serializer_class = CVTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CVTemplate.objects.filter(is_active=True)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generation_analytics(request):
    """
    Get analytics for user's generations.
    """
    user_generations = GeneratedDocument.objects.filter(user=request.user)

    analytics = {
        'total_generations': user_generations.count(),
        'completed_generations': user_generations.filter(status='completed').count(),
        'failed_generations': user_generations.filter(status='failed').count(),
        'average_rating': 0,
        'most_used_template': None,
        'generation_history': []
    }

    # Calculate average rating
    rated_generations = user_generations.filter(user_rating__isnull=False)
    if rated_generations.exists():
        total_rating = sum(g.user_rating for g in rated_generations)
        analytics['average_rating'] = round(total_rating / rated_generations.count(), 1)

    # Most used template
    template_usage = {}
    for gen in user_generations:
        template_id = gen.template_id
        template_usage[template_id] = template_usage.get(template_id, 0) + 1

    if template_usage:
        most_used_template_id = max(template_usage, key=template_usage.get)
        try:
            template = CVTemplate.objects.get(id=most_used_template_id)
            analytics['most_used_template'] = template.name
        except CVTemplate.DoesNotExist:
            pass

    # Recent generation history (last 10)
    recent_generations = user_generations.order_by('-created_at')[:10]
    analytics['generation_history'] = [
        {
            'id': str(gen.id),
            'status': gen.status,
            'created_at': gen.created_at,
            'rating': gen.user_rating
        }
        for gen in recent_generations
    ]

    return Response(analytics)


# ===== ft-006 Bullet Generation API Endpoints =====

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def validate_bullets(request):
    """
    Validate a bullet set without saving.

    POST /api/v1/cv/bullets/validate/

    Validates:
        - Structure (exactly 3 bullets with correct hierarchy)
        - Content quality (action verbs, metrics, keywords)
        - Semantic similarity (no redundant bullets)
        - ATS compatibility

    Feature: ft-006 (three-bullets-per-artifact)
    """
    # Validate request data
    serializer = BulletValidationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    bullets = data['bullets']
    job_context = data['job_context']

    # Validate bullet count
    if len(bullets) != 3:
        return Response({
            'error': f'Expected exactly 3 bullets, got {len(bullets)}'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Perform validation with proper cleanup
    async def validate_with_cleanup():
        service = BulletValidationService()
        try:
            result = await service.validate_bullet_set(
                bullets=bullets,
                job_context=job_context
            )

            # Calculate ATS compatibility score
            ats_score = sum(
                service.calculate_keyword_relevance(bullet, job_context)
                for bullet in bullets
            ) / len(bullets) if bullets else 0

            return result, ats_score
        finally:
            # Cleanup within same event loop
            await service.cleanup()

    try:
        # Execute async operation with cleanup in same event loop
        result, ats_score = async_to_sync(validate_with_cleanup)()

        return Response({
            'validation_results': {
                'is_valid': result.is_valid,
                'overall_quality_score': result.overall_quality_score,
                'structure_valid': result.structure_valid,
                'bullet_scores': result.bullet_scores,
                'similarity_pairs': result.similarity_pairs,
                'ats_compatibility_score': round(ats_score, 2),
                'issues': result.issues,
                'suggestions': result.suggestions
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': 'Validation failed',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ft-030: Review Workflow Endpoints

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_bullet(request, bullet_id):
    """
    Approve a flagged bullet point (ft-030).

    Marks the bullet as approved by the user after review.
    """
    try:
        bullet = BulletPoint.objects.get(id=bullet_id, artifact__user=request.user)
    except BulletPoint.DoesNotExist:
        return Response(
            {'error': 'Bullet not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )

    bullet.is_approved = True
    bullet.approved_by = request.user
    bullet.approved_at = timezone.now()
    bullet.save()

    return Response(
        BulletPointSerializer(bullet).data,
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_bullet(request, bullet_id):
    """
    Reject a flagged bullet point (ft-030).

    Marks the bullet as rejected and optionally triggers regeneration.
    """
    try:
        bullet = BulletPoint.objects.get(id=bullet_id, artifact__user=request.user)
    except BulletPoint.DoesNotExist:
        return Response(
            {'error': 'Bullet not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Mark as rejected
    bullet.is_approved = False
    bullet.save()

    # Optional: Trigger regeneration
    regenerate = request.data.get('regenerate', False)
    if regenerate:
        # Logic to trigger regeneration would go here
        pass

    return Response(
        {'status': 'rejected', 'regenerate': regenerate},
        status=status.HTTP_200_OK
    )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_bullet(request, bullet_id):
    """
    Update bullet text after user edit (ft-030).

    Allows user to manually edit bullet text.
    """
    try:
        bullet = BulletPoint.objects.get(id=bullet_id, artifact__user=request.user)
    except BulletPoint.DoesNotExist:
        return Response(
            {'error': 'Bullet not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )

    new_text = request.data.get('text')
    if not new_text:
        return Response(
            {'error': 'Text field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    bullet.text = new_text
    bullet.is_approved = True  # Edited bullets are automatically approved
    bullet.approved_by = request.user
    bullet.approved_at = timezone.now()
    bullet.save()

    return Response(
        BulletPointSerializer(bullet).data,
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_approve_bullets(request):
    """
    Bulk approve multiple bullets (ft-030).

    Approves all bullets in the provided list.
    """
    bullet_ids = request.data.get('bullet_ids', [])

    if not bullet_ids:
        return Response(
            {'error': 'bullet_ids array is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    bullets = BulletPoint.objects.filter(
        id__in=bullet_ids,
        artifact__user=request.user
    )

    updated_count = bullets.update(
        is_approved=True,
        approved_by=request.user,
        approved_at=timezone.now()
    )

    return Response(
        {'approved_count': updated_count},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_reject_bullets(request):
    """
    Bulk reject multiple bullets (ft-030).

    Rejects all bullets in the provided list.
    """
    bullet_ids = request.data.get('bullet_ids', [])

    if not bullet_ids:
        return Response(
            {'error': 'bullet_ids array is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    bullets = BulletPoint.objects.filter(
        id__in=bullet_ids,
        artifact__user=request.user
    )

    updated_count = bullets.update(is_approved=False)

    return Response(
        {'rejected_count': updated_count},
        status=status.HTTP_200_OK
    )