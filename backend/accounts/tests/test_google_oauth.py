import json
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings, tag
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from allauth.socialaccount.models import SocialAccount, SocialApp
from accounts.views import verify_google_id_token, get_or_create_user_from_google, get_or_create_google_social_app

User = get_user_model()


@tag('medium', 'integration', 'accounts', 'oauth')
class GoogleAuthTestCase(TestCase):
    """Test cases for Google OAuth authentication."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Mock Google user info
        self.google_user_info = {
            'sub': '123456789',
            'email': 'test@example.com',
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'picture': 'https://example.com/photo.jpg',
            'iss': 'https://accounts.google.com'
        }

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

        # Create Google social app
        self.social_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id',
            secret='test-client-secret'
        )

    @patch('accounts.views.verify_google_id_token')
    @patch('accounts.views.get_or_create_user_from_google')
    def test_google_auth_success_existing_user(self, mock_get_user, mock_verify):
        """Test successful Google authentication with existing user."""
        # Setup mocks
        mock_verify.return_value = self.google_user_info
        mock_get_user.return_value = (self.test_user, False)

        # Make request
        response = self.client.post(reverse('google_auth'), {
            'credential': 'fake-jwt-token'
        })

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIn('user', data)
        self.assertEqual(data['created'], False)
        self.assertEqual(data['user']['email'], self.test_user.email)

        # Verify mocks were called
        mock_verify.assert_called_once_with('fake-jwt-token')
        mock_get_user.assert_called_once_with(self.google_user_info)

    @patch('accounts.views.verify_google_id_token')
    @patch('accounts.views.get_or_create_user_from_google')
    def test_google_auth_success_new_user(self, mock_get_user, mock_verify):
        """Test successful Google authentication with new user creation."""
        # Create new user for this test
        new_user = User.objects.create_user(
            username='newuser@gmail.com',
            email='newuser@gmail.com',
            first_name='New',
            last_name='User'
        )

        # Setup mocks
        mock_verify.return_value = self.google_user_info
        mock_get_user.return_value = (new_user, True)

        # Make request
        response = self.client.post(reverse('google_auth'), {
            'credential': 'fake-jwt-token'
        })

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['created'], True)
        self.assertEqual(data['user']['email'], new_user.email)

    def test_google_auth_missing_credential(self):
        """Test Google auth fails when credential is missing."""
        response = self.client.post(reverse('google_auth'), {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertEqual(data['error'], 'google_auth_failed')
        self.assertEqual(data['message'], 'Google credential is required')
        self.assertTrue(data['recoverable'])

    @patch('accounts.views.verify_google_id_token')
    def test_google_auth_invalid_token(self, mock_verify):
        """Test Google auth fails with invalid token."""
        mock_verify.side_effect = ValueError('Invalid Google ID token: Token expired')

        # Assert that invalid token error is logged
        with self.assertLogs('google_auth', level='ERROR') as cm:
            response = self.client.post(reverse('google_auth'), {
                'credential': 'invalid-jwt-token'
            })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertEqual(data['error'], 'google_auth_failed')
        self.assertEqual(data['message'], 'Invalid Google credential')
        self.assertTrue(data['recoverable'])

        # Verify expected error message was logged
        self.assertIn('Invalid Google token', cm.output[0])
        self.assertIn('Token expired', cm.output[0])

    @patch('accounts.views.verify_google_id_token')
    @patch('accounts.views.get_or_create_user_from_google')
    def test_google_auth_unexpected_error(self, mock_get_user, mock_verify):
        """Test Google auth handles unexpected errors."""
        mock_verify.return_value = self.google_user_info
        mock_get_user.side_effect = Exception('Database error')

        # Assert that unexpected error is logged by both application and Django loggers
        with self.assertLogs('google_auth', level='ERROR') as app_cm, \
             self.assertLogs('django.request', level='ERROR') as django_cm:
            response = self.client.post(reverse('google_auth'), {
                'credential': 'fake-jwt-token'
            })

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()

        self.assertEqual(data['error'], 'internal_error')
        self.assertEqual(data['message'], 'Authentication service temporarily unavailable')
        self.assertFalse(data['recoverable'])

        # Verify application logger captured the error
        self.assertIn('Unexpected error in Google auth', app_cm.output[0])
        self.assertIn('Database error', app_cm.output[0])

        # Verify Django request logger captured the 500 error
        self.assertIn('Internal Server Error', django_cm.output[0])


@tag('medium', 'integration', 'accounts', 'oauth')
class GoogleLinkTestCase(TestCase):
    """Test cases for Google account linking."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

        # Authenticate user
        self.client.force_authenticate(user=self.test_user)

        # Mock Google user info
        self.google_user_info = {
            'sub': '123456789',
            'email': 'test@gmail.com',
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'iss': 'https://accounts.google.com'
        }

    @patch('accounts.views.verify_google_id_token')
    @patch('accounts.views.get_or_create_google_social_app')
    def test_google_link_success(self, mock_social_app, mock_verify):
        """Test successful Google account linking."""
        mock_verify.return_value = self.google_user_info
        mock_social_app.return_value = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id',
            secret='test-client-secret'
        )

        response = self.client.post(reverse('google_link'), {
            'credential': 'fake-jwt-token'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['message'], 'Google account linked successfully')
        self.assertEqual(data['linkedEmail'], 'test@gmail.com')

        # Verify social account was created
        social_account = SocialAccount.objects.get(
            user=self.test_user,
            provider='google',
            uid='123456789'
        )
        self.assertEqual(social_account.extra_data, self.google_user_info)

    def test_google_link_unauthenticated(self):
        """Test Google link fails for unauthenticated users."""
        self.client.force_authenticate(user=None)

        response = self.client.post(reverse('google_link'), {
            'credential': 'fake-jwt-token'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_google_link_missing_credential(self):
        """Test Google link fails when credential is missing."""
        response = self.client.post(reverse('google_link'), {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertEqual(data['error'], 'google_link_failed')
        self.assertEqual(data['message'], 'Google credential is required')

    @patch('accounts.views.verify_google_id_token')
    def test_google_link_already_linked_same_user(self, mock_verify):
        """Test linking Google account that's already linked to same user."""
        mock_verify.return_value = self.google_user_info

        # Create existing social account
        SocialAccount.objects.create(
            user=self.test_user,
            provider='google',
            uid='123456789',
            extra_data=self.google_user_info
        )

        response = self.client.post(reverse('google_link'), {
            'credential': 'fake-jwt-token'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['message'], 'Google account is already linked to your account')
        self.assertEqual(data['linkedEmail'], 'test@gmail.com')

    @patch('accounts.views.verify_google_id_token')
    def test_google_link_already_linked_different_user(self, mock_verify):
        """Test linking Google account that's already linked to different user."""
        mock_verify.return_value = self.google_user_info

        # Create another user with the Google account
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com'
        )

        SocialAccount.objects.create(
            user=other_user,
            provider='google',
            uid='123456789',
            extra_data=self.google_user_info
        )

        response = self.client.post(reverse('google_link'), {
            'credential': 'fake-jwt-token'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertEqual(data['error'], 'account_already_linked')
        self.assertEqual(data['message'], 'This Google account is already linked to another user')


@tag('medium', 'integration', 'accounts', 'oauth')
class GoogleUnlinkTestCase(TestCase):
    """Test cases for Google account unlinking."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

        # Authenticate user
        self.client.force_authenticate(user=self.test_user)

        # Create linked social account
        self.social_account = SocialAccount.objects.create(
            user=self.test_user,
            provider='google',
            uid='123456789',
            extra_data={
                'email': 'test@gmail.com',
                'name': 'Test User'
            }
        )

    def test_google_unlink_success(self):
        """Test successful Google account unlinking."""
        response = self.client.post(reverse('google_unlink'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['message'], 'Google account unlinked successfully')

        # Verify social account was deleted
        with self.assertRaises(SocialAccount.DoesNotExist):
            SocialAccount.objects.get(pk=self.social_account.pk)

    def test_google_unlink_no_account(self):
        """Test unlinking when no Google account is linked."""
        # Delete the social account
        self.social_account.delete()

        response = self.client.post(reverse('google_unlink'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertEqual(data['error'], 'no_google_account')
        self.assertEqual(data['message'], 'No Google account linked to this user')

    def test_google_unlink_unauthenticated(self):
        """Test unlinking fails for unauthenticated users."""
        self.client.force_authenticate(user=None)

        response = self.client.post(reverse('google_unlink'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@tag('medium', 'integration', 'accounts', 'oauth')
class VerifyGoogleIdTokenTestCase(TestCase):
    """Test cases for Google ID token verification."""

    @patch('google.oauth2.id_token.verify_oauth2_token')
    @override_settings(GOOGLE_CLIENT_ID='test-client-id')
    def test_verify_valid_token(self, mock_verify):
        """Test verification of valid Google ID token."""
        mock_token_info = {
            'iss': 'https://accounts.google.com',
            'sub': '123456789',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_verify.return_value = mock_token_info

        result = verify_google_id_token('valid-token')

        self.assertEqual(result, mock_token_info)
        mock_verify.assert_called_once()

    @patch('google.oauth2.id_token.verify_oauth2_token')
    @override_settings(GOOGLE_CLIENT_ID='test-client-id')
    def test_verify_invalid_issuer(self, mock_verify):
        """Test verification fails with invalid issuer."""
        mock_verify.return_value = {
            'iss': 'https://evil.com',
            'sub': '123456789',
            'email': 'test@example.com'
        }

        with self.assertRaises(ValueError) as context:
            verify_google_id_token('token-with-bad-issuer')

        self.assertIn('Invalid issuer', str(context.exception))

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_token_validation_error(self, mock_verify):
        """Test verification fails with token validation error."""
        mock_verify.side_effect = ValueError('Token expired')

        with self.assertRaises(ValueError) as context:
            verify_google_id_token('expired-token')

        self.assertIn('Invalid Google ID token', str(context.exception))


@tag('medium', 'integration', 'accounts', 'oauth')
class GetOrCreateUserFromGoogleTestCase(TestCase):
    """Test cases for user creation from Google info."""

    def setUp(self):
        """Set up test data."""
        self.google_user_info = {
            'sub': '123456789',
            'email': 'newuser@gmail.com',
            'given_name': 'New',
            'family_name': 'User',
            'name': 'New User'
        }

        # Create social app
        self.social_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id',
            secret='test-client-secret'
        )

    @patch('accounts.views.get_or_create_google_social_app')
    def test_create_new_user(self, mock_social_app):
        """Test creating a new user from Google info."""
        mock_social_app.return_value = self.social_app

        user, created = get_or_create_user_from_google(self.google_user_info)

        self.assertTrue(created)
        self.assertEqual(user.email, 'newuser@gmail.com')
        self.assertEqual(user.username, 'newuser@gmail.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')

        # Verify social account was created
        social_account = SocialAccount.objects.get(
            user=user,
            provider='google',
            uid='123456789'
        )
        self.assertEqual(social_account.extra_data, self.google_user_info)

    @patch('accounts.views.get_or_create_google_social_app')
    def test_get_existing_user_by_social_account(self, mock_social_app):
        """Test getting existing user by social account."""
        mock_social_app.return_value = self.social_app

        # Create existing user with social account
        existing_user = User.objects.create_user(
            username='existing@gmail.com',
            email='existing@gmail.com'
        )

        SocialAccount.objects.create(
            user=existing_user,
            provider='google',
            uid='123456789',
            extra_data=self.google_user_info
        )

        # Update google_user_info to match existing social account
        google_info = self.google_user_info.copy()
        google_info['email'] = 'existing@gmail.com'

        user, created = get_or_create_user_from_google(google_info)

        self.assertFalse(created)
        self.assertEqual(user, existing_user)

    @patch('accounts.views.get_or_create_google_social_app')
    def test_link_to_existing_user_by_email(self, mock_social_app):
        """Test linking Google account to existing user by email."""
        mock_social_app.return_value = self.social_app

        # Create existing user without social account
        existing_user = User.objects.create_user(
            username='existing',
            email='newuser@gmail.com',  # Same email as in google_user_info
            first_name='Existing',
            last_name='User'
        )

        user, created = get_or_create_user_from_google(self.google_user_info)

        self.assertFalse(created)
        self.assertEqual(user, existing_user)

        # Verify social account was created and linked
        social_account = SocialAccount.objects.get(
            user=existing_user,
            provider='google',
            uid='123456789'
        )
        self.assertEqual(social_account.extra_data, self.google_user_info)


@tag('medium', 'integration', 'accounts', 'oauth')
class GetOrCreateGoogleSocialAppTestCase(TestCase):
    """Test cases for Google social app creation."""

    @override_settings(
        GOOGLE_CLIENT_ID='test-client-id',
        GOOGLE_CLIENT_SECRET='test-client-secret'
    )
    def test_create_google_social_app(self):
        """Test creating Google social app."""
        social_app = get_or_create_google_social_app()

        self.assertEqual(social_app.provider, 'google')
        self.assertEqual(social_app.name, 'Google')
        self.assertEqual(social_app.client_id, 'test-client-id')
        self.assertEqual(social_app.secret, 'test-client-secret')

    @override_settings(
        GOOGLE_CLIENT_ID='test-client-id',
        GOOGLE_CLIENT_SECRET='test-client-secret'
    )
    def test_get_existing_google_social_app(self):
        """Test getting existing Google social app."""
        # Create existing app
        existing_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='existing-client-id',
            secret='existing-client-secret'
        )

        social_app = get_or_create_google_social_app()

        self.assertEqual(social_app, existing_app)
        self.assertEqual(social_app.client_id, 'existing-client-id')


@tag('medium', 'integration', 'accounts', 'oauth')
class GoogleAuthIntegrationTestCase(TestCase):
    """Integration test cases for complete Google auth flow."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    @patch('accounts.views.verify_google_id_token')
    def test_complete_new_user_flow(self, mock_verify):
        """Test complete flow for new user registration via Google."""
        # Mock Google token verification
        google_user_info = {
            'sub': '987654321',
            'email': 'integration@gmail.com',
            'given_name': 'Integration',
            'family_name': 'Test',
            'name': 'Integration Test',
            'iss': 'https://accounts.google.com'
        }
        mock_verify.return_value = google_user_info

        # Make Google auth request
        response = self.client.post(reverse('google_auth'), {
            'credential': 'fake-jwt-token'
        })

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['created'])
        self.assertEqual(data['user']['email'], 'integration@gmail.com')
        self.assertEqual(data['user']['firstName'], 'Integration')
        self.assertEqual(data['user']['lastName'], 'Test')

        # Verify user was created in database
        user = User.objects.get(email='integration@gmail.com')
        self.assertEqual(user.username, 'integration@gmail.com')

        # Verify social account was created
        social_account = SocialAccount.objects.get(
            user=user,
            provider='google',
            uid='987654321'
        )
        self.assertEqual(social_account.extra_data, google_user_info)

    @patch('accounts.views.verify_google_id_token')
    def test_complete_existing_user_flow(self, mock_verify):
        """Test complete flow for existing user login via Google."""
        # Create existing user
        existing_user = User.objects.create_user(
            username='existing@gmail.com',
            email='existing@gmail.com',
            first_name='Existing',
            last_name='User'
        )

        # Mock Google token verification
        google_user_info = {
            'sub': '111222333',
            'email': 'existing@gmail.com',
            'given_name': 'Existing',
            'family_name': 'User',
            'iss': 'https://accounts.google.com'
        }
        mock_verify.return_value = google_user_info

        # Make Google auth request
        response = self.client.post(reverse('google_auth'), {
            'credential': 'fake-jwt-token'
        })

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertFalse(data['created'])
        self.assertEqual(data['user']['id'], existing_user.id)
        self.assertEqual(data['user']['email'], 'existing@gmail.com')

        # Verify social account was linked
        social_account = SocialAccount.objects.get(
            user=existing_user,
            provider='google',
            uid='111222333'
        )
        self.assertEqual(social_account.extra_data, google_user_info)