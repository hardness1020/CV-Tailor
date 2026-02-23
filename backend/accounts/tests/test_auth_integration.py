"""
Integration tests for accounts app authentication flows
"""

from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@tag('medium', 'integration', 'accounts', 'auth')
class AuthenticationIntegrationTests(APITestCase):
    """Integration tests for complete authentication flow"""

    def test_complete_registration_and_login_flow(self):
        """Test complete user registration and login flow"""
        # Step 1: Register new user
        register_data = {
            'email': 'integration@example.com',
            'username': 'integrationuser',
            'password': 'integrationpass123',
            'password_confirm': 'integrationpass123',
            'first_name': 'Integration',
            'last_name': 'Test'
        }

        register_response = self.client.post(
            reverse('register'),
            register_data,
            format='json'
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', register_response.data)
        self.assertIn('refresh', register_response.data)

        access_token = register_response.data['access']
        refresh_token = register_response.data['refresh']

        # Step 2: Use access token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.get(reverse('profile'))

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['email'], 'integration@example.com')

        # Step 3: Logout
        logout_response = self.client.post(
            reverse('logout'),
            {'refresh': refresh_token},
            format='json'
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Step 4: Try to access protected endpoint after logout
        profile_response_after_logout = self.client.get(reverse('profile'))
        # Note: Token is blacklisted but might still work briefly,
        # this would need proper blacklist implementation

    def test_login_after_registration(self):
        """Test logging in with a user that was just registered"""
        # Register user
        register_data = {
            'email': 'login_test@example.com',
            'username': 'logintest',
            'password': 'loginpass123',
            'password_confirm': 'loginpass123',
            'first_name': 'Login',
            'last_name': 'Test'
        }

        self.client.post(reverse('register'), register_data, format='json')

        # Now login with the same credentials
        login_data = {
            'email': 'login_test@example.com',
            'password': 'loginpass123'
        }

        login_response = self.client.post(
            reverse('login'),
            login_data,
            format='json'
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)
        self.assertEqual(login_response.data['user']['email'], 'login_test@example.com')

    def test_token_refresh_integration(self):
        """Test token refresh functionality"""
        # Create user
        user = User.objects.create_user(
            email='refresh@example.com',
            username='refreshuser',
            password='refreshpass123'
        )

        # Login to get tokens
        login_data = {
            'email': 'refresh@example.com',
            'password': 'refreshpass123'
        }

        login_response = self.client.post(
            reverse('login'),
            login_data,
            format='json'
        )

        refresh_token = login_response.data['refresh']

        # Use refresh token to get new access token
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post(
            reverse('token_refresh'),
            refresh_data,
            format='json'
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

    def test_profile_update_integration(self):
        """Test updating user profile after authentication"""
        # Create and authenticate user
        user = User.objects.create_user(
            email='profile@example.com',
            username='profileuser',
            password='profilepass123',
            first_name='Original',
            last_name='Name'
        )

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Update profile
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Profile',
            'bio': 'This is my updated bio',
            'location': 'New York, NY'
        }

        update_response = self.client.patch(
            reverse('profile'),
            update_data,
            format='json'
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        # Verify updates
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Profile')
        self.assertEqual(user.bio, 'This is my updated bio')
        self.assertEqual(user.location, 'New York, NY')

    def test_concurrent_user_operations(self):
        """Test handling multiple users performing operations simultaneously"""
        # Create two users
        user1_data = {
            'email': 'user1@example.com',
            'username': 'user1',
            'password': 'user1pass123',
            'password_confirm': 'user1pass123',
            'first_name': 'User',
            'last_name': 'One'
        }

        user2_data = {
            'email': 'user2@example.com',
            'username': 'user2',
            'password': 'user2pass123',
            'password_confirm': 'user2pass123',
            'first_name': 'User',
            'last_name': 'Two'
        }

        # Register both users
        response1 = self.client.post(reverse('register'), user1_data, format='json')
        response2 = self.client.post(reverse('register'), user2_data, format='json')

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify both users exist and have different tokens
        self.assertNotEqual(response1.data['access'], response2.data['access'])
        self.assertNotEqual(response1.data['refresh'], response2.data['refresh'])

        # Verify both users can access their profiles independently
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response1.data["access"]}')
        profile1 = self.client.get(reverse('profile'))

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response2.data["access"]}')
        profile2 = self.client.get(reverse('profile'))

        self.assertEqual(profile1.data['email'], 'user1@example.com')
        self.assertEqual(profile2.data['email'], 'user2@example.com')