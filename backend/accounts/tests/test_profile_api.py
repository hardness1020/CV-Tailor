"""
Unit tests for accounts app user profile API endpoints
"""

from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@tag('medium', 'integration', 'accounts', 'api')
class UserProfileAPITests(APITestCase):
    """Test cases for user profile management"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_user_profile(self):
        """Test retrieving user profile"""
        url = reverse('profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['username'], 'testuser')

    def test_update_user_profile(self):
        """Test updating user profile"""
        url = reverse('profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio',
            'location': 'New York, NY',
            'phone': '+1234567890'
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')

    def test_change_password(self):
        """Test password change endpoint"""
        url = reverse('change_password')
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpassword123',
            'new_password_confirm': 'newpassword123'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

    def test_change_password_wrong_current(self):
        """Test password change with wrong current password"""
        url = reverse('change_password')
        data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'new_password_confirm': 'newpassword123'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch(self):
        """Test password change with mismatched new passwords"""
        url = reverse('change_password')
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpassword123',
            'new_password_confirm': 'differentpassword123'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthorized_profile_access(self):
        """Test that unauthenticated users can't access profile"""
        self.client.credentials()  # Remove auth

        url = reverse('profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_unauthorized(self):
        """Test password change without authentication"""
        self.client.credentials()  # Remove auth

        data = {
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }

        response = self.client.post(reverse('change_password'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@tag('medium', 'integration', 'accounts', 'api')
class UserPreferencesTests(APITestCase):
    """Test cases for user preferences"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_update_cv_template_preference(self):
        """Test updating preferred CV template"""
        url = reverse('profile')
        data = {'preferred_cv_template': 2}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_cv_template, 2)

    def test_update_email_notifications(self):
        """Test updating email notification preferences"""
        url = reverse('profile')
        data = {'email_notifications': False}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertFalse(self.user.email_notifications)


@tag('medium', 'integration', 'accounts', 'api')
class PasswordResetTests(APITestCase):
    """Test cases for password reset functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_password_reset_request(self):
        """Test password reset request"""
        url = reverse('password_reset_request')
        data = {'email': 'test@example.com'}

        response = self.client.post(url, data, format='json')

        # Should return success even for security (don't reveal if email exists)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email"""
        url = reverse('password_reset_request')
        data = {'email': 'nonexistent@example.com'}

        response = self.client.post(url, data, format='json')

        # Should still return success for security
        self.assertEqual(response.status_code, status.HTTP_200_OK)