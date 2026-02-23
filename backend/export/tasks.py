"""
Celery tasks for document export.
"""

import os
import logging
from celery import shared_task
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.apps import apps
from .document_generators import PDFGenerator, DOCXGenerator

logger = logging.getLogger(__name__)


@shared_task
def export_document_task(export_job_id):
    """
    Export document to PDF or DOCX format.
    Implements Feature 003 - Document Export System.

    NEW (ft-023): Status validation to prevent duplicate exports.
    """
    try:
        # Import models here to avoid circular imports
        ExportJob = apps.get_model('export', 'ExportJob')
        ExportAnalytics = apps.get_model('export', 'ExportAnalytics')

        export_job = ExportJob.objects.get(id=export_job_id)

        # NEW (ft-023): Validate status before processing
        if export_job.status not in ['pending', 'failed']:
            logger.warning(
                f"Cannot export job {export_job_id}: "
                f"status is {export_job.status}, expected 'pending' or 'failed'"
            )
            return {
                'skipped': True,
                'reason': 'invalid_status',
                'current_status': export_job.status
            }

        export_job.status = 'processing'
        export_job.progress_percentage = 10
        export_job.save()

        # Get generated document content
        generated_doc = export_job.generated_document
        if not generated_doc.content:
            export_job.status = 'failed'
            export_job.error_message = 'No content available for export'
            export_job.save()
            return

        export_job.progress_percentage = 30
        export_job.save()

        # Prepare content for export
        content = generated_doc.content.copy()

        # Add personal information from user profile
        user = export_job.user
        content['personal_info'] = {
            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'phone': getattr(user, 'phone', ''),
            'location': getattr(user, 'location', ''),
            'linkedin_url': getattr(user, 'linkedin_url', ''),
            'github_url': getattr(user, 'github_url', ''),
            'website_url': getattr(user, 'website_url', ''),
        }

        export_job.progress_percentage = 50
        export_job.save()

        # Generate document based on format
        if export_job.format == 'pdf':
            document_bytes = generate_pdf_document(content, export_job.export_options)
            file_extension = 'pdf'
            content_type = 'application/pdf'
        elif export_job.format == 'docx':
            document_bytes = generate_docx_document(content, export_job.export_options)
            file_extension = 'docx'
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            export_job.status = 'failed'
            export_job.error_message = f'Unsupported format: {export_job.format}'
            export_job.save()
            return

        export_job.progress_percentage = 80
        export_job.save()

        # Save file to storage
        filename = f"cv_{user.id}_{export_job.id}.{file_extension}"
        file_path = f"exports/{filename}"

        # Save to storage
        saved_path = default_storage.save(file_path, ContentFile(document_bytes))

        # Update export job
        export_job.file_path = saved_path
        export_job.file_size = len(document_bytes)
        export_job.status = 'completed'
        export_job.progress_percentage = 100
        export_job.completed_at = timezone.now()

        # Set expiration (24 hours from now)
        export_job.expires_at = timezone.now() + timezone.timedelta(hours=24)
        export_job.save()

        # Create analytics event
        ExportAnalytics.objects.create(
            export_job=export_job,
            event_type='created',
            metadata={
                'file_size': export_job.file_size,
                'format': export_job.format,
                'processing_time_ms': (timezone.now() - export_job.created_at).total_seconds() * 1000
            }
        )

        logger.info(f"Successfully exported document {export_job_id} as {export_job.format}")

    except Exception as e:
        logger.error(f"Error exporting document {export_job_id}: {e}")
        try:
            export_job = ExportJob.objects.get(id=export_job_id)
            export_job.status = 'failed'
            export_job.error_message = str(e)
            export_job.save()
        except:
            pass


def generate_pdf_document(content, options):
    """Generate PDF document from content."""
    try:
        generator = PDFGenerator()
        return generator.generate_cv(content, options)
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise


def generate_docx_document(content, options):
    """Generate DOCX document from content."""
    try:
        generator = DOCXGenerator()
        return generator.generate_cv(content, options)
    except Exception as e:
        logger.error(f"Error generating DOCX: {e}")
        raise


@shared_task
def cleanup_expired_exports():
    """Cleanup expired export files."""
    ExportJob = apps.get_model('export', 'ExportJob')
    ExportAnalytics = apps.get_model('export', 'ExportAnalytics')

    expired_exports = ExportJob.objects.filter(
        expires_at__lt=timezone.now(),
        status='completed'
    )

    deleted_count = 0
    for export_job in expired_exports:
        try:
            # Delete file from storage
            if export_job.file_path and default_storage.exists(export_job.file_path):
                default_storage.delete(export_job.file_path)

            # Create analytics event
            ExportAnalytics.objects.create(
                export_job=export_job,
                event_type='deleted',
                metadata={'reason': 'expired'}
            )

            # Delete export job
            export_job.delete()
            deleted_count += 1

        except Exception as e:
            logger.error(f"Error deleting expired export {export_job.id}: {e}")

    logger.info(f"Cleaned up {deleted_count} expired export files")
    return deleted_count


@shared_task
def validate_evidence_links_for_export(export_job_id):
    """Validate evidence links before including in export."""
    import requests

    try:
        ExportJob = apps.get_model('export', 'ExportJob')
        export_job = ExportJob.objects.get(id=export_job_id)

        # Get evidence links from generated document content
        content = export_job.generated_document.content
        evidence_links = []

        # Collect evidence links from various sections
        for exp in content.get('experience', []):
            evidence_links.extend(exp.get('evidence_references', []))

        for project in content.get('projects', []):
            if project.get('evidence_url'):
                evidence_links.append(project['evidence_url'])

        # Validate each link
        validated_links = []
        for link in evidence_links:
            try:
                response = requests.head(link, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    validated_links.append(link)
                else:
                    logger.warning(f"Evidence link validation failed for {link}: {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Evidence link validation error for {link}: {e}")

        # Update export options with validated links
        export_options = export_job.export_options.copy()
        export_options['validated_evidence_links'] = validated_links
        export_job.export_options = export_options
        export_job.save()

        return len(validated_links)

    except Exception as e:
        logger.error(f"Error validating evidence links for export {export_job_id}: {e}")
        return 0