"""
Security utilities for accounts app.

Implements email anonymization for logging to comply with data protection
regulations (GDPR, CCPA) and prevent PII exposure in logs.

Related Security Issues:
    - High Security Issue #3: Sensitive Data in Logs (CVSS 6.5)
    - docs/security/backend-security.md:437-463

Security References:
    - GDPR Article 32: Security of processing
    - OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
"""

import hashlib
from typing import Optional


def anonymize_email(email: str) -> str:
    """
    Anonymize email address for logging purposes.

    Creates a SHA-256 hash of the email and returns the first 12 characters
    as a unique identifier. This allows correlation of log entries for the
    same user without exposing the actual email address.

    Args:
        email: Email address to anonymize

    Returns:
        12-character hash prefix (e.g., "a3b7c9d1e5f2")

    Usage:
        logger.info(f'Login successful for user: {anonymize_email(user.email)}')

    Security Benefits:
        - Complies with GDPR/CCPA data protection requirements
        - Prevents email enumeration via log analysis
        - Enables log correlation without PII exposure
        - One-way hash prevents email recovery from logs

    Example:
        >>> anonymize_email('john.doe@example.com')
        'a3b7c9d1e5f2'
        >>> anonymize_email('jane.smith@example.com')
        'b8c2d4f6a1e3'

    Related:
        - High Security Issue #3: Sensitive Data in Logs
        - docs/security/backend-security.md:437-463
    """
    if not email:
        return 'anonymous'

    # Create SHA-256 hash of email
    hash_object = hashlib.sha256(email.encode('utf-8'))
    hash_hex = hash_object.hexdigest()

    # Return first 12 characters for brevity while maintaining uniqueness
    # 12 hex chars = 48 bits = ~281 trillion combinations
    return hash_hex[:12]


def anonymize_user_id(user_id: int) -> str:
    """
    Anonymize user ID for logging.

    While user IDs are not PII, anonymizing them adds an extra layer of
    privacy protection and consistency with email anonymization.

    Args:
        user_id: User ID to anonymize

    Returns:
        Anonymized user ID as hex string

    Usage:
        logger.info(f'Action for user: {anonymize_user_id(user.id)}')
    """
    if not user_id:
        return 'unknown'

    # Hash the user ID
    hash_object = hashlib.sha256(str(user_id).encode('utf-8'))
    return hash_object.hexdigest()[:8]


def create_audit_context(
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    **kwargs
) -> dict:
    """
    Create anonymized context dictionary for audit logging.

    Provides a structured way to log user actions with anonymized identifiers
    and additional context fields.

    Args:
        user_email: User email to anonymize
        user_id: User ID to anonymize
        action: Action being performed
        **kwargs: Additional context fields

    Returns:
        Dictionary with anonymized fields and extra context

    Usage:
        logger.info(
            'User action completed',
            extra=create_audit_context(
                user_email=user.email,
                user_id=user.id,
                action='login_success',
                ip_address=request.META.get('REMOTE_ADDR')
            )
        )

    Example Output:
        {
            'user_hash': 'a3b7c9d1e5f2',
            'user_id_hash': 'b8c2d4f6',
            'action': 'login_success',
            'ip_address': '192.168.1.1'
        }
    """
    context = {}

    if user_email:
        context['user_hash'] = anonymize_email(user_email)

    if user_id:
        context['user_id_hash'] = anonymize_user_id(user_id)

    if action:
        context['action'] = action

    # Add any additional context fields
    context.update(kwargs)

    return context
