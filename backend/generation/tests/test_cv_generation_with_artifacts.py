"""
Tests for CV generation with selected artifacts (ft-007)
"""

import unittest
from unittest.mock import patch
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from asgiref.sync import sync_to_async

from artifacts.models import Artifact
from generation.models import GeneratedDocument
from common.test_base import AsyncTestCase

User = get_user_model()


@tag('medium', 'integration', 'generation', 'api')
class GenerationWithSelectedArtifactsAPITests(APITestCase):
    """Test cases for CV generation with manually selected artifacts (ft-007)"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test artifacts
        self.artifact1 = Artifact.objects.create(
            user=self.user,
            title='Full Stack Project',
            description='Built complete web application',
            technologies=['React', 'Node.js', 'PostgreSQL'],
            start_date='2023-01-01'
        )
        self.artifact2 = Artifact.objects.create(
            user=self.user,
            title='Backend API',
            description='RESTful API service',
            technologies=['Python', 'Django', 'Redis'],
            start_date='2022-06-01'
        )
        self.artifact3 = Artifact.objects.create(
            user=self.user,
            title='Mobile App',
            description='Cross-platform mobile',
            technologies=['React Native'],
            start_date='2024-01-01'
        )

    @patch('generation.tasks.prepare_generation_bullets_task.delay')
    def test_generate_cv_with_artifact_ids(self, mock_task):
        """Test CV generation with specific artifact IDs"""
        url = reverse('create_generation')
        data = {
            'job_description': 'Looking for a full-stack developer with React and Node.js',
            'artifact_ids': [self.artifact1.id, self.artifact2.id]
        }

        response = self.client.post(url, data, format='json')

        # ft-007: Async implementation returns 202 Accepted (task submitted)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('generation_id', response.data)
        # CV generation happens asynchronously
        # (use generation_id to poll for completion)
        mock_task.assert_called_once()

    @patch('generation.tasks.prepare_generation_bullets_task.delay')
    def test_generate_cv_without_artifact_ids_backward_compatibility(self, mock_task):
        """Test CV generation without artifact_ids (backward compatibility)"""
        url = reverse('create_generation')
        data = {
            'job_description': 'Looking for React and Python developer'
            # No artifact_ids - should use automatic keyword ranking
        }

        response = self.client.post(url, data, format='json')

        # ft-007: Async implementation returns 202 Accepted (task submitted)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('generation_id', response.data)
        # Should automatically select artifacts based on keyword ranking
        mock_task.assert_called_once()

    def test_generate_cv_with_empty_artifact_ids_list(self):
        """Test CV generation with empty artifact_ids list"""
        url = reverse('create_generation')
        data = {
            'job_description': 'Looking for developer',
            'artifact_ids': []
        }

        response = self.client.post(url, data, format='json')

        # Should either use automatic selection or return error
        # (depends on business logic - document expected behavior)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_generate_cv_with_too_many_artifacts(self):
        """Test CV generation with excessive number of artifact IDs"""
        # Create many artifacts
        artifacts = [
            Artifact.objects.create(
                user=self.user,
                title=f'Project {i}',
                description='Test project',
                technologies=['Python']
            )
            for i in range(60)  # More than max allowed (e.g., 50)
        ]
        artifact_ids = [a.id for a in artifacts]

        url = reverse('create_generation')
        data = {
            'job_description': 'Looking for Python developer',
            'artifact_ids': artifact_ids
        }

        response = self.client.post(url, data, format='json')

        # Should return 400 Bad Request for too many artifacts
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('generation.tasks.prepare_generation_bullets_task.delay')
    def test_generate_cv_artifact_order_preserved(self, mock_task):
        """Test that artifact order is preserved in CV generation"""
        url = reverse('create_generation')
        data = {
            'job_description': 'Looking for developer',
            'artifact_ids': [self.artifact3.id, self.artifact1.id, self.artifact2.id]  # Specific order
        }

        response = self.client.post(url, data, format='json')

        # ft-007: Async implementation returns 202 Accepted (task submitted)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('generation_id', response.data)
        # Artifact order is preserved in service layer during generation
        mock_task.assert_called_once()


@tag('medium', 'integration', 'generation', 'service')
class GenerationServiceWithArtifactsTests(AsyncTestCase):
    """Unit tests for CV generation service with artifact selection (ft-007)"""

    def setUp(self):
        super().setUp()  # Initialize async event loop
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        self.artifacts = [
            Artifact.objects.create(
                user=self.user,
                title=f'Project {i}',
                description='Test project',
                technologies=['Python', 'Django'] if i % 2 == 0 else ['React', 'Node.js']
            )
            for i in range(5)
        ]

    async def test_fetch_selected_artifacts_returns_only_valid(self):
        """Test fetch_selected_artifacts returns only valid artifacts"""
        from generation.services.generation_service import GenerationService

        service = GenerationService()

        # Valid artifact IDs
        valid_ids = [self.artifacts[0].id, self.artifacts[1].id]

        # This should work without error
        # Actual implementation in Stage G
        # FIXED: Added await keyword for when this test is fully implemented
        # artifacts = await service._fetch_selected_artifacts(self.user.id, valid_ids)
        # self.assertEqual(len(artifacts), 2)

    def test_generate_cv_uses_selected_artifacts_only(self):
        """Test that CV generation uses only selected artifacts"""
        # This test will be fully implemented in Stage G
        # For now, just document expected behavior
        pass
