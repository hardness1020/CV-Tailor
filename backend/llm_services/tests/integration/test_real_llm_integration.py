"""
Real LLM API Integration Tests

These tests make actual API calls to LLM providers to verify integration works correctly.
They are designed to minimize token usage while ensuring core functionality works.

To run these tests:
1. Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY (optional)
2. Run with: python manage.py test llm_services.tests.test_real_llm_integration
3. Or pytest: pytest llm_services/tests/test_real_llm_integration.py -v

Note: These tests will consume actual API tokens and incur costs.
"""

import os
import pytest
import asyncio
import logging
from decimal import Decimal
from django.test import TestCase, override_settings, tag
from django.contrib.auth import get_user_model

from ...services.core.tailored_content_service import TailoredContentService
from ...services.core.artifact_ranking_service import ArtifactRankingService
from ...services.core.document_loader_service import DocumentLoaderService
from ..helpers.api_helpers import (
    ensure_api_keys_in_environment,
    get_real_api_test_settings,
    RealAPITestMixin
)
from .test_real_api_config import require_real_api_key, skip_unless_forced
from .test_real_api_config import require_real_api_key

User = get_user_model()
logger = logging.getLogger(__name__)


# Minimal test data to reduce token usage
MINIMAL_JOB_DESC = "Python dev. Skills: Django, REST APIs."
MINIMAL_ARTIFACTS = [
    {
        'id': 1,
        'title': 'API Project',
        'description': 'Built REST API with Django',
        'artifact_type': 'project',
        'technologies': ['Python', 'Django'],
        'start_date': '2023-01-01',
        'end_date': '2023-06-01'
    }
]
MINIMAL_JOB_DATA = {
    'company_name': 'TestCorp',
    'role_title': 'Python Dev',
    'must_have_skills': ['Python'],
    'nice_to_have_skills': ['Django'],
    'key_responsibilities': ['Build APIs']
}


@tag('slow', 'real_api', 'llm_services')
class RealLLMIntegrationTestCase(RealAPITestMixin, TestCase):
    """Test real LLM API integration with minimal token usage"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with real API keys."""
        super().setUpClass()
        ensure_api_keys_in_environment()

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.llm_service = TailoredContentService()

    @skip_unless_forced
    @require_real_api_key('openai')
    def test_real_job_description_parsing(self):
        """Test real job description parsing with minimal tokens"""

        async def run_test():
            result = await self.llm_service.parse_job_description(
                job_description=MINIMAL_JOB_DESC,
                company_name="TestCorp",
                role_title="Dev",
                user_id=self.user.id
            )

            # Verify basic structure without checking specific content
            # (since LLM outputs can vary)
            self.assertIsInstance(result, dict)
            self.assertNotIn('error', result, f"API call failed: {result}")

            # Check expected fields exist (updated to match actual API structure)
            self.assertIn('role_title', result)
            self.assertIn('must_have_skills', result)
            self.assertIn('processing_metadata', result)

            # Company info is nested under company_info.name, not company_name
            company_info = result.get('company_info', {})
            self.assertIsInstance(company_info, dict)
            self.assertIn('name', company_info)

            # Verify metadata tracking
            metadata = result.get('processing_metadata', {})
            self.assertIn('model_used', metadata)
            self.assertIn('processing_time_ms', metadata)
            self.assertGreater(metadata.get('tokens_used', 0), 0)

            # Verify cost tracking
            cost = metadata.get('cost_usd', 0)
            self.assertGreater(cost, 0)
            self.assertLess(cost, 0.01, "Test used too many tokens")  # Safety check

            logger.info(f"Job parsing test - Tokens: {metadata.get('tokens_used', 0)}, "
                       f"Cost: ${cost:.6f}, Model: {metadata.get('model_used', 'unknown')}")

            return result

        # Run async test
        result = asyncio.run(run_test())
        self.assertTrue(result)

    @skip_unless_forced
    @require_real_api_key('openai')
    def test_real_cv_generation_minimal(self):
        """Test real CV generation with minimal input to reduce tokens"""

        async def run_test():
            result = await self.llm_service.generate_cv_content(
                job_data=MINIMAL_JOB_DATA,
                artifacts=MINIMAL_ARTIFACTS,
                preferences={'style': 'concise'},
                user_id=self.user.id
            )

            # Verify basic structure
            self.assertIsInstance(result, dict)
            self.assertNotIn('error', result, f"CV generation failed: {result}")

            # Check content structure
            content = result.get('content', {})
            self.assertIsInstance(content, dict)
            self.assertTrue(len(content) > 0, "No content generated")

            # Verify processing metadata
            metadata = result.get('processing_metadata', {})
            self.assertIn('model_used', metadata)
            self.assertGreater(metadata.get('tokens_used', 0), 0)

            # Cost safety check
            cost = metadata.get('cost_usd', 0)
            self.assertLess(cost, 0.05, "Test used too many tokens")  # Higher limit for CV gen

            logger.info(f"CV generation test - Tokens: {metadata.get('tokens_used', 0)}, "
                       f"Cost: ${cost:.6f}, Model: {metadata.get('model_used', 'unknown')}")

            return result

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @skip_unless_forced
    @require_real_api_key('openai')
    def test_real_artifact_ranking(self):
        """Test real artifact ranking with minimal data"""

        async def run_test():
            # Use ArtifactRankingService instead of TailoredContentService
            ranking_service = ArtifactRankingService()

            job_skills = ['Python', 'Django']

            # Use keyword strategy for simpler testing (no embedding needed)
            result = await ranking_service.rank_artifacts_by_relevance(
                artifacts=MINIMAL_ARTIFACTS,
                job_requirements=job_skills,
                user_id=self.user.id,
                strategy='keyword'  # Use keyword strategy to avoid needing embeddings
            )

            # Verify basic structure
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0, "No ranked artifacts returned")

            # Debug what we actually got
            logger.info(f"Ranking result: {result}")

            # Check first ranked artifact has expected fields
            first_artifact = result[0]
            self.assertIn('id', first_artifact)
            self.assertIn('title', first_artifact)
            self.assertIn('relevance_score', first_artifact, "relevance_score missing from ranked artifact")

            # Score should be 0.0-1.0 (not 0-10)
            score = first_artifact.get('relevance_score', 0)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

            # Verify ranking method is set
            self.assertIn('ranking_method', first_artifact)
            self.assertEqual(first_artifact['ranking_method'], 'keyword')

            logger.info(f"Artifact ranking test - Artifacts ranked: {len(result)}, Top score: {score}")

            return result

        result = asyncio.run(run_test())
        self.assertTrue(result)


# REMOVED (ft-007): RealEmbeddingIntegrationTestCase - embeddings no longer used


@tag('slow', 'real_api', 'llm_services')
class RealDocumentProcessorTestCase(RealAPITestMixin, TestCase):
    """Test real document processing with LangChain"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with real API keys."""
        super().setUpClass()
        ensure_api_keys_in_environment()

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.processor = DocumentLoaderService()

    @skip_unless_forced
    def test_real_text_processing(self):
        """Test real text processing and chunking"""

        async def run_test():
            # Use minimal text content to avoid token usage
            test_content = """Python Developer Resume

            Skills: Python, Django, REST APIs
            Experience: 3 years backend development
            Projects: Built e-commerce API, payment system"""

            result = await self.processor.load_and_chunk_document(
                content=test_content,
                content_type='text',
                metadata={'title': 'Test Resume'}
            )

            # Verify basic structure
            self.assertIsInstance(result, dict)
            self.assertTrue(result.get('success', False), f"Processing failed: {result}")

            # Check chunks
            chunks = result.get('chunks', [])
            self.assertIsInstance(chunks, list)
            self.assertGreater(len(chunks), 0, "No chunks generated")

            # Verify chunk structure
            first_chunk = chunks[0]
            self.assertIn('content', first_chunk)
            self.assertIn('metadata', first_chunk)
            self.assertTrue(len(first_chunk['content']) > 0, "Empty chunk content")

            # Check processing metadata
            processing_metadata = result.get('processing_metadata', {})

            # If LangChain is available, check total_chunks
            if processing_metadata.get('langchain_used', False):
                self.assertIn('total_chunks', processing_metadata)
                self.assertEqual(processing_metadata['total_chunks'], len(chunks))
            else:
                # Fallback processing - verify it's marked as fallback
                self.assertTrue(processing_metadata.get('fallback_processing', False))

            logger.info(f"Text processing test - Chunks: {len(chunks)}, "
                       f"Total chars: {sum(len(c['content']) for c in chunks)}")

            return result

        result = asyncio.run(run_test())
        self.assertTrue(result)


@tag('slow', 'real_api', 'llm_services')
class APIBudgetSafetyTestCase(RealAPITestMixin, TestCase):
    """Safety tests to ensure we don't accidentally use too many tokens"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with real API keys."""
        super().setUpClass()
        ensure_api_keys_in_environment()

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @skip_unless_forced
    @require_real_api_key('openai')
    def test_token_usage_limits(self):
        """Test that our minimal test cases stay within safe token limits"""

        async def run_test():
            llm_service = TailoredContentService()

            # Test job parsing with strict token limits
            result = await llm_service.parse_job_description(
                job_description="Python dev",  # Extremely minimal
                company_name="Co",
                role_title="Dev",
                user_id=self.user.id
            )

            self.assertNotIn('error', result)

            # Strict token limit check
            metadata = result.get('processing_metadata', {})
            tokens_used = metadata.get('tokens_used', 0)
            cost_usd = metadata.get('cost_usd', 0)

            # Safety thresholds
            MAX_TOKENS = 500  # Very conservative limit
            MAX_COST_USD = 0.01  # 1 cent maximum

            self.assertLessEqual(tokens_used, MAX_TOKENS,
                               f"Token usage {tokens_used} exceeds safety limit {MAX_TOKENS}")
            self.assertLessEqual(cost_usd, MAX_COST_USD,
                               f"Cost ${cost_usd:.6f} exceeds safety limit ${MAX_COST_USD}")

            logger.warning(f"SAFETY CHECK - Tokens: {tokens_used}/{MAX_TOKENS}, "
                          f"Cost: ${cost_usd:.6f}/${MAX_COST_USD}")

            return result

        result = asyncio.run(run_test())
        self.assertTrue(result)

    @skip_unless_forced
    def test_input_size_validation(self):
        """Validate that our test inputs are appropriately sized"""

        # Check our test data sizes
        job_desc_tokens = len(MINIMAL_JOB_DESC.split())
        artifact_desc_tokens = sum(len(a.get('description', '').split()) for a in MINIMAL_ARTIFACTS)

        # Conservative token estimates (1 word ≈ 1.3 tokens)
        estimated_job_tokens = job_desc_tokens * 1.3
        estimated_artifact_tokens = artifact_desc_tokens * 1.3

        # Safety limits
        MAX_JOB_TOKENS = 20  # Very small job descriptions
        MAX_ARTIFACT_TOKENS = 50  # Small artifact descriptions

        self.assertLessEqual(estimated_job_tokens, MAX_JOB_TOKENS,
                           f"Job description too large: ~{estimated_job_tokens} tokens")
        self.assertLessEqual(estimated_artifact_tokens, MAX_ARTIFACT_TOKENS,
                           f"Artifact descriptions too large: ~{estimated_artifact_tokens} tokens")

        logger.info(f"Input size validation - Job: ~{estimated_job_tokens} tokens, "
                   f"Artifacts: ~{estimated_artifact_tokens} tokens")


# Test configuration for different environments
class RealAPITestSuite:
    """Test suite configuration for real API testing"""
    # Configuration values for real API testing
    TEST_SETTINGS = {
        'MODEL_SELECTION_STRATEGY': 'cost_optimized',
        'MODEL_BUDGETS': {
            'test_tier': {'daily_limit_usd': 0.50}  # 50 cents max for all tests
        },
        'LOGGING': {
            'version': 1,
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                },
            },
            'loggers': {
                'llm_services': {
                    'handlers': ['console'],
                    'level': 'INFO',
                },
            },
        }
    }


if __name__ == '__main__':
    # Run with: python manage.py test llm_services.tests.test_real_llm_integration
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["llm_services.tests.test_real_llm_integration"])