"""
Unit tests for export app Celery tasks
"""

from unittest.mock import patch, Mock
from datetime import timedelta
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone

from export.models import ExportJob, ExportTemplate, ExportAnalytics
from export.tasks import (
    export_document_task, generate_pdf_document, generate_docx_document,
    cleanup_expired_exports, validate_evidence_links_for_export
)
from generation.models import GeneratedDocument, JobDescription

User = get_user_model()


@tag('medium', 'integration', 'export', 'tasks')
class ExportTaskTests(TestCase):
    """Test cases for export Celery tasks"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.generated_doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            status='completed',
            content={
                'professional_summary': 'Experienced developer',
                'key_skills': ['Python', 'Django']
            }
        )

    @patch('export.tasks.generate_pdf_document')
    @patch('export.tasks.default_storage')
    def test_export_document_task_pdf(self, mock_storage, mock_generate_pdf):
        """Test PDF export task"""
        # Mock PDF generation
        fake_pdf_content = b'%PDF-1.4 fake pdf content'
        mock_generate_pdf.return_value = fake_pdf_content

        # Mock storage
        mock_storage.save.return_value = 'exports/test.pdf'

        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='pending'  # ft-023: Task only processes 'pending' or 'failed' jobs
        )

        export_document_task(str(export_job.id))

        export_job.refresh_from_db()
        self.assertEqual(export_job.status, 'completed')
        self.assertEqual(export_job.progress_percentage, 100)
        self.assertEqual(export_job.file_size, len(fake_pdf_content))
        self.assertIsNotNone(export_job.completed_at)

        # Check analytics was created
        self.assertEqual(ExportAnalytics.objects.count(), 1)

    @patch('export.tasks.generate_docx_document')
    @patch('export.tasks.default_storage')
    def test_export_document_task_docx(self, mock_storage, mock_generate_docx):
        """Test DOCX export task"""
        fake_docx_content = b'fake docx content'
        mock_generate_docx.return_value = fake_docx_content
        mock_storage.save.return_value = 'exports/test.docx'

        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='docx',
            status='pending'  # ft-023: Task only processes 'pending' or 'failed' jobs
        )

        export_document_task(str(export_job.id))

        export_job.refresh_from_db()
        self.assertEqual(export_job.status, 'completed')
        self.assertEqual(export_job.file_size, len(fake_docx_content))

    def test_export_task_no_content(self):
        """Test export task with no content"""
        # Create generation without content
        empty_doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='def456',
            status='completed'
            # No content field
        )

        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=empty_doc,
            format='pdf',
            status='pending'  # ft-023: Task only processes 'pending' or 'failed' jobs
        )

        export_document_task(str(export_job.id))

        export_job.refresh_from_db()
        self.assertEqual(export_job.status, 'failed')
        self.assertIn('No content available', export_job.error_message)

    def test_cleanup_expired_exports(self):
        """Test cleanup of expired export files"""
        # Create expired export
        expired_time = timezone.now() - timedelta(hours=1)
        expired_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            file_path='exports/expired.pdf',
            expires_at=expired_time
        )

        # Create valid export
        future_time = timezone.now() + timedelta(hours=1)
        valid_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            file_path='exports/valid.pdf',
            expires_at=future_time
        )

        with patch('export.tasks.default_storage') as mock_storage:
            mock_storage.exists.return_value = True
            deleted_count = cleanup_expired_exports()

        self.assertEqual(deleted_count, 1)
        self.assertEqual(ExportJob.objects.count(), 1)
        self.assertEqual(ExportJob.objects.first().id, valid_job.id)

    @patch('requests.head')
    def test_validate_evidence_links_for_export(self, mock_requests):
        """Test evidence link validation for export"""
        # Create content with evidence links
        content_with_evidence = {
            'experience': [
                {
                    'title': 'Engineer',
                    'evidence_references': ['https://github.com/user/repo']
                }
            ],
            'projects': [
                {
                    'name': 'Web App',
                    'evidence_url': 'https://demo.app.com'
                }
            ]
        }

        self.generated_doc.content = content_with_evidence
        self.generated_doc.save()

        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf'
        )

        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.return_value = mock_response

        validated_count = validate_evidence_links_for_export(str(export_job.id))

        self.assertEqual(validated_count, 2)  # 2 links validated

        export_job.refresh_from_db()
        validated_links = export_job.export_options.get('validated_evidence_links', [])
        self.assertEqual(len(validated_links), 2)