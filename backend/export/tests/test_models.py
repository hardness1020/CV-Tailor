"""
Unit tests for export app models
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone

from export.models import ExportJob, ExportTemplate, ExportAnalytics
from generation.models import GeneratedDocument, JobDescription

User = get_user_model()


@tag('fast', 'unit', 'export')
class ExportTemplateModelTests(TestCase):
    """Test cases for ExportTemplate model"""

    def test_export_template_creation(self):
        """Test basic export template creation"""
        template = ExportTemplate.objects.create(
            name='Professional Modern',
            category='modern',
            description='A professional modern template',
            template_config={
                'font_family': 'Arial',
                'font_size': 12,
                'margins': {'top': 1, 'bottom': 1, 'left': 1, 'right': 1}
            },
            css_styles='body { font-family: Arial; }',
            is_premium=False,
            is_active=True
        )

        self.assertEqual(template.name, 'Professional Modern')
        self.assertEqual(template.category, 'modern')
        self.assertFalse(template.is_premium)
        self.assertTrue(template.is_active)
        self.assertEqual(template.template_config['font_family'], 'Arial')



@tag('fast', 'unit', 'export')
class ExportJobModelTests(TestCase):
    """Test cases for ExportJob model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
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
                'key_skills': ['Python', 'Django']
            }
        )
        self.template = ExportTemplate.objects.create(
            name='Test Template',
            category='modern',
            description='Test template'
        )

    def test_export_job_creation(self):
        """Test basic export job creation"""
        job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            template=self.template,
            export_options={'include_evidence': True}
        )

        self.assertEqual(job.user, self.user)
        self.assertEqual(job.generated_document, self.generated_doc)
        self.assertEqual(job.format, 'pdf')
        self.assertEqual(job.template, self.template)
        self.assertEqual(job.status, 'processing')  # Default status
        self.assertIsInstance(job.id, uuid.UUID)

    def test_export_job_with_file_info(self):
        """Test export job with completed file information"""
        job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            file_path='exports/cv_1_test.pdf',
            file_size=2048,
            download_count=3
        )

        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.file_path, 'exports/cv_1_test.pdf')
        self.assertEqual(job.file_size, 2048)
        self.assertEqual(job.download_count, 3)

    def test_download_url_property(self):
        """Test download_url property"""
        # Completed job should have download URL
        job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='completed',
            file_path='exports/test.pdf'
        )
        expected_url = f"/api/v1/export/{job.id}/download"
        self.assertEqual(job.download_url, expected_url)

        # Processing job should not have download URL
        job2 = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf',
            status='processing'
        )
        self.assertIsNone(job2.download_url)



@tag('fast', 'unit', 'export')
class ExportAnalyticsModelTests(TestCase):
    """Test cases for ExportAnalytics model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.generated_doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123'
        )
        self.export_job = ExportJob.objects.create(
            user=self.user,
            generated_document=self.generated_doc,
            format='pdf'
        )

    def test_analytics_creation(self):
        """Test analytics record creation"""
        analytics = ExportAnalytics.objects.create(
            export_job=self.export_job,
            event_type='downloaded',
            metadata={'user_agent': 'Mozilla/5.0', 'referrer': 'direct'},
            user_agent='Mozilla/5.0 Chrome',
            ip_address='192.168.1.1'
        )

        self.assertEqual(analytics.export_job, self.export_job)
        self.assertEqual(analytics.event_type, 'downloaded')
        self.assertEqual(analytics.ip_address, '192.168.1.1')