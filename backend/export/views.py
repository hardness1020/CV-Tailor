from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
# from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, Http404
from django.core.files.storage import default_storage
from generation.models import GeneratedDocument
from .models import ExportJob, ExportTemplate, ExportAnalytics
from .serializers import (
    ExportRequestSerializer, ExportJobSerializer, ExportJobDetailSerializer,
    ExportTemplateSerializer
)
from .tasks import export_document_task, validate_evidence_links_for_export


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
# @ratelimit(key='user', rate='20/h', method='POST')
def export_document(request, generation_id):
    """
    Export a generated document to PDF or DOCX format.
    Implements Feature 003 - Document Export System.
    """
    try:
        # Get the generated document
        generated_doc = GeneratedDocument.objects.get(
            id=generation_id,
            user=request.user,
            status='completed'
        )
    except GeneratedDocument.DoesNotExist:
        return Response({
            'error': 'Generated document not found or not completed'
        }, status=status.HTTP_404_NOT_FOUND)

    # Validate request data
    serializer = ExportRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = serializer.validated_data

        # Get or validate template
        template = None
        if data.get('template_id'):
            try:
                template = ExportTemplate.objects.get(
                    id=data['template_id'],
                    is_active=True
                )
                # Check if user has access to premium templates
                if template.is_premium:
                    # Add premium access check here if needed
                    pass
            except ExportTemplate.DoesNotExist:
                return Response({
                    'error': 'Template not found'
                }, status=status.HTTP_404_NOT_FOUND)

        # Create export job
        export_job = ExportJob.objects.create(
            user=request.user,
            generated_document=generated_doc,
            format=data['format'],
            template=template,
            export_options={
                'options': data.get('options', {}),
                'sections': data.get('sections', {}),
                'watermark': data.get('watermark'),
            },
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Start async export
        if data.get('options', {}).get('include_evidence', False):
            # Validate evidence links first
            validate_evidence_links_for_export.delay(str(export_job.id))

        export_document_task.delay(str(export_job.id))

        return Response({
            'export_id': str(export_job.id),
            'status': 'processing',
            'estimated_completion_time': timezone.now() + timedelta(seconds=10),
            'file_size_estimate': 0  # Will be updated when completed
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response({
            'error': 'Failed to initiate export',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_status(request, export_id):
    """
    Get export status and download information.
    """
    try:
        export_job = ExportJob.objects.get(
            id=export_id,
            user=request.user
        )

        serializer = ExportJobDetailSerializer(export_job)
        return Response(serializer.data)

    except ExportJob.DoesNotExist:
        return Response({
            'error': 'Export job not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_export(request, export_id):
    """
    Download the exported document file.
    """
    try:
        export_job = ExportJob.objects.get(
            id=export_id,
            user=request.user,
            status='completed'
        )

        if not export_job.file_path or not default_storage.exists(export_job.file_path):
            return Response({
                'error': 'Export file not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if expired
        if export_job.expires_at and export_job.expires_at < timezone.now():
            return Response({
                'error': 'Export file has expired'
            }, status=status.HTTP_410_GONE)

        # Get file content
        file_content = default_storage.open(export_job.file_path).read()

        # Set appropriate content type
        if export_job.format == 'pdf':
            content_type = 'application/pdf'
        elif export_job.format == 'docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            content_type = 'application/octet-stream'

        # Generate filename
        user_name = f"{request.user.first_name}_{request.user.last_name}".strip('_') or request.user.username
        company_name = "company"  # Could be extracted from job description
        filename = f"cv_{user_name}_{company_name}.{export_job.format}"

        # Create response
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_content)

        # Update download count
        export_job.download_count += 1
        export_job.save()

        # Create analytics event
        ExportAnalytics.objects.create(
            export_job=export_job,
            event_type='downloaded',
            metadata={
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'download_count': export_job.download_count
            },
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return response

    except ExportJob.DoesNotExist:
        raise Http404("Export not found")


class UserExportsListView(generics.ListAPIView):
    """List user's export jobs."""

    serializer_class = ExportJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExportJob.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class ExportJobDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a specific export job."""

    serializer_class = ExportJobDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'  # Model field to lookup by
    lookup_url_kwarg = 'export_id'  # URL parameter name (ADR-039)

    def get_queryset(self):
        return ExportJob.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        """Delete export job and associated file."""
        # Delete file from storage
        if instance.file_path and default_storage.exists(instance.file_path):
            default_storage.delete(instance.file_path)

        # Create analytics event
        ExportAnalytics.objects.create(
            export_job=instance,
            event_type='deleted',
            metadata={'reason': 'user_request'}
        )

        # Delete instance
        instance.delete()


class ExportTemplateListView(generics.ListAPIView):
    """List available export templates."""

    serializer_class = ExportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExportTemplate.objects.filter(is_active=True)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_analytics(request):
    """
    Get export analytics for the user.
    """
    user_exports = ExportJob.objects.filter(user=request.user)

    analytics = {
        'total_exports': user_exports.count(),
        'completed_exports': user_exports.filter(status='completed').count(),
        'failed_exports': user_exports.filter(status='failed').count(),
        'total_downloads': sum(export.download_count for export in user_exports),
        'format_distribution': {},
        'template_usage': {},
        'recent_exports': []
    }

    # Format distribution
    for export in user_exports:
        format_name = export.format
        analytics['format_distribution'][format_name] = analytics['format_distribution'].get(format_name, 0) + 1

    # Template usage
    for export in user_exports.filter(template__isnull=False):
        template_name = export.template.name
        analytics['template_usage'][template_name] = analytics['template_usage'].get(template_name, 0) + 1

    # Recent exports (last 10)
    recent_exports = user_exports.order_by('-created_at')[:10]
    analytics['recent_exports'] = [
        {
            'id': str(export.id),
            'format': export.format,
            'status': export.status,
            'download_count': export.download_count,
            'created_at': export.created_at,
            'file_size': export.file_size
        }
        for export in recent_exports
    ]

    return Response(analytics)