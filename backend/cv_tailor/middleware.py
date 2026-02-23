"""
Custom middleware for cv_tailor project.

Implements health check bypass for ALB to avoid ALLOWED_HOSTS wildcard.

Security:
    - Allows ALB health checks without compromising Host header security
    - Related to Critical Security Issue #2: Wildcard in ALLOWED_HOSTS
    - docs/security/backend-security.md:186-266
"""

from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Bypass ALLOWED_HOSTS validation for ALB health checks.

    AWS Application Load Balancer performs health checks from various
    internal IPs, making it difficult to whitelist all possible Host headers.
    This middleware allows health check requests to bypass ALLOWED_HOSTS
    validation while maintaining security for all other requests.

    Security Considerations:
        - Only allows /health/ endpoint bypass
        - Verifies User-Agent is AWS ELB health checker
        - All other requests go through normal ALLOWED_HOSTS validation
        - Prevents Host header injection attacks

    Usage:
        Add to MIDDLEWARE in settings (must be FIRST middleware):

        MIDDLEWARE = [
            'cv_tailor.middleware.HealthCheckMiddleware',  # Must be first
            'django.middleware.security.SecurityMiddleware',
            # ... rest of middleware
        ]

    Related:
        - Critical Security Issue #2: Wildcard in production ALLOWED_HOSTS
        - docs/security/backend-security.md:186-266
    """

    def __init__(self, get_response):
        """Initialize middleware with the next middleware/view in chain."""
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request before view execution.

        Bypasses ALLOWED_HOSTS for health check requests from ALB.
        """
        # Check if this is a health check request
        if request.path == '/health/':
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # AWS ELB health checker User-Agent patterns
            is_elb_health_check = (
                'ELB-HealthChecker' in user_agent or
                'Amazon-Route53-Health-Check-Service' in user_agent
            )

            if is_elb_health_check:
                # Log health check (debug level to avoid log spam)
                logger.debug(
                    f"Health check from ALB: {user_agent} "
                    f"from {request.META.get('REMOTE_ADDR')}"
                )

                # Return 200 OK immediately, bypassing ALLOWED_HOSTS
                return HttpResponse('OK', status=200, content_type='text/plain')

        # For all other requests, proceed normally through middleware chain
        response = self.get_response(request)
        return response
