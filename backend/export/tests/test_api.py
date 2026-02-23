"""
Unit tests for export app API endpoints
"""

import uuid
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from export.models import ExportJob, ExportTemplate, ExportAnalytics
from generation.models import GeneratedDocument, JobDescription

User = get_user_model()


@tag('medium', 'integration', 'export', 'api')
class ExportAPITests(APITestCase):
    """Test cases for Export API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test data
        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Test job description'
        )
        self.generated_doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc,
            status='completed',
            content={
                'professional_summary': 'Experienced developer',
                'key_skills': ['Python', 'Django'],
                'experience': [
                    {
                        'title': 'Software Engineer',
                        'organization': 'TechCorp',
                        'achievements': ['Built web applications']
                    }
                ]
            }
        )
        self.template = ExportTemplate.objects.create(
            name='Test Template',
            category='modern',
            description='Test template',
            is_active=True
        )

    @patch('export.tasks.export_document_task.delay')
    def test_export_document_pdf(self, mock_task):
        """Test PDF export request"""
        url = reverse('export_document', kwargs={'generation_id': self.generated_doc.id})
        data = {
            'format': 'pdf',
            'template_id': self.template.id,
            'options': {
                'include_evidence': False,
                'page_margins': 'normal',
                'font_size': 12
            },
            'sections': {
                'include_professional_summary': True,
                'include_skills': True,
                'include_experience': True
            }
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('export_id', response.data)
        self.assertEqual(response.data['status'], 'processing')

        # Check that export job was created
        self.assertEqual(ExportJob.objects.count(), 1)
        export_job = ExportJob.objects.first()
        self.assertEqual(export_job.format, 'pdf')
        self.assertEqual(export_job.template, self.template)

        # Check that async task was called
        mock_task.assert_called_once()

    @patch('export.tasks.validate_evidence_links_for_export.delay')
    @patch('export.tasks.export_document_task.delay')
    def test_export_document_docx(self, mock_export_task, mock_validate_task):
        """Test DOCX export request"""
        url = reverse('export_document', kwargs={'generation_id': self.generated_doc.id})
        data = {
            'format': 'docx',
            'template_id': self.template.id,
            'options': {
                'include_evidence': True,
                'evidence_format': 'hyperlinks'
            },
            'sections': {
                'include_professional_summary': True,
                'include_skills': True,
                'include_experience': True
            }
        }

        response = self.client.post(url, data, format='json')

        if response.status_code != status.HTTP_202_ACCEPTED:
            print(f"Error response: {response.data}")
            print(f"Status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        export_job = ExportJob.objects.first()
        self.assertEqual(export_job.format, 'docx')
        self.assertTrue(export_job.export_options['options']['include_evidence'])

        # Check that async tasks were called
        mock_export_task.assert_called_once()
        mock_validate_task.assert_called_once()

    def test_export_document_not_found(self):
        """Test export request for non-existent generation"""
        fake_id = str(uuid.uuid4())
        url = reverse('export_document', kwargs={'generation_id': fake_id})
        data = {'format': 'pdf'}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_status(self):
        """Test export status endpoint"""
        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            progress_percentage=100,
            file_path='exports/test.pdf',
            file_size=2048
        )

        url = reverse('export_status', kwargs={'export_id': export_job.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['progress_percentage'], 100)
        self.assertEqual(response.data['file_size'], 2048)

    def test_export_status_not_found(self):
        """Test export status for non-existent export"""
        fake_id = str(uuid.uuid4())
        url = reverse('export_status', kwargs={'export_id': fake_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('export.views.default_storage')
    def test_download_export_success(self, mock_storage):
        """Test successful file download"""
        # Mock file content
        file_content = b'%PDF-1.4 fake pdf content'
        mock_file = Mock()
        mock_file.read.return_value = file_content
        mock_storage.open.return_value = mock_file
        mock_storage.exists.return_value = True

        export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            file_path='exports/test.pdf',
            file_size=len(file_content),
            expires_at=timezone.now() + timedelta(hours=1)
        )

        url = reverse('download_export', kwargs={'export_id': export_job.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

        # Check download count was incremented
        export_job.refresh_from_db()
        self.assertEqual(export_job.download_count, 1)

        # Check analytics was created
        self.assertEqual(ExportAnalytics.objects.count(), 1)

    def test_user_exports_list(self):
        """Test listing user's exports"""
        # Create test exports
        ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf'
        )
        ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='docx'
        )

        url = reverse('user_exports_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


@tag('medium', 'integration', 'export', 'api')
class ExportTemplateAPITests(APITestCase):
    """Test cases for Export Template API"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test templates
        ExportTemplate.objects.create(
            name='Modern',
            category='modern',
            description='Modern template',
            is_active=True
        )
        ExportTemplate.objects.create(
            name='Classic',
            category='classic',
            description='Classic template',
            is_active=True
        )
        ExportTemplate.objects.create(
            name='Inactive',
            category='modern',
            description='Inactive template',
            is_active=False
        )

    def test_list_active_templates(self):
        """Test listing only active templates"""
        url = reverse('export_templates_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # Only active templates

        template_names = [t['name'] for t in response.data['results']]
        self.assertIn('Modern', template_names)
        self.assertIn('Classic', template_names)
        self.assertNotIn('Inactive', template_names)


@tag('medium', 'integration', 'export', 'api')
class ExportAnalyticsAPITests(APITestCase):
    """Test cases for export analytics API"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        self.generated_doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123'
        )

        self.template = ExportTemplate.objects.create(
            name='Test Template',
            category='modern',
            description='Test template'
        )

        # Create test exports
        ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            template=self.template,
            status='completed',
            download_count=2,
            file_size=2048
        )
        ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='docx',
            status='completed',
            download_count=1,
            file_size=1024
        )
        ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='failed'
        )

    def test_export_analytics(self):
        """Test export analytics endpoint"""
        url = reverse('export_analytics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        analytics = response.data
        self.assertEqual(analytics['total_exports'], 3)
        self.assertEqual(analytics['completed_exports'], 2)
        self.assertEqual(analytics['failed_exports'], 1)
        self.assertEqual(analytics['total_downloads'], 3)  # 2 + 1

        # Check format distribution
        self.assertEqual(analytics['format_distribution']['pdf'], 2)
        self.assertEqual(analytics['format_distribution']['docx'], 1)

        # Check template usage
        self.assertEqual(analytics['template_usage']['Test Template'], 1)


