"""
Common test mocks and fixtures for the CV-Tailor test suite.

Provides reusable mock objects for:
- LLM service responses (TailoredContentService)
- Bullet point generation
- Validation results
- API responses

Usage:
    from common.test_mocks import mock_llm_bullet_response, mock_validation_result

    with patch.object(service, 'tailored_content_service') as mock_llm:
        mock_llm.generate_bullet_points = AsyncMock(return_value=mock_llm_bullet_response())
        result = await service.generate_bullets(...)
"""

from unittest.mock import Mock, AsyncMock
from decimal import Decimal
from typing import List, Dict, Any, Optional


# ============================================================================
# LLM Service Mocks
# ============================================================================

def mock_llm_bullet_response(
    num_bullets: int = 3,
    quality_score: float = 0.85,
    cost_usd: float = 0.0025,
    generation_time_ms: int = 1200,
    model_used: str = "gpt-5"
) -> Dict[str, Any]:
    """
    Mock response from TailoredContentService.generate_bullet_points()

    Args:
        num_bullets: Number of bullets to generate (default 3)
        quality_score: Overall quality score 0-1 (default 0.85)
        cost_usd: Mock API cost (default $0.0025)
        generation_time_ms: Mock generation time (default 1200ms)
        model_used: Model identifier (default "gpt-5")

    Returns:
        Dictionary matching TailoredContentService response format
    """
    bullets = []
    bullet_types = ['achievement', 'technical', 'impact']

    # Generate varied, realistic bullets that pass validation
    bullet_templates = [
        "Led development of microservices platform serving 100k+ daily users with 99.9% uptime",
        "Built scalable REST API using Python Django and PostgreSQL with comprehensive test coverage",
        "Improved system performance by 40% through database query optimization and caching strategies"
    ]

    for i in range(num_bullets):
        # Use templates if available, otherwise generate generic
        if i < len(bullet_templates):
            bullet_text = bullet_templates[i]
        else:
            bullet_text = f"Achieved significant milestone {i+1} using technical expertise with measurable 50% improvement"

        bullets.append({
            'text': bullet_text,
            'bullet_type': bullet_types[i % len(bullet_types)],
            'position': i + 1,
            'confidence_score': quality_score + (i * 0.02),  # Vary slightly
            'keywords': ['Python', 'Django', 'PostgreSQL'][:i+1],  # Note: 'keywords' not 'keywords_matched'
            'metrics': {}  # Empty metrics dict
        })

    return {
        'bullet_points': bullets,  # Note: 'bullet_points' not 'bullets'
        'processing_metadata': {  # Note: 'processing_metadata' not 'metadata'
            'total_bullets': num_bullets,
            'quality_score': quality_score,
            'generation_time_ms': generation_time_ms,
            'cost_usd': cost_usd,
            'model_used': model_used,
            'tokens_used': {
                'input': 150,
                'output': 80 * num_bullets,
                'total': 150 + (80 * num_bullets)
            }
        }
    }


def mock_llm_single_bullet_response(
    bullet_text: Optional[str] = None,
    bullet_type: str = 'achievement',
    quality_score: float = 0.85
) -> Dict[str, Any]:
    """
    Mock response for single bullet regeneration.

    Args:
        bullet_text: Custom bullet text (default auto-generated)
        bullet_type: Type of bullet (achievement/technical/impact)
        quality_score: Quality score 0-1

    Returns:
        Dictionary matching TailoredContentService single bullet response
    """
    if bullet_text is None:
        bullet_text = f"Regenerated {bullet_type} bullet point with proper length of 80-120 chars for testing"

    return {
        'bullet': {
            'text': bullet_text,
            'bullet_type': bullet_type,
            'confidence_score': quality_score,
            'keywords_matched': ['Python', 'Django']
        },
        'metadata': {
            'generation_time_ms': 800,
            'cost_usd': 0.001,
            'model_used': 'gpt-5',
            'tokens_used': {
                'input': 100,
                'output': 30,
                'total': 130
            }
        }
    }


# ============================================================================
# Validation Result Mocks
# ============================================================================

def mock_validation_result(
    is_valid: bool = True,
    overall_quality_score: float = 0.85,
    bullet_scores: Optional[List[float]] = None,
    issues: Optional[List[str]] = None
) -> Mock:
    """
    Mock ValidationResult from BulletValidationService.

    Args:
        is_valid: Whether validation passed
        overall_quality_score: Overall quality 0-1
        bullet_scores: Individual bullet scores (default [0.85, 0.87, 0.83])
        issues: List of validation issues (default empty if valid)

    Returns:
        Mock object with validation result attributes
    """
    if bullet_scores is None:
        bullet_scores = [0.85, 0.87, 0.83]

    if issues is None:
        issues = [] if is_valid else ['Quality below threshold']

    return Mock(
        is_valid=is_valid,
        overall_quality_score=overall_quality_score,
        bullet_scores=bullet_scores,
        issues=issues,
        validation_metadata={
            'checks_passed': ['length', 'uniqueness', 'keywords'] if is_valid else ['length'],
            'checks_failed': [] if is_valid else ['quality_score'],
            'validation_time_ms': 50
        }
    )


def mock_validation_result_invalid(
    reason: str = "Quality below threshold",
    overall_quality_score: float = 0.45
) -> Mock:
    """
    Mock invalid ValidationResult for testing retry logic.

    Args:
        reason: Failure reason
        overall_quality_score: Low quality score

    Returns:
        Mock object representing failed validation
    """
    return mock_validation_result(
        is_valid=False,
        overall_quality_score=overall_quality_score,
        bullet_scores=[0.45, 0.40, 0.50],
        issues=[reason]
    )


# ============================================================================
# Bullet Point Mocks
# ============================================================================

def mock_bullet_point_data(
    position: int = 1,
    bullet_type: str = 'achievement',
    text: Optional[str] = None,
    quality_score: float = 0.85
) -> Dict[str, Any]:
    """
    Mock bullet point data for database creation.

    Args:
        position: Position in sequence (1-3)
        bullet_type: Type (achievement/technical/impact)
        text: Custom text (default auto-generated)
        quality_score: Quality score 0-1

    Returns:
        Dictionary suitable for BulletPoint.objects.create()
    """
    if text is None:
        text = f"Mock {bullet_type} bullet point at position {position} with appropriate length for testing"

    return {
        'position': position,
        'bullet_type': bullet_type,
        'text': text,
        'quality_score': Decimal(str(quality_score)),
        'is_approved': False,
        'keywords_matched': ['Python', 'Django', 'PostgreSQL'],
        'generation_metadata': {
            'model_used': 'gpt-5',
            'confidence_score': quality_score,
            'generation_time_ms': 1200
        }
    }


# ============================================================================
# Mock Async LLM Service
# ============================================================================

class MockTailoredContentService:
    """
    Mock TailoredContentService for testing without API calls.

    Usage:
        mock_service = MockTailoredContentService()
        with patch('generation.services.bullet_generation_service.TailoredContentService',
                   return_value=mock_service):
            # Tests run with mocked service
            result = await service.generate_bullets(...)
    """

    def __init__(self, fail_after: Optional[int] = None):
        """
        Initialize mock service.

        Args:
            fail_after: Number of successful calls before failing (for testing retry logic)
        """
        self.call_count = 0
        self.fail_after = fail_after
        self.generate_bullet_points = AsyncMock(side_effect=self._generate_bullets)
        self.generate_single_bullet = AsyncMock(side_effect=self._generate_single_bullet)

    async def _generate_bullets(self, *args, **kwargs) -> Dict[str, Any]:
        """Mock implementation of generate_bullet_points()"""
        self.call_count += 1

        if self.fail_after and self.call_count > self.fail_after:
            raise Exception("Mock API failure for testing retry logic")

        return mock_llm_bullet_response(
            num_bullets=kwargs.get('target_count', 3)
        )

    async def _generate_single_bullet(self, *args, **kwargs) -> Dict[str, Any]:
        """Mock implementation of generate_single_bullet()"""
        self.call_count += 1

        if self.fail_after and self.call_count > self.fail_after:
            raise Exception("Mock API failure for testing retry logic")

        return mock_llm_single_bullet_response(
            bullet_type=kwargs.get('bullet_type', 'achievement')
        )


# ============================================================================
# Semantic Similarity Mocks
# ============================================================================

def mock_semantic_similarity_result(
    similar_pairs: Optional[List[tuple]] = None,
    similarity_threshold: float = 0.85
) -> List[Dict[str, Any]]:
    """
    Mock semantic similarity check results.

    Args:
        similar_pairs: List of (idx1, idx2) tuples for similar bullets
        similarity_threshold: Threshold used

    Returns:
        List of similarity result dictionaries
    """
    if similar_pairs is None:
        similar_pairs = []

    results = []
    for idx1, idx2 in similar_pairs:
        results.append({
            'bullet_1_index': idx1,
            'bullet_2_index': idx2,
            'similarity_score': similarity_threshold + 0.05,
            'is_duplicate': True
        })

    return results


# ============================================================================
# Export convenience function for common test scenarios
# ============================================================================

def setup_mocked_llm_service(mock_response: Optional[Dict] = None) -> AsyncMock:
    """
    Quick setup for mocked LLM service in tests.

    Usage:
        mock_llm = setup_mocked_llm_service()
        with patch.object(service, 'tailored_content_service', mock_llm):
            result = await service.generate_bullets(...)

    Args:
        mock_response: Custom response (default uses mock_llm_bullet_response())

    Returns:
        AsyncMock configured with generate_bullet_points method
    """
    if mock_response is None:
        mock_response = mock_llm_bullet_response()

    mock_service = Mock()
    mock_service.generate_bullet_points = AsyncMock(return_value=mock_response)
    mock_service.generate_single_bullet = AsyncMock(
        return_value=mock_llm_single_bullet_response()
    )
    return mock_service
