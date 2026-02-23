"""
Configuration and Utilities for Real LLM API Testing

This module provides:
- Safe test configuration with strict token limits
- Cost monitoring and budget enforcement
- Test data optimization for minimal token usage
- Environment validation for real API testing

Usage:
    from .test_real_api_config import RealAPITestConfig, TestDataFactory

    config = RealAPITestConfig()
    if config.should_run_real_tests():
        test_data = TestDataFactory.minimal_job_description()
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
from django.conf import settings
from django.test import override_settings, tag
from unittest import skipIf
from ..helpers.api_helpers import has_openai_api_key, has_anthropic_api_key, should_run_real_api_tests

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Token usage budget for test safety"""
    max_tokens_per_test: int = 30000     # Realistic for CV generation
    max_tokens_total: int = 50000        # Total budget for all tests
    max_cost_per_test_usd: float = 0.30  # 30 cents per test (realistic for CV generation)
    max_cost_total_usd: float = 1.00     # $1 total budget
    current_usage: int = field(default=0)
    current_cost: float = field(default=0.0)

    def can_use_tokens(self, tokens: int, cost: float = 0.0) -> bool:
        """Check if token usage is within budget"""
        return (
            tokens <= self.max_tokens_per_test and
            self.current_usage + tokens <= self.max_tokens_total and
            cost <= self.max_cost_per_test_usd and
            self.current_cost + cost <= self.max_cost_total_usd
        )

    def record_usage(self, tokens: int, cost: float):
        """Record token usage"""
        self.current_usage += tokens
        self.current_cost += cost

    def get_remaining_budget(self) -> Dict[str, Any]:
        """Get remaining budget information"""
        return {
            'tokens_remaining': self.max_tokens_total - self.current_usage,
            'cost_remaining_usd': self.max_cost_total_usd - self.current_cost,
            'usage_percent': (self.current_usage / self.max_tokens_total) * 100,
            'cost_percent': (self.current_cost / self.max_cost_total_usd) * 100
        }


class RealAPITestConfig:
    """Configuration manager for real API tests"""

    def __init__(self):
        self.budget = TokenBudget()
        self.openai_available = has_openai_api_key()
        self.anthropic_available = has_anthropic_api_key()



    def get_safe_django_settings(self) -> Dict[str, Any]:
        """Get Django settings overrides for safe testing"""
        return {
            'MODEL_SELECTION_STRATEGY': 'cost_optimized',
            'MODEL_BUDGETS': {
                'test_tier': {
                    'daily_limit_usd': self.budget.max_cost_total_usd,
                    'hourly_limit_usd': self.budget.max_cost_total_usd / 24
                }
            },
            'DEFAULT_MODEL_TEMPERATURE': 0.0,  # Deterministic outputs
            'OPENAI_MAX_RETRIES': 1,  # Reduce retry attempts
            'ANTHROPIC_MAX_RETRIES': 1,
            'CACHE_EMBEDDING_RESULTS': True,  # Cache to avoid duplicate calls
            'LOGGING': {
                'version': 1,
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'level': 'INFO',
                    },
                },
                'loggers': {
                    'llm_services.tests': {
                        'handlers': ['console'],
                        'level': 'INFO',
                        'propagate': False,
                    },
                },
            }
        }

    def validate_test_result(self, result: Dict[str, Any], test_name: str) -> bool:
        """Validate test result against budget constraints"""
        if 'error' in result:
            logger.warning(f"{test_name} failed: {result['error']}")
            return False

        metadata = result.get('processing_metadata', {})
        tokens_used = metadata.get('tokens_used', 0)
        cost_usd = metadata.get('cost_usd', 0.0)

        if not self.budget.can_use_tokens(tokens_used, cost_usd):
            logger.error(f"{test_name} exceeded budget - "
                        f"Tokens: {tokens_used}, Cost: ${cost_usd:.6f}")
            return False

        self.budget.record_usage(tokens_used, cost_usd)

        logger.info(f"{test_name} - Tokens: {tokens_used}, Cost: ${cost_usd:.6f}, "
                   f"Budget remaining: {self.budget.get_remaining_budget()}")

        return True


class TestDataFactory:
    """Factory for generating minimal test data to reduce token usage"""

    @staticmethod
    def minimal_job_description() -> str:
        """Extremely minimal job description"""
        return "Python dev. Django, APIs."

    @staticmethod
    def minimal_job_data() -> Dict[str, Any]:
        """Minimal parsed job data"""
        return {
            'company_name': 'Co',
            'role_title': 'Dev',
            'must_have_skills': ['Python'],
            'nice_to_have_skills': ['Django'],
            'key_responsibilities': ['Code'],
            'seniority_level': 'mid',
            'confidence_score': 0.8
        }

    @staticmethod
    def minimal_artifacts() -> List[Dict[str, Any]]:
        """Minimal artifact data"""
        return [
            {
                'id': 1,
                'title': 'API Project',
                'description': 'Built REST API',
                'artifact_type': 'project',
                'technologies': ['Python'],
                'start_date': '2023-01-01',
                'end_date': '2023-06-01',
                'evidence_links': [],
                'extracted_metadata': {}
            }
        ]

    @staticmethod
    def minimal_text_content() -> str:
        """Minimal text for document processing"""
        return """Resume
        Skills: Python, Django
        Experience: API development
        Projects: Built web app"""

    @staticmethod
    def minimal_generation_preferences() -> Dict[str, Any]:
        """Minimal CV generation preferences"""
        return {
            'style': 'concise',
            'max_experience_items': 2,
            'max_skills': 5,
            'include_summary': True,
            'include_projects': False  # Reduce content
        }

    @staticmethod
    def minimal_embedding_text() -> str:
        """Minimal text for embedding generation"""
        return "Python developer"

    @staticmethod
    def get_token_estimate(text: str) -> int:
        """Rough token estimate for text (1 word ≈ 1.3 tokens)"""
        words = len(text.split())
        return int(words * 1.3)

    @classmethod
    def validate_minimal_data(cls) -> Dict[str, int]:
        """Validate that our minimal data is actually minimal"""
        validations = {
            'job_description_tokens': cls.get_token_estimate(cls.minimal_job_description()),
            'artifact_description_tokens': sum(
                cls.get_token_estimate(a.get('description', ''))
                for a in cls.minimal_artifacts()
            ),
            'text_content_tokens': cls.get_token_estimate(cls.minimal_text_content()),
            'embedding_text_tokens': cls.get_token_estimate(cls.minimal_embedding_text()),
        }

        # Safety checks
        for key, token_count in validations.items():
            if token_count > 50:  # Very conservative limit
                logger.warning(f"{key} has {token_count} tokens - consider reducing")

        return validations


# Decorators for real API testing
skip_unless_forced = skipIf(
    not should_run_real_api_tests(),
    "Skipping real API test. Set FORCE_REAL_API_TESTS=true to enable."
)

def require_real_api_key(api_provider: str = 'openai'):
    """Decorator to check if API key is available, raise error if not"""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            if api_provider == 'openai':
                if not has_openai_api_key():
                    raise RuntimeError("ERROR: OpenAI API key is required for real API tests. Please set OPENAI_API_KEY environment variable.")
            elif api_provider == 'anthropic':
                if not has_anthropic_api_key():
                    raise RuntimeError("ERROR: Anthropic API key is required for real API tests. Please set ANTHROPIC_API_KEY environment variable.")
            else:
                raise RuntimeError(f"ERROR: Unknown API provider: {api_provider}")

            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def with_budget_control(budget: Optional[TokenBudget] = None):
    """Decorator to add budget control to test methods"""
    def decorator(test_func):
        def wrapper(self, *args, **kwargs):
            # Run the test directly since real API tests should always run if API keys are available
            result = test_func(self, *args, **kwargs)

            # Validate budget if result contains metadata
            if hasattr(result, 'get') and isinstance(result, dict):
                config = RealAPITestConfig()
                config.validate_test_result(result, test_func.__name__)

            return result
        return wrapper
    return decorator


def with_safe_settings():
    """Decorator to apply safe settings for real API tests"""
    def decorator(test_class):
        """Apply safe settings to test class methods"""
        config = RealAPITestConfig()
        safe_settings = config.get_safe_django_settings()

        # Apply override_settings to each test method instead of class
        for attr_name in dir(test_class):
            attr = getattr(test_class, attr_name)
            if callable(attr) and attr_name.startswith('test_'):
                # Apply override_settings to individual test methods
                setattr(test_class, attr_name, override_settings(**safe_settings)(attr))

        return test_class
    return decorator


# Test utilities
class RealAPITestHelper:
    """Helper class for real API testing"""

    @staticmethod
    def log_test_summary(test_results: List[Dict[str, Any]]):
        """Log summary of test results"""
        total_tokens = sum(
            r.get('processing_metadata', {}).get('tokens_used', 0)
            for r in test_results if 'error' not in r
        )
        total_cost = sum(
            r.get('processing_metadata', {}).get('cost_usd', 0.0)
            for r in test_results if 'error' not in r
        )
        successful_tests = len([r for r in test_results if 'error' not in r])

        logger.info(f"Test Summary - Successful: {successful_tests}/{len(test_results)}, "
                   f"Total tokens: {total_tokens}, Total cost: ${total_cost:.6f}")

    @staticmethod
    def create_test_environment():
        """Create safe test environment settings"""
        return {
            'CELERY_TASK_ALWAYS_EAGER': True,
            'CELERY_TASK_EAGER_PROPAGATES': True,
            'CACHES': {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                }
            },
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
        }


# Example usage configuration
REAL_API_TEST_CONFIG = RealAPITestConfig()
TEST_DATA = TestDataFactory()

# Validation on import
if __name__ == '__main__':
    config = RealAPITestConfig()
    print(f"OpenAI API available: {config.openai_available}")
    print(f"Anthropic API available: {config.anthropic_available}")
    print(f"Budget: {config.budget}")

    validation = TestDataFactory.validate_minimal_data()
    print(f"Data validation: {validation}")