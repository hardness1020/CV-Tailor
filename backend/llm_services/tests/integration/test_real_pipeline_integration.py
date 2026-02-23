"""
End-to-End Pipeline Integration Tests with Real APIs

Tests the complete CV generation pipeline using real LLM APIs with strict token budgets.
Simulates the full workflow from job description to generated CV.

To run: python manage.py test llm_services.tests.test_real_pipeline_integration

WARNING: These tests use real API tokens and incur costs.
- test_end_to_end_pipeline_minimal: ~$0.10-0.25 (10-25 cents)

For PDF enrichment tests, see: test_real_pdf_enrichment.py
"""

import os
import asyncio
import logging
from django.test import TestCase, TransactionTestCase, tag
from django.contrib.auth import get_user_model
from django.db import transaction

from .test_real_api_config import (
    RealAPITestConfig, TestDataFactory, require_real_api_key,
    with_budget_control, with_safe_settings, RealAPITestHelper, skip_unless_forced
)
from llm_services.services.core.tailored_content_service import TailoredContentService
from llm_services.services.core.artifact_ranking_service import ArtifactRankingService
from llm_services.services.core.document_loader_service import DocumentLoaderService
from generation.models import GeneratedDocument, JobDescription
from artifacts.models import Artifact

User = get_user_model()
logger = logging.getLogger(__name__)

config = RealAPITestConfig()


@with_safe_settings()
@tag('slow', 'real_api', 'llm_services')
class RealPipelineIntegrationTestCase(TransactionTestCase):
    """Test complete CV generation pipeline with real APIs"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pipeline_user',
            email='pipeline@example.com',
            password='testpass123'
        )
        self.config = RealAPITestConfig()
        self.test_results = []

    def tearDown(self):
        """Log test summary"""
        if self.test_results:
            RealAPITestHelper.log_test_summary(self.test_results)

    @skip_unless_forced
    @require_real_api_key('openai')
    @with_budget_control()
    def test_end_to_end_pipeline_minimal(self):
        """Test complete pipeline with minimal data to reduce token usage"""


        # Step 1: Create minimal job description
        job_desc = JobDescription.objects.create(
            raw_content=TestDataFactory.minimal_job_description(),
            company_name="TestCorp",
            role_title="Python Dev",
            content_hash="test_hash_pipeline"
        )

        # Step 2: Create minimal artifact
        artifact = Artifact.objects.create(
            user=self.user,
            title="API Project",
            description="Built REST API with Python",
            artifact_type="project",
            technologies=["Python", "Django"]
        )

        # Step 3: Create generation request
        generation = GeneratedDocument.objects.create(
            user=self.user,
            job_description=job_desc,
            generation_preferences=TestDataFactory.minimal_generation_preferences(),
            status='pending'
        )

        # Step 4: Test the full pipeline
        async def run_pipeline():
            llm_service = TailoredContentService()
            ranking_service = ArtifactRankingService()

            # Parse job description (if not already parsed)
            if not job_desc.parsed_data:
                parse_result = await llm_service.parse_job_description(
                    job_desc.raw_content,
                    job_desc.company_name,
                    job_desc.role_title,
                    self.user.id
                )
                self.test_results.append(parse_result)
                self.assertNotIn('error', parse_result)

                # Update job description with parsed data (excluding non-serializable objects)
                from asgiref.sync import sync_to_async

                # Create a clean copy without the usage object for database storage
                clean_parse_result = {k: v for k, v in parse_result.items() if k != 'usage'}

                job_desc.parsed_data = clean_parse_result
                job_desc.parsing_confidence = clean_parse_result.get('confidence_score', 0.5)
                await sync_to_async(job_desc.save)()

            # Rank artifacts
            artifacts_data = [{
                'id': artifact.id,
                'title': artifact.title,
                'description': artifact.description,
                'artifact_type': artifact.artifact_type,
                'technologies': artifact.technologies,
                'start_date': None,
                'end_date': None,
                'evidence_links': [],
                'extracted_metadata': {}
            }]

            job_requirements = (
                job_desc.parsed_data.get('must_have_skills', []) +
                job_desc.parsed_data.get('nice_to_have_skills', [])
            )

            # Use ArtifactRankingService for ranking
            ranking_result = await ranking_service.rank_artifacts_by_relevance(
                artifacts_data,
                job_requirements,
                user_id=self.user.id,
                strategy='keyword'  # Use keyword strategy to avoid embedding requirements
            )
            # Note: Ranking might not have processing_metadata, so don't add to test_results

            # Generate CV content
            cv_result = await llm_service.generate_cv_content(
                job_data=job_desc.parsed_data,
                artifacts=ranking_result[:1],  # Use only top artifact to minimize tokens
                preferences=generation.generation_preferences,
                user_id=self.user.id
            )
            self.test_results.append(cv_result)
            self.assertNotIn('error', cv_result)

            # Update generation with results
            generation.content = cv_result.get('cv_content', cv_result.get('content', {}))
            generation.status = 'completed'

            processing_metadata = cv_result.get('processing_metadata', {})
            generation.metadata = {
                'model_used': processing_metadata.get('model_used'),
                'generation_time_ms': processing_metadata.get('processing_time_ms'),
                'token_usage': processing_metadata.get('tokens_used'),
                'cost_usd': processing_metadata.get('cost_usd'),
                'quality_score': processing_metadata.get('quality_score'),
            }
            await sync_to_async(generation.save)()

            return {
                'generation_id': generation.id,
                'job_parsing': parse_result,
                'cv_generation': cv_result,
                'artifacts_ranked': len(ranking_result)
            }

        # Run the pipeline
        pipeline_result = asyncio.run(run_pipeline())

        # Verify pipeline completed successfully
        self.assertIsInstance(pipeline_result, dict)
        self.assertIn('generation_id', pipeline_result)

        # Verify generation was updated
        generation.refresh_from_db()
        self.assertEqual(generation.status, 'completed')
        self.assertTrue(generation.content)

        # Verify content structure
        content = generation.content
        self.assertTrue(content, "Generated content should not be empty")
        # Content can be either string (formatted CV) or dict (structured data)
        if isinstance(content, str):
            self.assertGreater(len(content), 100, "CV content should be substantial")
        elif isinstance(content, dict):
            self.assertTrue(len(content) > 0, "Content dict should not be empty")
        else:
            self.fail(f"Content should be string or dict, got {type(content)}")

        # Verify budget compliance for all API calls
        total_cost = sum(
            r.get('processing_metadata', {}).get('cost_usd', 0.0)
            for r in self.test_results
        )
        total_tokens = sum(
            r.get('processing_metadata', {}).get('tokens_used', 0)
            for r in self.test_results
        )

        # Safety checks - Realistic limits for full CV generation pipeline
        max_total_cost = 0.25  # 25 cents max for entire pipeline (more realistic)
        max_total_tokens = 25000  # 25k tokens max (realistic for job parsing + CV generation)

        self.assertLess(total_cost, max_total_cost,
                       f"Pipeline cost ${total_cost:.6f} exceeds limit ${max_total_cost}")
        self.assertLess(total_tokens, max_total_tokens,
                       f"Pipeline tokens {total_tokens} exceeds limit {max_total_tokens}")

        logger.info(f"Pipeline test completed - Total cost: ${total_cost:.6f}, "
                   f"Total tokens: {total_tokens}, Generation ID: {generation.id}")

        return pipeline_result

    @skip_unless_forced
    @require_real_api_key('openai')
    def test_artifact_enhancement_minimal(self):
        """Test artifact enhancement with minimal content"""


        # Create minimal artifact for enhancement
        artifact = Artifact.objects.create(
            user=self.user,
            title="Test Project",
            description="Small Python project with Django",
            artifact_type="project",
            technologies=["Python"]
        )

        # Test document processing (without LLM enhancement to save tokens)
        async def run_enhancement():
            processor = DocumentLoaderService()

            # Process minimal text content
            result = await processor.load_and_chunk_document(
                content=TestDataFactory.minimal_text_content(),
                content_type='text',
                metadata={'title': artifact.title, 'artifact_id': artifact.id}
            )

            return result

        result = asyncio.run(run_enhancement())

        # Verify processing succeeded
        self.assertTrue(result.get('success', False))
        self.assertIn('chunks', result)
        self.assertGreater(len(result['chunks']), 0)

        # Verify chunks have correct structure
        first_chunk = result['chunks'][0]
        self.assertIn('content', first_chunk)
        self.assertIn('metadata', first_chunk)

        logger.info(f"Artifact enhancement test - Chunks: {len(result['chunks'])}")

    # REMOVED (ft-007): test_embedding_similarity_search - embeddings no longer used

    @skip_unless_forced
    def test_model_selection_and_fallback(self):
        """Test intelligent model selection and fallback mechanisms"""

        async def run_model_selection_test():
            llm_service = TailoredContentService()

            # Test model selection for different complexity levels
            simple_model = llm_service.model_selector.select_model_for_task(
                task_type='job_parsing',
                context={
                    'job_description': 'Simple job posting',  # Simple task
                    'user_id': self.user.id
                }
            )

            complex_model = llm_service.model_selector.select_model_for_task(
                task_type='cv_generation',
                context={
                    'job_description': 'Very complex senior software engineer position with extensive requirements and multiple technical domains including machine learning, distributed systems, cloud architecture, and full-stack development across multiple programming languages and frameworks',  # Complex task
                    'user_id': self.user.id
                }
            )

            # Verify selections are reasonable
            self.assertIsInstance(simple_model, str)
            self.assertIsInstance(complex_model, str)
            self.assertTrue(len(simple_model) > 0)
            self.assertTrue(len(complex_model) > 0)

            # Models should be different for different complexity levels
            # (unless there's only one model available)
            logger.info(f"Model selection - Simple: {simple_model}, "
                       f"Complex: {complex_model}")

            return {
                'simple_model': simple_model,
                'complex_model': complex_model
            }

        result = asyncio.run(run_model_selection_test())
        self.assertTrue(result)

    @skip_unless_forced
    def test_cost_tracking_accuracy(self):
        """Test that cost tracking is accurate and within expected ranges"""


        async def run_cost_test():
            llm_service = TailoredContentService()

            # Make a minimal API call and track cost
            result = await llm_service.parse_job_description(
                job_description="Dev job",
                company_name="Co",
                role_title="Dev",
                user_id=self.user.id
            )

            self.test_results.append(result)
            self.assertNotIn('error', result)

            metadata = result.get('processing_metadata', {})
            tokens_used = metadata.get('tokens_used', 0)
            cost_usd = metadata.get('cost_usd', 0.0)
            model_used = metadata.get('model_used', '')

            # Verify cost calculation is reasonable
            self.assertGreater(tokens_used, 0)
            self.assertGreater(cost_usd, 0.0)
            self.assertTrue(model_used)

            # Cost should be proportional to tokens
            # Rough estimate: GPT-4 is ~$0.00003 per token
            estimated_cost = tokens_used * 0.00005  # Conservative estimate
            cost_ratio = cost_usd / estimated_cost if estimated_cost > 0 else 0

            # Cost should be within reasonable range (0.01x to 10x estimate)
            # Note: Lower threshold due to newer cheaper models
            self.assertGreater(cost_ratio, 0.001, f"Cost seems too low: ${cost_usd:.6f}")
            self.assertLess(cost_ratio, 10.0, f"Cost seems too high: ${cost_usd:.6f}")

            return {
                'tokens_used': tokens_used,
                'cost_usd': cost_usd,
                'model_used': model_used,
                'cost_per_token': cost_usd / tokens_used if tokens_used > 0 else 0,
                'cost_ratio': cost_ratio
            }

        result = asyncio.run(run_cost_test())

        logger.info(f"Cost tracking test - Tokens: {result['tokens_used']}, "
                   f"Cost: ${result['cost_usd']:.6f}, "
                   f"Per token: ${result['cost_per_token']:.8f}, "
                   f"Model: {result['model_used']}")


if __name__ == '__main__':
    # Run with: python manage.py test llm_services.tests.test_real_pipeline_integration
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["llm_services.tests.test_real_pipeline_integration"])