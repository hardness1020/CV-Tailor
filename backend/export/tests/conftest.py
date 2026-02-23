"""
Pytest configuration and fixtures for export app tests
"""

import uuid
from datetime import datetime, timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from export.models import ExportJob, ExportTemplate, ExportAnalytics
from generation.models import GeneratedDocument, JobDescription

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
def job_description():
    """Create a test job description"""
    return JobDescription.objects.create(
        content_hash='test123',
        raw_content='Looking for Python developer'
    )


@pytest.fixture
def generated_document(user, job_description):
    """Create a test generated document"""
    return GeneratedDocument.objects.create(
        user=user,
        document_type='cv',
        job_description_hash='test123',
        job_description=job_description,
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


@pytest.fixture
def export_template():
    """Create a test export template"""
    return ExportTemplate.objects.create(
        name='Test Template',
        category='modern',
        description='A test export template',
        template_config={
            'font_family': 'Arial',
            'font_size': 12,
            'margins': {'top': 1, 'bottom': 1, 'left': 1, 'right': 1}
        },
        css_styles='body { font-family: Arial; }',
        is_active=True,
        is_premium=False
    )


@pytest.fixture
def export_job(user, generated_document, export_template):
    """Create a test export job"""
    return ExportJob.objects.create(
        user=user,
        generated_document=generated_document,
        format='pdf',
        template=export_template,
        export_options={'include_evidence': False},
        status='processing',
        expires_at=timezone.now() + timedelta(days=7)
    )