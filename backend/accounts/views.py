import logging
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from allauth.socialaccount.models import SocialAccount, SocialApp
from .models import User
from .serializers import UserRegistrationSerializer, UserProfileSerializer, UserUpdateSerializer
from .utils import anonymize_email, create_audit_context

logger = logging.getLogger('google_auth')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """User registration endpoint."""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """User login endpoint."""
    email = request.data.get('email')
    password = request.data.get('password')

    if email and password:
        user = authenticate(username=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view and update."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    # No lookup_field needed - uses custom get_object() to return current user
    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserProfileSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """User logout endpoint - blacklist refresh token."""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change user password endpoint."""
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    new_password_confirm = request.data.get('new_password_confirm')

    if not all([current_password, new_password, new_password_confirm]):
        return Response({'error': 'All password fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    if new_password != new_password_confirm:
        return Response({'error': 'New passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new_password, user)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """Password reset request endpoint."""
    email = request.data.get('email')

    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    # For security, always return success even if email doesn't exist
    # In a real implementation, you would send an email here
    return Response({'message': 'If this email exists, a password reset link has been sent'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """
    Authenticate user with Google OAuth ID token.

    Expects a Google ID token and returns JWT tokens for API access.
    Creates new user if none exists, or links to existing user by email.
    """
    credential = request.data.get('credential')

    if not credential:
        logger.warning('Google auth attempted without credential')
        return Response({
            'error': 'google_auth_failed',
            'message': 'Google credential is required',
            'recoverable': True
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify the Google ID token
        google_user_info = verify_google_id_token(credential)

        # Get or create user from Google info
        user, created = get_or_create_user_from_google(google_user_info)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Log successful authentication (SECURITY: anonymized email)
        logger.info(
            f'Google authentication successful for user: {anonymize_email(user.email)}',
            extra=create_audit_context(
                user_email=user.email,
                user_id=user.id,
                action='google_auth_success',
                user_created=created
            )
        )

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data,
            'created': created
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.error(f'Invalid Google token: {str(e)}')
        return Response({
            'error': 'google_auth_failed',
            'message': 'Invalid Google credential',
            'recoverable': True
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f'Unexpected error in Google auth: {str(e)}', exc_info=True)
        return Response({
            'error': 'internal_error',
            'message': 'Authentication service temporarily unavailable',
            'recoverable': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def google_link(request):
    """
    Link Google account to existing authenticated user.

    Allows users to link their Google account to their existing account
    for future Google sign-in access.
    """
    credential = request.data.get('credential')

    if not credential:
        return Response({
            'error': 'google_link_failed',
            'message': 'Google credential is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify the Google ID token
        google_user_info = verify_google_id_token(credential)
        google_email = google_user_info['email']
        google_sub = google_user_info['sub']

        # Check if this Google account is already linked to another user
        existing_social_account = SocialAccount.objects.filter(
            provider='google',
            uid=google_sub
        ).first()

        if existing_social_account:
            if existing_social_account.user != request.user:
                return Response({
                    'error': 'account_already_linked',
                    'message': 'This Google account is already linked to another user'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'message': 'Google account is already linked to your account',
                    'linked_email': google_email
                }, status=status.HTTP_200_OK)

        # Create social account link
        social_app = get_or_create_google_social_app()
        social_account = SocialAccount.objects.create(
            user=request.user,
            provider='google',
            uid=google_sub,
            extra_data=google_user_info
        )

        # SECURITY: Anonymized logging to protect PII
        logger.info(
            f'Linked Google account to user: {anonymize_email(request.user.email)}',
            extra=create_audit_context(
                user_email=request.user.email,
                user_id=request.user.id,
                action='google_account_linked',
                google_email_hash=anonymize_email(google_email)
            )
        )

        return Response({
            'message': 'Google account linked successfully',
            'linked_email': google_email
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.error(f'Invalid Google token in link: {str(e)}')
        return Response({
            'error': 'google_link_failed',
            'message': 'Invalid Google credential'
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f'Unexpected error in Google link: {str(e)}', exc_info=True)
        return Response({
            'error': 'internal_error',
            'message': 'Link service temporarily unavailable'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def google_unlink(request):
    """
    Unlink Google account from authenticated user.

    Removes the Google account link, requiring the user to use
    email/password authentication in the future.
    """
    try:
        social_account = SocialAccount.objects.get(
            user=request.user,
            provider='google'
        )

        google_email = social_account.extra_data.get('email', 'unknown')
        social_account.delete()

        logger.info(
            f'Unlinked Google account from user: {request.user.email}',
            extra={
                'user_id': request.user.id,
                'google_email': google_email,
                'action': 'google_account_unlinked'
            }
        )

        return Response({
            'message': 'Google account unlinked successfully'
        }, status=status.HTTP_200_OK)

    except SocialAccount.DoesNotExist:
        return Response({
            'error': 'no_google_account',
            'message': 'No Google account linked to this user'
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f'Unexpected error in Google unlink: {str(e)}', exc_info=True)
        return Response({
            'error': 'internal_error',
            'message': 'Unlink service temporarily unavailable'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def verify_google_id_token(token):
    """
    Verify Google ID token and return user information.

    Args:
        token (str): Google ID token to verify

    Returns:
        dict: Verified token payload containing user information

    Raises:
        ValueError: If token is invalid or verification fails
    """
    try:
        # Verify the token against Google's public keys
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        # Verify the issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer')

        return idinfo

    except ValueError as e:
        raise ValueError(f'Invalid Google ID token: {str(e)}')


def get_or_create_user_from_google(google_user_info):
    """
    Get existing user or create new user from Google user information.

    Args:
        google_user_info (dict): Verified Google user information

    Returns:
        tuple: (User instance, created boolean)
    """
    email = google_user_info['email']
    google_sub = google_user_info['sub']

    # First, try to find user by social account
    try:
        social_account = SocialAccount.objects.get(
            provider='google',
            uid=google_sub
        )
        return social_account.user, False

    except SocialAccount.DoesNotExist:
        pass

    # Try to find existing user by email
    try:
        existing_user = User.objects.get(email=email)

        # Link this Google account to the existing user
        social_app = get_or_create_google_social_app()
        SocialAccount.objects.create(
            user=existing_user,
            provider='google',
            uid=google_sub,
            extra_data=google_user_info
        )

        return existing_user, False

    except User.DoesNotExist:
        pass

    # Create new user
    user = User.objects.create_user(
        username=email,  # Use email as username
        email=email,
        first_name=google_user_info.get('given_name', ''),
        last_name=google_user_info.get('family_name', ''),
    )

    # Create social account
    social_app = get_or_create_google_social_app()
    SocialAccount.objects.create(
        user=user,
        provider='google',
        uid=google_sub,
        extra_data=google_user_info
    )

    return user, True


def get_or_create_google_social_app():
    """
    Get or create the Google Social App configuration.

    Returns:
        SocialApp: Google social app instance
    """
    social_app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': settings.GOOGLE_CLIENT_ID,
            'secret': settings.GOOGLE_CLIENT_SECRET,
        }
    )

    return social_app