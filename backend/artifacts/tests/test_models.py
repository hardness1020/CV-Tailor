"""
Unit tests for artifacts app models
"""

import uuid
from datetime import date
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from artifacts.models import (
    Artifact, Evidence, ArtifactProcessingJob, UploadedFile
)

User = get_user_model()


@tag('medium', 'integration', 'artifacts')
class ArtifactModelTests(TestCase):
    """Test cases for Artifact model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_artifact_creation(self):
        """Test basic artifact creation"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='A test project description',
            artifact_type='project',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            technologies=['Python', 'Django'],
            collaborators=['John Doe']
        )

        self.assertEqual(artifact.title, 'Test Project')
        self.assertEqual(artifact.user, self.user)
        self.assertEqual(artifact.artifact_type, 'project')
        self.assertEqual(len(artifact.technologies), 2)
        self.assertEqual(len(artifact.collaborators), 1)
        self.assertTrue(artifact.created_at)
        self.assertTrue(artifact.updated_at)



    def test_user_context_optional(self):
        """Test user_context field is optional (ft-018)"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
            # user_context NOT provided
        )
        self.assertEqual(artifact.user_context, '')

    def test_user_context_stored(self):
        """Test user_context is stored correctly (ft-018)"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context='Led a team of 6 engineers. Reduced infrastructure costs by 40%.'
        )
        self.assertEqual(artifact.user_context, 'Led a team of 6 engineers. Reduced infrastructure costs by 40%.')

    def test_user_context_can_be_empty_string(self):
        """Test user_context accepts empty string (ft-018)"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context=''
        )
        self.assertEqual(artifact.user_context, '')

    def test_user_context_can_be_long_text(self):
        """Test user_context accepts long text (ft-018)"""
        long_context = "Led a team of 6 engineers over 18 months. " * 20  # ~900 chars
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context=long_context
        )
        self.assertEqual(len(artifact.user_context), len(long_context))


@tag('medium', 'integration', 'artifacts')
class EvidenceModelTests(TestCase):
    """Test cases for Evidence model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

    def test_evidence_link_creation(self):
        """Test evidence link creation"""
        evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='https://github.com/user/repo',
            evidence_type='github',
            description='Source code repository'
        )

        self.assertEqual(evidence.artifact, self.artifact)
        self.assertEqual(evidence.url, 'https://github.com/user/repo')
        self.assertEqual(evidence.evidence_type, 'github')
        self.assertTrue(evidence.is_accessible)

    def test_evidence_link_with_file_data(self):
        """Test evidence link with file-specific fields"""
        evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='http://example.com/file.pdf',
            evidence_type='document',
            description='Project documentation',
            file_path='uploads/file.pdf',
            file_size=1024000,
            mime_type='application/pdf'
        )

        self.assertEqual(evidence.file_size, 1024000)
        self.assertEqual(evidence.mime_type, 'application/pdf')
        self.assertEqual(evidence.file_path, 'uploads/file.pdf')

    def test_evidence_type_validation_github_accepted(self):
        """Test that 'github' evidence type is accepted"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://github.com/user/repo',
            evidence_type='github',
            description='GitHub repository'
        )
        # Should not raise ValidationError
        evidence.full_clean()
        evidence.save()
        self.assertEqual(evidence.evidence_type, 'github')

    def test_evidence_type_validation_document_accepted(self):
        """Test that 'document' evidence type is accepted with file_path"""
        evidence = Evidence(
            artifact=self.artifact,
            url='http://example.com/doc.pdf',
            evidence_type='document',
            description='Document',
            file_path='uploads/test_document.pdf'  # Required for document type
        )
        # Should not raise ValidationError
        evidence.full_clean()
        evidence.save()
        self.assertEqual(evidence.evidence_type, 'document')

    def test_evidence_type_validation_live_app_rejected(self):
        """Test that 'live_app' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://example.com/app',
            evidence_type='live_app',
            description='Live application'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))

    def test_evidence_type_validation_video_rejected(self):
        """Test that 'video' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://youtube.com/watch?v=123',
            evidence_type='video',
            description='Video demo'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))

    def test_evidence_type_validation_audio_rejected(self):
        """Test that 'audio' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://example.com/audio.mp3',
            evidence_type='audio',
            description='Audio file'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))

    def test_evidence_type_validation_website_rejected(self):
        """Test that 'website' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://example.com',
            evidence_type='website',
            description='Website'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))

    def test_evidence_type_validation_portfolio_rejected(self):
        """Test that 'portfolio' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://portfolio.example.com',
            evidence_type='portfolio',
            description='Portfolio'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))

    def test_evidence_type_validation_other_rejected(self):
        """Test that 'other' evidence type is rejected"""
        evidence = Evidence(
            artifact=self.artifact,
            url='https://example.com/other',
            evidence_type='other',
            description='Other type'
        )
        with self.assertRaises(ValidationError) as context:
            evidence.full_clean()
        self.assertIn('evidence_type', str(context.exception))


@tag('medium', 'integration', 'artifacts')
class ArtifactProcessingJobModelTests(TestCase):
    """Test cases for ArtifactProcessingJob model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

    def test_processing_job_creation(self):
        """Test processing job creation"""
        job = ArtifactProcessingJob.objects.create(
            artifact=self.artifact,
            status='pending'
        )

        self.assertEqual(job.artifact, self.artifact)
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.progress_percentage, 0)
        self.assertIsInstance(job.id, uuid.UUID)

    def test_processing_job_completion(self):
        """Test processing job completion"""
        job = ArtifactProcessingJob.objects.create(
            artifact=self.artifact,
            status='processing',
            progress_percentage=50
        )

        # Update to completed
        job.status = 'completed'
        job.progress_percentage = 100
        job.metadata_extracted = {'title': 'Extracted Title'}
        job.save()

        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.progress_percentage, 100)
        self.assertEqual(job.metadata_extracted['title'], 'Extracted Title')