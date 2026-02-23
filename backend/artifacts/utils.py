"""
Security utilities for artifact processing.

Implements SSRF protection and file upload validation to prevent
security vulnerabilities identified in backend security audit.

Related Security Issues:
    - SSRF vulnerability (CVSS 9.1) - artifacts/validators.py:153, 210
    - File upload validation (CVSS 7.5) - artifacts/views.py:98

Security References:
    - docs/security/backend-security.md
    - OWASP SSRF Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
"""

import ipaddress
import socket
import os
import logging
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from typing import Optional

logger = logging.getLogger(__name__)


class SSRFProtection:
    """
    Server-Side Request Forgery (SSRF) protection utility.

    Validates URLs to prevent access to internal resources, cloud metadata,
    and private IP ranges.

    Usage:
        from artifacts.utils import SSRFProtection

        try:
            SSRFProtection.validate_url(user_provided_url)
            # URL is safe to fetch
            response = requests.get(user_provided_url)
        except ValueError as e:
            # URL is blocked
            logger.warning(f"Blocked SSRF attempt: {e}")

    Security Controls:
        - Blocks private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
        - Blocks localhost (127.0.0.0/8, ::1)
        - Blocks link-local addresses (169.254.0.0/16 - AWS metadata service)
        - Blocks IPv6 link-local (fe80::/10)
        - Only allows HTTP/HTTPS schemes
        - Resolves DNS to check final IP address

    Related:
        - Critical Security Issue #1: SSRF Vulnerability
        - docs/security/backend-security.md:49-183
    """

    # Private and reserved IP ranges that should never be accessed
    BLOCKED_CIDRS = [
        # IPv4 Private Ranges (RFC 1918)
        ipaddress.ip_network('10.0.0.0/8'),      # Class A private
        ipaddress.ip_network('172.16.0.0/12'),   # Class B private
        ipaddress.ip_network('192.168.0.0/16'),  # Class C private

        # IPv4 Localhost and Link-Local
        ipaddress.ip_network('127.0.0.0/8'),     # Localhost
        ipaddress.ip_network('169.254.0.0/16'),  # Link-local (AWS metadata: 169.254.169.254)
        ipaddress.ip_network('0.0.0.0/8'),       # Current network

        # IPv6 Special Ranges
        ipaddress.ip_network('::1/128'),         # IPv6 localhost
        ipaddress.ip_network('fe80::/10'),       # IPv6 link-local
        ipaddress.ip_network('fc00::/7'),        # IPv6 unique local
    ]

    ALLOWED_SCHEMES = ['http', 'https']

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validate URL is not pointing to internal resources.

        Args:
            url: User-provided URL to validate

        Returns:
            True if URL is safe

        Raises:
            ValueError: If URL is blocked for security reasons

        Security Checks:
            1. Parse URL and validate scheme
            2. Extract hostname
            3. Resolve hostname to IP address via DNS
            4. Check IP against blocked CIDR ranges
            5. Reject if IP is in any blocked range
        """
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

        # Validate scheme
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(
                f"Invalid URL scheme: {parsed.scheme}. "
                f"Only {', '.join(cls.ALLOWED_SCHEMES)} are allowed"
            )

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: no hostname found")

        # Resolve hostname to IP address
        try:
            # Use getaddrinfo to get all addresses (supports IPv4 and IPv6)
            addr_info = socket.getaddrinfo(hostname, None)

            # Check all resolved IP addresses
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_str = sockaddr[0]  # Extract IP from (ip, port) tuple

                try:
                    ip = ipaddress.ip_address(ip_str)
                except ValueError:
                    # Skip invalid IPs
                    continue

                # Check against blocked CIDRs
                for cidr in cls.BLOCKED_CIDRS:
                    if ip in cidr:
                        raise ValueError(
                            f"URL blocked: {hostname} resolves to {ip} which is in "
                            f"blocked IP range {cidr}. Access to internal/private "
                            f"resources is not allowed."
                        )

            return True

        except socket.gaierror as e:
            raise ValueError(f"Cannot resolve hostname: {hostname}. DNS error: {e}")
        except Exception as e:
            raise ValueError(f"Error validating URL: {e}")


class FileValidator:
    """
    File upload validator with MIME type checking via magic bytes.

    Validates uploaded files to prevent:
        - Malicious executables
        - Web shells disguised as documents
        - Storage exhaustion via compressed bombs
        - MIME type spoofing

    Usage:
        from artifacts.utils import FileValidator

        def upload_view(request):
            for uploaded_file in request.FILES.getlist('files'):
                try:
                    FileValidator.validate_file(uploaded_file)
                    # File is safe to process
                except ValidationError as e:
                    return Response({'error': str(e)}, status=400)

    Security Controls:
        - Whitelist of allowed MIME types
        - Magic byte validation (not just extension)
        - File size limits
        - Extension/MIME type consistency checks

    Related:
        - High Security Issue #1: File Upload Validation Missing
        - docs/security/backend-security.md:320-397
    """

    # Allowed MIME types and their corresponding file extensions
    ALLOWED_MIME_TYPES = {
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def validate_file(cls, uploaded_file) -> bool:
        """
        Validate uploaded file with MIME type and size checks.

        Args:
            uploaded_file: Django UploadedFile object

        Returns:
            True if file is valid

        Raises:
            ValidationError: If file fails validation

        Security Checks:
            1. Check file size
            2. Read magic bytes to determine true MIME type
            3. Validate MIME type against whitelist
            4. Validate extension matches MIME type
        """
        # Check file size
        if uploaded_file.size > cls.MAX_FILE_SIZE:
            raise ValidationError(
                f'File size exceeds maximum allowed size of '
                f'{cls.MAX_FILE_SIZE / 1024 / 1024:.0f}MB'
            )

        # Check if file is empty
        if uploaded_file.size == 0:
            raise ValidationError('File is empty')

        try:
            # Try to import python-magic
            import magic

            # Read first 2KB for magic byte detection
            uploaded_file.seek(0)
            file_header = uploaded_file.read(2048)
            uploaded_file.seek(0)  # Reset file pointer

            # Detect MIME type from magic bytes
            mime = magic.from_buffer(file_header, mime=True)

        except ImportError:
            # python-magic not installed - fall back to Django's content_type
            logger.warning(
                "python-magic not installed. Falling back to less secure "
                "content-type validation. Install with: uv add python-magic"
            )
            mime = getattr(uploaded_file, 'content_type', 'application/octet-stream')
        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            raise ValidationError(f'Could not determine file type: {e}')

        # Validate MIME type
        if mime not in cls.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f'File type not allowed: {mime}. '
                f'Allowed types: {", ".join(cls.ALLOWED_MIME_TYPES.keys())}'
            )

        # Validate extension matches MIME type
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_exts = cls.ALLOWED_MIME_TYPES[mime]

        if file_ext not in allowed_exts:
            raise ValidationError(
                f'File extension {file_ext} does not match detected file type {mime}. '
                f'Expected one of: {", ".join(allowed_exts)}'
            )

        return True
