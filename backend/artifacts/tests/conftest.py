"""
Pytest configuration and fixtures for artifacts app tests
"""

import uuid
from datetime import date
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from artifacts.models import Artifact, Evidence, ArtifactProcessingJob, UploadedFile

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def other_user():
    """Create another test user"""
    return User.objects.create_user(
        email='other@example.com',
        username='otheruser',
        password='otherpass123',
        first_name='Other',
        last_name='User'
    )


@pytest.fixture
def api_client():
    """Create an API client"""
    return APIClient()


@pytest.fixture
def authenticated_client(user, api_client):
    """Create an authenticated API client"""
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api_client


@pytest.fixture
def artifact(user):
    """Create a test artifact"""
    return Artifact.objects.create(
        user=user,
        title='Test Project',
        description='A test project description',
        artifact_type='project',
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 1),
        technologies=['Python', 'Django'],
        collaborators=['John Doe']
    )


@pytest.fixture
def evidence_link(artifact):
    """Create a test evidence link"""
    return Evidence.objects.create(
        artifact=artifact,
        url='https://github.com/user/repo',
        link_type='github',
        description='Source code repository',
        is_accessible=True
    )


@pytest.fixture
def processing_job(artifact):
    """Create a test processing job"""
    return ArtifactProcessingJob.objects.create(
        artifact=artifact,
        status='pending',
        progress_percentage=0
    )


@pytest.fixture
def sample_file():
    """Create a sample uploaded file for testing"""
    return SimpleUploadedFile(
        "test.pdf",
        b"fake pdf content",
        content_type="application/pdf"
    )


@pytest.fixture
def multiple_artifacts(user):
    """Create multiple test artifacts"""
    artifacts = []
    for i in range(3):
        artifact = Artifact.objects.create(
            user=user,
            title=f'Project {i+1}',
            description=f'Test project {i+1}',
            artifact_type='project',
            technologies=[f'Tech{i+1}', 'Common']
        )
        artifacts.append(artifact)
    return artifacts