import logging
from typing import Any, Dict

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth import get_user_model
from django.http import HttpRequest

User = get_user_model()
logger = logging.getLogger('google_auth')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for handling Google OAuth integration."""

    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        """
        Handle user account linking and duplicate prevention before social login.

        This method is called before the social account is linked to a user.
        It handles linking existing users by email and prevents duplicate accounts.
        """
        user = sociallogin.user
        if user.id:
            # User already exists, no action needed
            return

        try:
            # Check if a user with this email already exists
            existing_user = User.objects.get(email=user.email)

            # Link the social account to the existing user
            sociallogin.connect(request, existing_user)

            logger.info(
                f'Linked Google account to existing user: {existing_user.email}',
                extra={
                    'user_id': existing_user.id,
                    'google_email': user.email,
                    'action': 'account_linked'
                }
            )

        except User.DoesNotExist:
            # No existing user found, will create new user
            logger.info(
                f'No existing user found for email: {user.email}, will create new user',
                extra={
                    'google_email': user.email,
                    'action': 'new_user_creation'
                }
            )

    def save_user(self, request: HttpRequest, sociallogin: SocialLogin, form=None) -> User:
        """
        Create and save a new user from social login data.

        This method is called when creating a new user from social login.
        It populates user fields with data from the Google account.
        """
        user = super().save_user(request, sociallogin, form)

        # Get additional data from Google account
        extra_data = sociallogin.account.extra_data

        self._populate_user_from_google_data(user, extra_data)

        logger.info(
            f'Created new user from Google account: {user.email}',
            extra={
                'user_id': user.id,
                'google_email': user.email,
                'action': 'user_created'
            }
        )

        return user

    def _populate_user_from_google_data(self, user: User, extra_data: Dict[str, Any]) -> None:
        """
        Populate user fields with data from Google account.

        Args:
            user: The user instance to populate
            extra_data: Additional data from Google OAuth response
        """
        updated_fields = []

        # Handle name fields
        if 'given_name' in extra_data and not user.first_name:
            user.first_name = extra_data['given_name']
            updated_fields.append('first_name')

        if 'family_name' in extra_data and not user.last_name:
            user.last_name = extra_data['family_name']
            updated_fields.append('last_name')

        # Handle full name if given_name/family_name not available
        if 'name' in extra_data and not user.first_name and not user.last_name:
            names = extra_data['name'].split(' ', 1)
            user.first_name = names[0]
            user.last_name = names[1] if len(names) > 1 else ''
            updated_fields.extend(['first_name', 'last_name'])

        # Handle profile picture URL
        if 'picture' in extra_data:
            # Note: In a production environment, you might want to download
            # and store the profile picture locally rather than just storing the URL
            # For now, we'll store the URL in a custom field if it exists
            if hasattr(user, 'profile_image_url'):
                user.profile_image_url = extra_data['picture']
                updated_fields.append('profile_image_url')

        # Handle locale/language preference
        if 'locale' in extra_data:
            # Could be used to set user's preferred language
            pass

        # Save the user if any fields were updated
        if updated_fields:
            user.save(update_fields=updated_fields)

            logger.info(
                f'Updated user fields from Google data: {", ".join(updated_fields)}',
                extra={
                    'user_id': user.id,
                    'updated_fields': updated_fields,
                    'action': 'user_profile_updated'
                }
            )

    def is_auto_signup_allowed(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        """
        Determine if automatic signup is allowed for this social login.

        Returns True to allow automatic user creation from Google accounts.
        This can be customized based on business rules (e.g., domain restrictions).
        """
        # Allow auto-signup for all Google accounts
        # In production, you might want to add domain restrictions or other checks
        return True

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount) -> str:
        """
        Return the URL to redirect to after successfully connecting a social account.

        This is called after linking a social account to an existing user.
        """
        # Redirect to profile settings page after successful linking
        return '/profile/settings/'

    def authentication_error(
        self,
        request: HttpRequest,
        provider_id: str,
        error: Exception = None,
        exception: Exception = None,
        extra_context: Dict = None
    ) -> None:
        """
        Handle authentication errors from social providers.

        Log errors for monitoring and debugging purposes.
        """
        logger.error(
            f'Google authentication error: {str(error or exception)}',
            extra={
                'provider_id': provider_id,
                'error': str(error or exception),
                'action': 'authentication_error',
                'extra_context': extra_context or {}
            }
        )

        super().authentication_error(request, provider_id, error, exception, extra_context)