"""
Unit tests for accounts app authentication API endpoints
"""

from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@tag('medium', 'integration', 'accounts', 'api')
class AuthenticationAPITests(APITestCase):
    """Test cases for authentication API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }

        initial_count = User.objects.count()
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), initial_count + 1)

        # Check response format matches frontend expectations
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')
        self.assertEqual(response.data['user']['username'], 'newuser@example.com')

        new_user = User.objects.get(email='newuser@example.com')
        self.assertEqual(new_user.username, 'newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')

    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'newpass123',
            'password_confirm': 'differentpass123',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Test registration with existing email"""
        url = reverse('register')
        data = {
            'email': 'test@example.com',  # Already exists
            'username': 'newuser',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login(self):
        """Test user login endpoint"""
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check response format matches frontend expectations
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh(self):
        """Test JWT token refresh"""
        refresh = RefreshToken.for_user(self.user)

        url = reverse('token_refresh')
        data = {'refresh': str(refresh)}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_refresh_invalid(self):
        """Test token refresh with invalid token"""
        url = reverse('token_refresh')
        data = {'refresh': 'invalid_token'}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        """Test user logout endpoint"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        url = reverse('logout')
        data = {'refresh': str(refresh)}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag('medium', 'integration', 'accounts', 'api')
class AuthenticationEndpointTests(APITestCase):
    """Test authentication endpoints for proper response format and error handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_login_response_format(self):
        """Test login response includes all required fields"""
        response = self.client.post(
            reverse('login'),
            {'email': 'test@example.com', 'password': 'testpass123'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        required_fields = ['user', 'access', 'refresh']
        for field in required_fields:
            self.assertIn(field, response.data)

        # Check user object structure
        user_data = response.data['user']
        user_required_fields = ['id', 'email', 'username', 'first_name', 'last_name']
        for field in user_required_fields:
            self.assertIn(field, user_data)

    def test_register_response_format(self):
        """Test registration response includes all required fields"""
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = self.client.post(reverse('register'), data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        required_fields = ['user', 'access', 'refresh']
        for field in required_fields:
            self.assertIn(field, response.data)

    def test_logout_with_invalid_refresh_token(self):
        """Test logout with invalid refresh token"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.client.post(
            reverse('logout'),
            {'refresh': 'invalid_refresh_token'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields(self):
        """Test login with missing email or password"""
        # Missing password
        response = self.client.post(
            reverse('login'),
            {'email': 'test@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing email
        response = self.client.post(
            reverse('login'),
            {'password': 'testpass123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email_format(self):
        """Test registration with invalid email format"""
        data = {
            'email': 'invalid-email',
            'username': 'testuser',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        response = self.client.post(reverse('register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@tag('medium', 'integration', 'accounts', 'api')
class TokenSecurityTests(APITestCase):
    """Test JWT token security and validation"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_access_token_expiry_handling(self):
        """Test that expired access tokens are rejected"""
        # Login to get tokens
        response = self.client.post(
            reverse('login'),
            {'email': 'test@example.com', 'password': 'testpass123'},
            format='json'
        )

        # Use a clearly invalid token
        invalid_token = 'invalid.jwt.token'
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {invalid_token}')

        # Try to access protected endpoint
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_with_valid_token(self):
        """Test token refresh with valid refresh token"""
        refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': str(refresh)},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_blacklisted_token_usage(self):
        """Test that blacklisted tokens cannot be used"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        # Authenticate and logout (blacklist token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = self.client.post(
            reverse('logout'),
            {'refresh': str(refresh)},
            format='json'
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Try to use the same refresh token again
        refresh_response = self.client.post(
            reverse('token_refresh'),
            {'refresh': str(refresh)},
            format='json'
        )

        # Should fail because token is blacklisted
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)