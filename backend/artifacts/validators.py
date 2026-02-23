"""
Evidence validation utilities for Layer 2 validation (ADR ft-010)

Implements async validation of evidence links before artifact submission.
This provides early feedback to users about accessibility issues with their evidence.

Security: SSRF protection implemented via artifacts.utils.SSRFProtection
"""
import requests
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .utils import SSRFProtection

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_evidence_links(request):
    """
    Validate multiple evidence links (Layer 2 validation from ft-010).

    Request body:
        {
            "evidence_links": [
                {"url": "...", "evidence_type": "github"},
                {"url": "...", "evidence_type": "document"}
            ]
        }

    Response:
        {
            "results": [
                {
                    "url": "...",
                    "evidence_type": "...",
                    "valid": true,
                    "accessible": true,
                    "status": "success",  // "success" | "warning" | "error"
                    "message": null
                },
                {...}
            ]
        }
    """
    evidence_links = request.data.get('evidence_links', [])
    results = []

    for link in evidence_links:
        url = link.get('url')
        evidence_type = link.get('evidence_type')

        if not url:
            results.append({
                'url': url,
                'evidence_type': evidence_type,
                'valid': False,
                'accessible': False,
                'status': 'error',
                'message': 'URL is required'
            })
            continue

        result = validate_single_evidence(url, evidence_type)
        results.append({
            'url': url,
            'evidence_type': evidence_type,
            **result
        })

    return Response({'results': results})


def validate_single_evidence(url: str, evidence_type: str) -> dict:
    """
    Validate a single evidence link.

    Returns:
        {
            "valid": bool,        # URL format is valid
            "accessible": bool,   # Resource is accessible
            "status": str,        # "success" | "warning" | "error"
            "message": str        # Human-readable message
        }
    """
    # URL format already validated by frontend Zod schema

    # Validate evidence type
    if evidence_type not in ['github', 'document']:
        return {
            'valid': False,
            'accessible': False,
            'status': 'error',
            'message': f"Evidence type '{evidence_type}' is not supported. Use 'github' or 'document'."
        }

    if evidence_type == 'github':
        return validate_github_repo(url)
    elif evidence_type == 'document':
        # Documents must be uploaded files (with file_path), not URLs
        # This validator is only for URL-based evidence (GitHub repositories)
        return {
            'valid': False,
            'accessible': False,
            'status': 'error',
            'message': 'Document evidence must be uploaded files, not URLs. Please use the file upload section.'
        }
    else:
        # This should never be reached due to validation above
        return {
            'valid': False,
            'accessible': False,
            'status': 'error',
            'message': f"Unknown evidence type: {evidence_type}"
        }


def validate_github_repo(url: str) -> dict:
    """
    Validate GitHub repository accessibility.

    Uses GitHub API to check if repository exists and is accessible.
    Returns warnings (not errors) for private/not found repos to allow submission.
    """
    try:
        # Extract owner/repo from URL
        # Format: https://github.com/owner/repo
        url_clean = url.replace('https://github.com/', '').replace('http://github.com/', '')
        parts = url_clean.split('/')

        if len(parts) < 2:
            return {
                'valid': False,
                'accessible': False,
                'status': 'error',
                'message': 'Invalid GitHub URL format. Expected: https://github.com/owner/repo'
            }

        owner = parts[0]
        repo = parts[1].split('?')[0].split('#')[0]  # Remove query params and fragments

        # Validate owner/repo format
        if not owner or not repo:
            return {
                'valid': False,
                'accessible': False,
                'status': 'error',
                'message': 'Invalid GitHub URL format'
            }

        api_url = f'https://api.github.com/repos/{owner}/{repo}'

        # SECURITY: Validate URL to prevent SSRF attacks
        try:
            SSRFProtection.validate_url(api_url)
        except ValueError as e:
            logger.warning(f"SSRF protection blocked URL: {api_url}, reason: {e}")
            return {
                'valid': False,
                'accessible': False,
                'status': 'error',
                'message': f'URL blocked for security reasons: {str(e)}'
            }

        # HEAD request to check existence (lightweight, no body)
        response = requests.head(api_url, timeout=5)

        if response.status_code == 200:
            return {
                'valid': True,
                'accessible': True,
                'status': 'success',
                'message': 'Repository found and accessible'
            }
        elif response.status_code == 404:
            return {
                'valid': True,
                'accessible': False,
                'status': 'warning',
                'message': 'Repository not found. It may be private or the URL is incorrect. You can still submit.'
            }
        elif response.status_code == 403:
            return {
                'valid': True,
                'accessible': False,
                'status': 'warning',
                'message': 'Repository may be private or GitHub API rate limit exceeded. You can still submit.'
            }
        else:
            return {
                'valid': True,
                'accessible': False,
                'status': 'warning',
                'message': f'Could not verify repository (HTTP {response.status_code}). You can still submit.'
            }

    except requests.RequestException as e:
        logger.error(f"GitHub validation error for {url}: {e}")
        return {
            'valid': True,
            'accessible': False,
            'status': 'warning',
            'message': 'Could not verify repository due to network error. You can still submit.'
        }
    except Exception as e:
        logger.error(f"Unexpected error validating GitHub URL {url}: {e}")
        return {
            'valid': True,
            'accessible': False,
            'status': 'warning',
            'message': 'Could not verify repository. You can still submit.'
        }


def validate_web_url(url: str) -> dict:
    """
    Validate web URL accessibility.

    Performs HEAD request to check if URL is accessible.
    Returns warnings (not errors) for inaccessible URLs to allow submission.
    """
    try:
        # SECURITY: Validate URL to prevent SSRF attacks
        try:
            SSRFProtection.validate_url(url)
        except ValueError as e:
            logger.warning(f"SSRF protection blocked URL: {url}, reason: {e}")
            return {
                'valid': False,
                'accessible': False,
                'status': 'error',
                'message': f'URL blocked for security reasons: {str(e)}'
            }

        response = requests.head(url, timeout=5, allow_redirects=True, max_redirects=3)

        if response.status_code == 200:
            return {
                'valid': True,
                'accessible': True,
                'status': 'success',
                'message': 'URL is accessible'
            }
        elif 400 <= response.status_code < 500:
            return {
                'valid': True,
                'accessible': False,
                'status': 'warning',
                'message': f'URL returned HTTP {response.status_code}. The site may require authentication. You can still submit.'
            }
        else:
            return {
                'valid': True,
                'accessible': False,
                'status': 'warning',
                'message': f'URL returned HTTP {response.status_code}. You can still submit.'
            }
    except requests.Timeout:
        logger.warning(f"Timeout validating URL: {url}")
        return {
            'valid': True,
            'accessible': False,
            'status': 'warning',
            'message': 'URL validation timed out. The site may be slow or unreachable. You can still submit.'
        }
    except requests.RequestException as e:
        logger.error(f"Web URL validation error for {url}: {e}")
        return {
            'valid': True,
            'accessible': False,
            'status': 'warning',
            'message': 'Could not verify URL due to network error. You can still submit.'
        }
    except Exception as e:
        logger.error(f"Unexpected error validating web URL {url}: {e}")
        return {
            'valid': True,
            'accessible': False,
            'status': 'warning',
            'message': 'Could not verify URL. You can still submit.'
        }
