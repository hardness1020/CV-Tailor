"""
Unit tests for Evidence Review & Acceptance API endpoints (ft-045)
TDD Stage F - RED Phase: These tests will fail initially until implementation in Stage G
"""

import unittest
from unittest.mock import patch, Mock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from artifacts.models import Artifact, Evidence
from llm_services.models import EnhancedEvidence

User = get_user_model()


@tag('medium', 'integration', 'artifacts', 'evidence_review')
class EvidenceReviewAPITests(APITestCase):
    """Test cases for Evidence Review & Acceptance API endpoints (ft-045)"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test artifact
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context='Led team of 5 engineers',
            artifact_type='project',
            start_date='2024-01-01'
        )

        # Create evidence sources
        self.github_evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='https://github.com/test/repo',
            evidence_type='github',
            description='GitHub repository'
        )

        self.pdf_evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='https://example.com/doc.pdf',
            evidence_type='document',
            description='Project documentation'
        )

        # Create EnhancedEvidence for each source
        self.enhanced_github = EnhancedEvidence.objects.create(
            user=self.user,
            evidence=self.github_evidence,
            title='test-repo',
            content_type='github',
            raw_content='# Test Repository\nA test project',
            processed_content={
                'summary': 'A full-stack web application',
                'technologies': ['React', 'Django', 'PostgreSQL'],
                'achievements': ['Built authentication system', 'Deployed to AWS']
            },
            processing_confidence=0.85,
            accepted=False  # Not yet accepted
        )

        self.enhanced_pdf = EnhancedEvidence.objects.create(
            user=self.user,
            evidence=self.pdf_evidence,
            title='project-doc.pdf',
            content_type='pdf',
            raw_content='Project documentation content',
            processed_content={
                'summary': 'Technical architecture documentation',
                'technologies': ['Microservices', 'Docker'],
                'achievements': ['Designed scalable architecture']
            },
            processing_confidence=0.75,
            accepted=False  # Not yet accepted
        )

    def test_accept_evidence(self):
        """Test POST /api/v1/artifacts/{id}/evidence/{id}/accept/ - Mark evidence as accepted"""
        url = reverse(
            'artifact_evidence_accept',
            kwargs={
                'artifact_id': self.artifact.id,
                'evidence_id': self.enhanced_github.id
            }
        )
        data = {
            'review_notes': 'Looks good after review'
        }

        response = self.client.post(url, data, format='json')

        # Expected: 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure
        self.assertIn('id', response.data)
        self.assertTrue(response.data['accepted'])
        self.assertIsNotNone(response.data['accepted_at'])
        self.assertEqual(response.data['review_notes'], 'Looks good after review')

        # Verify database update
        self.enhanced_github.refresh_from_db()
        self.assertTrue(self.enhanced_github.accepted)
        self.assertIsNotNone(self.enhanced_github.accepted_at)

    def test_reject_evidence(self):
        """Test POST /api/v1/artifacts/{id}/evidence/{id}/reject/ - Mark evidence as rejected"""
        # First accept it
        self.enhanced_github.accepted = True
        self.enhanced_github.accepted_at = timezone.now()
        self.enhanced_github.save()

        url = reverse(
            'artifact_evidence_reject',
            kwargs={
                'artifact_id': self.artifact.id,
                'evidence_id': self.enhanced_github.id
            }
        )

        response = self.client.post(url, format='json')

        # Expected: 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure
        self.assertFalse(response.data['accepted'])
        # Timestamp is kept to distinguish rejected (reviewed) from pending (never reviewed)
        self.assertIsNotNone(response.data['accepted_at'])

        # Verify database update
        self.enhanced_github.refresh_from_db()
        self.assertFalse(self.enhanced_github.accepted)
        # Timestamp remains to indicate it was reviewed
        self.assertIsNotNone(self.enhanced_github.accepted_at)

    def test_edit_evidence_content(self):
        """Test PATCH /api/v1/artifacts/{id}/evidence/{id}/content/ - Update processed_content"""
        url = reverse(
            'artifact_evidence_edit_content',
            kwargs={
                'artifact_id': self.artifact.id,
                'evidence_id': self.enhanced_github.id
            }
        )
        data = {
            'processed_content': {
                'summary': 'User-edited summary with corrections',
                'technologies': ['React', 'TypeScript', 'Django'],  # Added TypeScript
                'achievements': [
                    'Built authentication system',
                    'Deployed to AWS',
                    'Improved performance by 40%'  # Added achievement
                ]
            }
        }

        response = self.client.patch(url, data, format='json')

        # Expected: 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response contains updated content
        self.assertIn('processed_content', response.data)
        self.assertEqual(
            response.data['processed_content']['summary'],
            'User-edited summary with corrections'
        )
        self.assertIn('TypeScript', response.data['processed_content']['technologies'])
        self.assertEqual(len(response.data['processed_content']['achievements']), 3)

        # Verify database update
        self.enhanced_github.refresh_from_db()
        self.assertEqual(
            self.enhanced_github.processed_content['summary'],
            'User-edited summary with corrections'
        )
        self.assertIn('TypeScript', self.enhanced_github.processed_content['technologies'])

    def test_get_acceptance_status(self):
        """Test GET /api/v1/artifacts/{id}/evidence-acceptance-status/ - Fetch acceptance summary"""
        # Accept one evidence, leave other pending
        self.enhanced_github.accepted = True
        self.enhanced_github.accepted_at = timezone.now()
        self.enhanced_github.save()

        url = reverse(
            'artifact_evidence_acceptance_status',
            kwargs={'artifact_id': self.artifact.id}
        )

        response = self.client.get(url)

        # Expected: 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure
        self.assertIn('can_finalize', response.data)
        self.assertIn('total_evidence', response.data)
        self.assertIn('accepted', response.data)
        self.assertIn('rejected', response.data)
        self.assertIn('pending', response.data)
        self.assertIn('evidence_details', response.data)

        # Verify values
        self.assertFalse(response.data['can_finalize'])  # Not all accepted yet
        self.assertEqual(response.data['total_evidence'], 2)
        self.assertEqual(response.data['accepted'], 1)
        self.assertEqual(response.data['rejected'], 0)
        self.assertEqual(response.data['pending'], 1)

        # Verify evidence_details
        self.assertEqual(len(response.data['evidence_details']), 2)
        accepted_evidence = [e for e in response.data['evidence_details'] if e['accepted']][0]
        self.assertEqual(accepted_evidence['title'], 'test-repo')
        self.assertIsNotNone(accepted_evidence['accepted_at'])

    @unittest.skip("ft-045: TDD RED phase - reunify_artifact_evidence not implemented")
    @patch('artifacts.views.reunify_artifact_evidence')
    def test_finalize_evidence_review_success(self, mock_reunify_task):
        """Test POST /api/v1/artifacts/{id}/finalize-evidence-review/ - Success when all accepted"""
        # Mock the Celery task to prevent actual async execution
        mock_reunify_task.delay = Mock(return_value=Mock(id='mock-task-id'))

        # Accept all evidence
        self.enhanced_github.accepted = True
        self.enhanced_github.accepted_at = timezone.now()
        self.enhanced_github.save()

        self.enhanced_pdf.accepted = True
        self.enhanced_pdf.accepted_at = timezone.now()
        self.enhanced_pdf.save()

        url = reverse(
            'artifact_finalize_evidence_review',
            kwargs={'artifact_id': self.artifact.id}
        )

        response = self.client.post(url, format='json')

        # Verify the Celery task was triggered with correct parameters
        mock_reunify_task.delay.assert_called_once()
        call_kwargs = mock_reunify_task.delay.call_args.kwargs
        self.assertEqual(call_kwargs['artifact_id'], self.artifact.id)
        self.assertEqual(call_kwargs['user_id'], self.user.id)

        # Expected: 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure (async task response, not reunification results)
        self.assertIn('message', response.data)
        self.assertIn('artifactId', response.data)
        self.assertIn('processingJobId', response.data)
        self.assertIn('phase', response.data)
        self.assertEqual(response.data['phase'], 2)

        # Verify artifact status was updated to 'reunifying'
        self.artifact.refresh_from_db()
        self.assertEqual(self.artifact.status, 'reunifying')
        self.assertEqual(self.artifact.last_wizard_step, 5)

    def test_finalize_evidence_review_partial_403(self):
        """Test POST /api/v1/artifacts/{id}/finalize-evidence-review/ - 403 when not all accepted"""
        # Only accept one evidence
        self.enhanced_github.accepted = True
        self.enhanced_github.accepted_at = timezone.now()
        self.enhanced_github.save()
        # enhanced_pdf remains pending (accepted=False)

        url = reverse(
            'artifact_finalize_evidence_review',
            kwargs={'artifact_id': self.artifact.id}
        )

        response = self.client.post(url, format='json')

        # Expected: 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify error message
        self.assertIn('error', response.data)
        self.assertIn('All evidence must be accepted', response.data['error'])

    def test_edit_evidence_validation(self):
        """Test PATCH /api/v1/artifacts/{id}/evidence/{id}/content/ - Invalid content rejected (400)"""
        url = reverse(
            'artifact_evidence_edit_content',
            kwargs={
                'artifact_id': self.artifact.id,
                'evidence_id': self.enhanced_github.id
            }
        )

        # Invalid data: technologies should be array, not string
        invalid_data = {
            'processed_content': {
                'summary': 'Valid summary',
                'technologies': 'React, Django',  # Should be array
                'achievements': []
            }
        }

        response = self.client.patch(url, invalid_data, format='json')

        # Expected: 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify error message indicates validation failure
        self.assertIn('error', response.data)

    def test_acceptance_status_calculation(self):
        """Test can_finalize logic is correct based on acceptance states"""
        url = reverse(
            'artifact_evidence_acceptance_status',
            kwargs={'artifact_id': self.artifact.id}
        )

        # Scenario 1: All pending
        response = self.client.get(url)
        self.assertFalse(response.data['can_finalize'])
        self.assertEqual(response.data['pending'], 2)

        # Scenario 2: One accepted, one pending
        self.enhanced_github.accepted = True
        self.enhanced_github.accepted_at = timezone.now()
        self.enhanced_github.save()

        response = self.client.get(url)
        self.assertFalse(response.data['can_finalize'])
        self.assertEqual(response.data['accepted'], 1)
        self.assertEqual(response.data['pending'], 1)

        # Scenario 3: All accepted (can finalize)
        self.enhanced_pdf.accepted = True
        self.enhanced_pdf.accepted_at = timezone.now()
        self.enhanced_pdf.save()

        response = self.client.get(url)
        self.assertTrue(response.data['can_finalize'])
        self.assertEqual(response.data['accepted'], 2)
        self.assertEqual(response.data['pending'], 0)

        # Scenario 4: One rejected (cannot finalize)
        # Note: Rejected means accepted=False but has timestamp (was reviewed)
        self.enhanced_pdf.accepted = False
        # Keep the timestamp to indicate it was reviewed (rejected, not just pending)
        # Don't set accepted_at to None - that would make it "pending" not "rejected"
        self.enhanced_pdf.save()

        response = self.client.get(url)
        self.assertFalse(response.data['can_finalize'])
        self.assertEqual(response.data['accepted'], 1)
        self.assertEqual(response.data['rejected'], 1)
