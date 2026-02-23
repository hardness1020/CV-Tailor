"""
Unit tests for unified generation status endpoint (ft-026)

Following TDD RED phase - these tests will fail until implementation is complete.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from generation.models import (
    JobDescription, GeneratedDocument, BulletPoint, BulletGenerationJob
)
from artifacts.models import Artifact

User = get_user_model()


@tag('medium', 'integration', 'generation', 'status')
class GenerationStatusEndpointTests(APITestCase):
    """Test cases for unified generation status endpoint"""

    def setUp(self):
        """Set up test user, authentication, and test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test artifacts
        self.artifacts = [
            Artifact.objects.create(
                user=self.user,
                title=f'Project {i}',
                description=f'Description for project {i}',
                technologies=['Python', 'Django']
            )
            for i in range(1, 4)
        ]

        # Create test job description
        self.job_description = JobDescription.objects.create(
            company_name='TechCorp',
            role_title='Senior Developer',
            raw_content='Looking for experienced developer',
            content_hash='test-hash-123',
            parsing_confidence=0.95
        )

    def test_generation_status_endpoint_returns_comprehensive_response(self):
        """Test that status endpoint returns all required fields"""
        # Create generation with bullet jobs
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing',
            progress_percentage=60,
            model_version='gpt-4o-2024-05-13'
        )

        # Create bullet generation jobs
        for i, artifact in enumerate(self.artifacts[:2]):
            BulletGenerationJob.objects.create(
                user=self.user,
                artifact=artifact,
                cv_generation=generation,
                status='completed' if i == 0 else 'processing',
                progress_percentage=100 if i == 0 else 50,
                llm_cost_usd=0.02,
                tokens_used=500,
                processing_duration_ms=1500
            )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        # Assert response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Core status fields
        self.assertEqual(response.data['generation_id'], str(generation.id))
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['progress_percentage'], 60)
        self.assertIsNone(response.data['error_message'])
        self.assertIn('created_at', response.data)

        # Phase tracking
        self.assertEqual(response.data['current_phase'], 'bullet_generation')
        self.assertIn('phase_details', response.data)
        self.assertIn('bullet_generation', response.data['phase_details'])
        self.assertIn('assembly', response.data['phase_details'])

        # Sub-job aggregation
        self.assertIn('bullet_generation_jobs', response.data)
        self.assertEqual(len(response.data['bullet_generation_jobs']), 2)

        # Processing metrics
        self.assertIn('processing_metrics', response.data)
        self.assertIn('total_cost_usd', response.data['processing_metrics'])

        # Quality metrics
        self.assertIn('quality_metrics', response.data)

    def test_generation_status_aggregates_bullet_jobs(self):
        """Test that status endpoint correctly aggregates bullet generation jobs"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing'
        )

        # Create 3 jobs with different statuses
        jobs_data = [
            {'status': 'completed', 'bullets': 3, 'duration': 1500},
            {'status': 'processing', 'bullets': 0, 'duration': None},
            {'status': 'failed', 'bullets': 0, 'duration': 2000}
        ]

        for i, job_data in enumerate(jobs_data):
            job = BulletGenerationJob.objects.create(
                user=self.user,
                artifact=self.artifacts[i],
                cv_generation=generation,
                status=job_data['status'],
                processing_duration_ms=job_data['duration'],
                llm_cost_usd=0.02 if job_data['status'] == 'completed' else 0,
                tokens_used=500 if job_data['status'] == 'completed' else 0
            )

            # Add bullets for completed job
            if job_data['status'] == 'completed':
                for pos in range(1, 4):
                    BulletPoint.objects.create(
                        artifact=self.artifacts[i],
                        cv_generation=generation,
                        position=pos,
                        bullet_type=['achievement', 'technical', 'impact'][pos - 1],
                        text=f'Bullet {pos} for artifact {i}',
                        quality_score=0.85,
                        keyword_relevance_score=0.90,
                        confidence_score=0.88
                    )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check bullet job aggregation
        jobs = response.data['bullet_generation_jobs']
        self.assertEqual(len(jobs), 3)

        # Verify completed job details
        completed_job = next(j for j in jobs if j['status'] == 'completed')
        self.assertEqual(completed_job['artifact_id'], self.artifacts[0].id)
        self.assertEqual(completed_job['artifact_title'], 'Project 1')
        self.assertEqual(completed_job['bullets_generated'], 3)
        self.assertEqual(completed_job['processing_duration_ms'], 1500)
        self.assertIsNone(completed_job['error_message'])

        # Verify processing job
        processing_job = next(j for j in jobs if j['status'] == 'processing')
        self.assertEqual(processing_job['bullets_generated'], 0)
        self.assertIsNone(processing_job['processing_duration_ms'])

        # Verify failed job
        failed_job = next(j for j in jobs if j['status'] == 'failed')
        self.assertEqual(failed_job['artifact_title'], 'Project 3')

    def test_generation_status_calculates_phase_details(self):
        """Test phase-level status calculation"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing',
            bullets_generated_at=None
        )

        # Create 5 jobs: 3 completed, 2 processing
        for i in range(5):
            BulletGenerationJob.objects.create(
                user=self.user,
                artifact=self.artifacts[i % len(self.artifacts)],
                cv_generation=generation,
                status='completed' if i < 3 else 'processing',
                llm_cost_usd=0.02,
                tokens_used=500
            )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check bullet generation phase
        bullet_phase = response.data['phase_details']['bullet_generation']
        self.assertEqual(bullet_phase['status'], 'in_progress')
        self.assertEqual(bullet_phase['artifacts_total'], 5)
        self.assertEqual(bullet_phase['artifacts_processed'], 3)
        self.assertIsNotNone(bullet_phase['started_at'])
        self.assertIsNone(bullet_phase['completed_at'])

        # Check assembly phase (not started yet)
        assembly_phase = response.data['phase_details']['assembly']
        self.assertEqual(assembly_phase['status'], 'not_started')
        self.assertIsNone(assembly_phase['started_at'])
        self.assertIsNone(assembly_phase['completed_at'])

    def test_generation_status_bullets_ready_phase(self):
        """Test status when bullets are ready for review"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='bullets_ready',
            bullets_generated_at=timezone.now(),
            bullets_count=9
        )

        # Create 3 completed jobs
        for artifact in self.artifacts:
            BulletGenerationJob.objects.create(
                user=self.user,
                artifact=artifact,
                cv_generation=generation,
                status='completed'
            )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_phase'], 'bullet_review')
        self.assertEqual(response.data['status'], 'bullets_ready')

        # Bullet generation phase should be completed
        bullet_phase = response.data['phase_details']['bullet_generation']
        self.assertEqual(bullet_phase['status'], 'completed')
        self.assertEqual(bullet_phase['artifacts_processed'], 3)
        self.assertIsNotNone(bullet_phase['completed_at'])

    def test_generation_status_assembly_phase(self):
        """Test status during CV assembly"""
        now = timezone.now()
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='assembling',
            bullets_generated_at=now - timedelta(minutes=5),
            bullets_count=9
        )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_phase'], 'assembly')

        # Assembly phase should be in progress
        assembly_phase = response.data['phase_details']['assembly']
        self.assertEqual(assembly_phase['status'], 'in_progress')
        self.assertIsNotNone(assembly_phase['started_at'])
        self.assertIsNone(assembly_phase['completed_at'])

    def test_generation_status_completed_state(self):
        """Test status for completed generation"""
        now = timezone.now()
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='completed',
            bullets_generated_at=now - timedelta(minutes=10),
            assembled_at=now - timedelta(minutes=2),
            bullets_count=9,
            model_version='gpt-4o-2024-05-13',
            content={'summary': 'Test CV content'}
        )

        # Create completed jobs
        for artifact in self.artifacts:
            job = BulletGenerationJob.objects.create(
                user=self.user,
                artifact=artifact,
                cv_generation=generation,
                status='completed',
                llm_cost_usd=0.02,
                tokens_used=500,
                processing_duration_ms=1500
            )

            # Add bullets with quality scores
            for pos in range(1, 4):
                BulletPoint.objects.create(
                    artifact=artifact,
                    cv_generation=generation,
                    position=pos,
                    bullet_type=['achievement', 'technical', 'impact'][pos - 1],
                    text=f'Bullet {pos}',
                    quality_score=0.85 + (pos * 0.02),
                    keyword_relevance_score=0.90,
                    confidence_score=0.88,
                    user_approved=True if pos <= 2 else False,
                    user_edited=True if pos == 3 else False
                )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['current_phase'], 'completed')

        # Check processing metrics
        metrics = response.data['processing_metrics']
        self.assertIsNotNone(metrics['total_duration_ms'])
        self.assertEqual(metrics['total_cost_usd'], 0.06)  # 3 jobs * 0.02
        self.assertEqual(metrics['total_tokens_used'], 1500)  # 3 jobs * 500
        self.assertEqual(metrics['model_version'], 'gpt-4o-2024-05-13')

        # Check quality metrics
        quality = response.data['quality_metrics']
        self.assertIsNotNone(quality['average_bullet_quality'])
        self.assertIsNotNone(quality['average_keyword_relevance'])
        self.assertEqual(quality['bullets_approved'], 6)  # 2 approved per artifact
        self.assertEqual(quality['bullets_rejected'], 0)
        self.assertEqual(quality['bullets_edited'], 3)  # 1 edited per artifact

    def test_generation_status_failed_state(self):
        """Test status for failed generation"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='failed',
            error_message='LLM API timeout after 3 retries'
        )

        # Create some failed jobs
        for artifact in self.artifacts[:2]:
            BulletGenerationJob.objects.create(
                user=self.user,
                artifact=artifact,
                cv_generation=generation,
                status='failed',
                error_message='API timeout'
            )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'failed')
        self.assertEqual(response.data['error_message'], 'LLM API timeout after 3 retries')

        # Check failed jobs
        jobs = response.data['bullet_generation_jobs']
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job['status'], 'failed')
            self.assertIsNotNone(job['error_message'])

    def test_generation_status_handles_missing_generation(self):
        """Test 404 response for non-existent generation"""
        fake_id = uuid.uuid4()
        url = reverse('generation_status', kwargs={'generation_id': fake_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generation_status_requires_authentication(self):
        """Test that unauthenticated requests are rejected"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing'
        )

        # Remove authentication
        self.client.credentials()

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generation_status_enforces_ownership(self):
        """Test that users can only view their own generations"""
        # Create another user
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )

        # Create generation owned by other user
        other_job_description = JobDescription.objects.create(
            company_name='OtherCorp',
            role_title='Developer',
            raw_content='Looking for developer',
            content_hash='other-hash',
            parsing_confidence=0.90
        )
        generation = GeneratedDocument.objects.create(
            user=other_user,
            document_type='cv',
            job_description=other_job_description,
            job_description_hash='other-hash',
            status='processing'
        )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        # Should return 404 to avoid leaking existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generation_status_empty_jobs_list(self):
        """Test status when no bullet generation jobs exist yet"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='pending'
        )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

        # Bullet generation jobs should be empty
        self.assertEqual(len(response.data['bullet_generation_jobs']), 0)

        # Phase details should reflect no jobs
        bullet_phase = response.data['phase_details']['bullet_generation']
        self.assertEqual(bullet_phase['artifacts_total'], 0)
        self.assertEqual(bullet_phase['artifacts_processed'], 0)
        self.assertEqual(bullet_phase['bullets_generated'], 0)

    def test_generation_status_partial_completion(self):
        """Test status when some bullet jobs are still pending"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing'
        )

        # Create jobs with mixed statuses
        statuses = ['completed', 'processing', 'pending', 'completed', 'pending']
        for i, job_status in enumerate(statuses):
            BulletGenerationJob.objects.create(
                user=self.user,
                artifact=self.artifacts[i % len(self.artifacts)],
                cv_generation=generation,
                status=job_status
            )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check partial completion
        bullet_phase = response.data['phase_details']['bullet_generation']
        self.assertEqual(bullet_phase['status'], 'in_progress')
        self.assertEqual(bullet_phase['artifacts_total'], 5)
        self.assertEqual(bullet_phase['artifacts_processed'], 2)  # Only completed jobs

    def test_generation_status_needs_review_jobs(self):
        """Test status when jobs are in needs_review state"""
        generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description=self.job_description,
            job_description_hash='test-hash-123',
            status='processing'
        )

        # Create job that needs review (max attempts reached)
        BulletGenerationJob.objects.create(
            user=self.user,
            artifact=self.artifacts[0],
            cv_generation=generation,
            status='needs_review',
            generation_attempts=3,
            max_attempts=3,
            error_message='Quality validation failed after max attempts'
        )

        url = reverse('unified_generation_status', kwargs={'generation_id': generation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check needs_review job
        jobs = response.data['bullet_generation_jobs']
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['status'], 'needs_review')
        self.assertIsNotNone(jobs[0]['error_message'])
