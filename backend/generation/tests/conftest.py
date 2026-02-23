"""
Pytest configuration and fixtures for generation app tests
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from generation.models import JobDescription, GeneratedDocument, CVTemplate

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
        raw_content='Looking for Python developer with Django experience',
        company_name='TechCorp',
        role_title='Python Developer',
        parsing_confidence=0.9,
        parsed_data={
            'must_have_skills': ['Python', 'Django'],
            'nice_to_have_skills': ['React'],
            'experience_level': 'mid'
        }
    )


@pytest.fixture
def cv_template():
    """Create a test CV template"""
    return CVTemplate.objects.create(
        name='Test Template',
        category='modern',
        description='A test template for testing',
        template_config={'font': 'Arial', 'color': '#000'},
        prompt_template='Generate CV with: {requirements}',
        is_active=True,
        is_premium=False
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