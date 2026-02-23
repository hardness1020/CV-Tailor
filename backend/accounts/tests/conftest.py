"""
Pytest configuration and fixtures for accounts app tests
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

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
def admin_user():
    """Create a test admin user"""
    return User.objects.create_superuser(
        email='admin@example.com',
        username='admin',
        password='adminpass123'
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
def user_tokens(user):
    """Generate JWT tokens for a user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


@pytest.fixture
def multiple_users():
    """Create multiple test users"""
    users = []
    for i in range(3):
        user = User.objects.create_user(
            email=f'user{i}@example.com',
            username=f'user{i}',
            password=f'password{i}123',
            first_name=f'User{i}',
            last_name='Test'
        )
        users.append(user)
    return users