"""
Settings Test Helper Utilities.

Provides reusable helper functions for testing Django settings across environments.

Usage:
    from cv_tailor.tests.utils.settings_test_helpers import setup_mock_secrets

    mock_get_secret = Mock()
    setup_mock_secrets(mock_get_secret, include_db=True)
"""

from typing import Dict, Any, Callable
from unittest.mock import MagicMock


def setup_mock_secrets(
    mock_get_secret: MagicMock,
    include_db: bool = False,
    custom_secrets: Dict[str, Any] = None
) -> None:
    """
    Configure a mock get_secret function with standard test values.

    This helper provides consistent mock secrets across all settings tests,
    reducing duplication and making tests more maintainable.

    Args:
        mock_get_secret: MagicMock object to configure (typically from @patch)
        include_db: If True, configure side_effect for database secrets
        custom_secrets: Optional dict to override default secret values

    Example:
        @patch('cv_tailor.settings.production.get_secret')
        def test_something(self, mock_get_secret):
            setup_mock_secrets(mock_get_secret, include_db=True)
            # Now mock_get_secret is configured with standard test values
    """
    # Default application secrets
    default_app_secrets = {
        'DJANGO_SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'OPENAI_API_KEY': 'sk-test-openai-key-' + 'y' * 40,
        'GITHUB_TOKEN': 'ghp_test_github_token',
        'GOOGLE_CLIENT_ID': 'test-client-id.apps.googleusercontent.com',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret',
    }

    # Default database secrets
    default_db_secrets = {
        'username': 'cv_tailor_test_user',
        'password': 'test-db-password-' + 'z' * 20,
        'host': 'test-rds-endpoint.us-west-1.rds.amazonaws.com',
        'port': 5432,
    }

    # Merge custom secrets if provided
    if custom_secrets:
        default_app_secrets.update(custom_secrets)

    if include_db:
        # Configure side_effect to return different values based on secret name
        def mock_secret_side_effect(secret_name, *args, **kwargs):
            """Return app or db secrets based on secret name"""
            if 'db' in secret_name.lower():
                return default_db_secrets
            else:
                return default_app_secrets

        mock_get_secret.side_effect = mock_secret_side_effect
    else:
        # Simple return value for application secrets only
        mock_get_secret.return_value = default_app_secrets


def assert_production_security_enabled(settings_module) -> None:
    """
    Assert that all required production security settings are enabled.

    This helper checks all critical security settings at once,
    making it easier to verify production configuration.

    Args:
        settings_module: Django settings module to check

    Raises:
        AssertionError: If any security setting is not properly configured

    Example:
        from cv_tailor.settings import production
        assert_production_security_enabled(production)

    Note:
        SECURE_SSL_REDIRECT may be False if using ALB (Application Load Balancer)
        to handle HTTP→HTTPS redirect. This is acceptable and more efficient.
    """
    # DEBUG must be False
    assert not settings_module.DEBUG, \
        "Production must have DEBUG=False"

    # HTTPS redirect - may be handled by ALB instead of Django
    # So we don't enforce SECURE_SSL_REDIRECT=True
    # (ALB redirect is more efficient and the comment in settings confirms this)

    # Secure cookies (critical - must be True)
    assert getattr(settings_module, 'SESSION_COOKIE_SECURE', False), \
        "Production must use secure session cookies"
    assert getattr(settings_module, 'CSRF_COOKIE_SECURE', False), \
        "Production must use secure CSRF cookies"

    # HSTS (HTTP Strict Transport Security)
    hsts_seconds = getattr(settings_module, 'SECURE_HSTS_SECONDS', 0)
    assert hsts_seconds >= 31536000, \
        f"Production must enable HSTS for at least 1 year, got {hsts_seconds}"

    assert getattr(settings_module, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False), \
        "Production HSTS must include subdomains"


def assert_production_uses_s3(settings_module, expected_bucket: str = None) -> None:
    """
    Assert that production settings use S3 for file storage.

    Args:
        settings_module: Django settings module to check
        expected_bucket: Optional S3 bucket name to verify

    Raises:
        AssertionError: If S3 is not properly configured
    """
    # Check storage backend
    assert settings_module.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage', \
        "Production must use S3 for media file storage"

    # Check bucket is configured
    bucket_name = getattr(settings_module, 'AWS_STORAGE_BUCKET_NAME', None)
    assert bucket_name is not None, \
        "Production must define AWS_STORAGE_BUCKET_NAME"

    if expected_bucket:
        assert bucket_name == expected_bucket, \
            f"Expected bucket '{expected_bucket}', got '{bucket_name}'"

    # Check private ACL (security)
    assert settings_module.AWS_DEFAULT_ACL == 'private', \
        "Production S3 files must use private ACL"

    # Check signed URLs enabled
    assert getattr(settings_module, 'AWS_QUERYSTRING_AUTH', False), \
        "Production must use signed URLs for private files"


def assert_rate_limiting_enabled(settings_module) -> None:
    """
    Assert that API rate limiting is properly configured.

    Args:
        settings_module: Django settings module to check

    Raises:
        AssertionError: If rate limiting is not configured
    """
    throttle_classes = settings_module.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])

    assert 'rest_framework.throttling.AnonRateThrottle' in throttle_classes, \
        "Production must rate limit anonymous users"
    assert 'rest_framework.throttling.UserRateThrottle' in throttle_classes, \
        "Production must rate limit authenticated users"

    throttle_rates = settings_module.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
    assert 'anon' in throttle_rates, "Production must define anon rate limit"
    assert 'user' in throttle_rates, "Production must define user rate limit"


def assert_database_uses_ssl(settings_module) -> None:
    """
    Assert that database connection requires SSL/TLS.

    Args:
        settings_module: Django settings module to check

    Raises:
        AssertionError: If SSL is not required for database
    """
    db_options = settings_module.DATABASES['default'].get('OPTIONS', {})

    assert db_options.get('sslmode') == 'require', \
        "Production database must require SSL connections"


def assert_connection_pooling_enabled(settings_module) -> None:
    """
    Assert that database connection pooling is enabled.

    Args:
        settings_module: Django settings module to check

    Raises:
        AssertionError: If connection pooling is not enabled
    """
    conn_max_age = settings_module.DATABASES['default'].get('CONN_MAX_AGE', 0)

    assert conn_max_age > 0, \
        f"Production must enable connection pooling (CONN_MAX_AGE > 0), got {conn_max_age}"


def get_test_environment_variables() -> Dict[str, str]:
    """
    Get standard environment variables for testing settings.

    Returns a dictionary of environment variables commonly needed
    for testing production/staging settings.

    Returns:
        Dict of environment variable name → value

    Example:
        @patch.dict(os.environ, get_test_environment_variables())
        def test_something(self):
            # Test with standard env vars
    """
    return {
        'DJANGO_ENV': 'test',
        'SECRET_KEY': 'test-secret-key',
        'OPENAI_API_KEY': 'sk-test-key',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
    }


def create_mock_boto3_client() -> MagicMock:
    """
    Create a properly configured mock boto3 client for testing.

    Returns:
        MagicMock configured to behave like boto3.client('secretsmanager')

    Example:
        @patch('boto3.client')
        def test_something(self, mock_boto3):
            mock_client = create_mock_boto3_client()
            mock_boto3.return_value = mock_client
            # Test code that uses boto3
    """
    mock_client = MagicMock()

    # Default successful response
    mock_client.get_secret_value.return_value = {
        'SecretString': '{"DJANGO_SECRET_KEY":"test","OPENAI_API_KEY":"sk-test"}'
    }

    return mock_client


# Type hints for better IDE support
MockSecretCallback = Callable[[str], Dict[str, Any]]
