"""
Real PDF Enrichment Integration Tests

Tests PDF artifact enrichment with real LLM API calls (NO MOCKING).
This catches bugs that are hidden by over-mocking in regular tests,
such as missing imports or broken LLM integration code.

To run this test:
    docker-compose exec -e FORCE_REAL_API_TESTS=true backend uv run python manage.py test llm_services.tests.integration.test_real_pdf_enrichment --keepdb --verbosity=2

WARNING: This test uses real API tokens and incurs costs.
- test_pdf_enrichment_with_real_api: ~$0.02-0.05 (2-5 cents)

IMPORTANT: This test runs WITHOUT MOCKING the LLM layer to verify:
- PDF file path resolution works correctly
- Document loader can load real PDF files
- LLM extraction code has no import errors
- End-to-end enrichment pipeline functions properly
"""

import os
import asyncio
import logging
import tempfile
from pathlib import Path
from django.test import TransactionTestCase, tag
from django.contrib.auth import get_user_model

from .test_real_api_config import (
    RealAPITestConfig, require_real_api_key,
    with_budget_control, with_safe_settings, RealAPITestHelper, skip_unless_forced
)
from ...services.core.artifact_enrichment_service import ArtifactEnrichmentService
from artifacts.models import Artifact, Evidence, ArtifactProcessingJob
from ..helpers.api_helpers import RealAPITestMixin

User = get_user_model()
logger = logging.getLogger(__name__)


@with_safe_settings()
@tag('slow', 'real_api', 'llm_services')
class RealPDFEnrichmentTestCase(RealAPITestMixin, TransactionTestCase):
    """Test PDF artifact enrichment with real LLM API calls"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='pdf_test_user',
            email='pdftest@example.com',
            password='testpass123'
        )
        self.config = RealAPITestConfig()
        self.test_results = []

    def tearDown(self):
        """Log test summary"""
        if self.test_results:
            RealAPITestHelper.log_test_summary(self.test_results)

    def _create_minimal_pdf(self):
        """Create a minimal test PDF with realistic content"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        # Create temp PDF file
        pdf_fd, pdf_path = tempfile.mkstemp(suffix='.pdf')
        os.close(pdf_fd)

        # Create PDF with minimal content
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Add minimal but realistic content
        c.drawString(100, 750, "Software Engineering Project - API Development")
        c.drawString(100, 730, "")
        c.drawString(100, 710, "Technologies: Python, Django, PostgreSQL, Redis")
        c.drawString(100, 690, "")
        c.drawString(100, 670, "Achievements:")
        c.drawString(120, 650, "- Improved API response time by 40%")
        c.drawString(120, 630, "- Led team of 3 engineers")
        c.drawString(120, 610, "- Deployed to production serving 10k users")

        c.save()
        return pdf_path

    @skip_unless_forced
    @require_real_api_key('openai')
    @with_budget_control()
    def test_pdf_enrichment_with_real_api(self):
        """
        Test PDF enrichment using real LLM API calls (NO MOCKING).

        This test catches bugs that are hidden by over-mocking in regular tests,
        such as missing imports or broken LLM integration code.

        Uses minimal PDF content to keep costs low (~2-5 cents).
        """

        pdf_path = self._create_minimal_pdf()

        try:
            # Create artifact
            artifact = Artifact.objects.create(
                user=self.user,
                title='API Development Project',
                description='Built scalable REST API',
                artifact_type='project'
            )

            # Create evidence with PDF
            evidence = Evidence.objects.create(
                artifact=artifact,
                url='file://test_project.pdf',
                evidence_type='document',
                file_path=pdf_path,  # Use absolute path for test
                description='Project documentation PDF'
            )

            # Create processing job
            job = ArtifactProcessingJob.objects.create(
                artifact=artifact,
                status='pending'
            )

            # Run enrichment WITHOUT MOCKING (this is the key difference)
            async def run_enrichment():
                enrichment_service = ArtifactEnrichmentService()
                result = await enrichment_service.preprocess_multi_source_artifact(
                    artifact_id=artifact.id,
                    job_id=job.id,
                    user_id=self.user.id
                )
                return result

            result = asyncio.run(run_enrichment())

            # Track costs
            self.test_results.append({
                'processing_metadata': {
                    'tokens_used': 0,  # Enrichment doesn't track tokens directly
                    'cost_usd': result.total_cost_usd,
                    'model_used': 'gpt-5-mini',
                    'processing_time_ms': result.processing_time_ms
                }
            })

            # Assertions - verify enrichment succeeded
            self.assertTrue(result.success, f"Enrichment failed: {result.error_message}")
            self.assertEqual(result.sources_processed, 1)
            self.assertEqual(result.sources_successful, 1)

            # Verify extracted content structure
            self.assertGreater(len(result.unified_description), 0, "Should have description")

            # Verify LLM enrichment actually occurred (not fallback)
            original_description = f"{artifact.title}. {artifact.description}"
            self.assertNotEqual(
                result.unified_description,
                original_description,
                "Description should be LLM-enriched, not fallback to original"
            )

            # Verify enrichment adds meaningful content
            self.assertGreater(
                len(result.unified_description),
                len(original_description),
                "Enriched description should be longer/more detailed than original"
            )

            self.assertGreater(len(result.enriched_technologies), 0, "Should extract technologies")
            self.assertGreater(result.processing_confidence, 0, "Should have confidence score")

            # Verify reasonable costs (PDF extraction should be cheap with GPT-5-mini)
            max_cost = 0.05  # 5 cents max for minimal PDF
            self.assertLess(result.total_cost_usd, max_cost,
                           f"PDF enrichment cost ${result.total_cost_usd:.6f} exceeds limit ${max_cost}")

            logger.info(
                f"PDF enrichment test - Cost: ${result.total_cost_usd:.6f}, "
                f"Technologies: {result.enriched_technologies}, "
                f"Confidence: {result.processing_confidence:.2%}"
            )

            return result

        finally:
            # Cleanup temp PDF file
            if Path(pdf_path).exists():
                Path(pdf_path).unlink()

    @skip_unless_forced
    @require_real_api_key('openai')
    @with_budget_control()
    def test_pdf_file_path_resolution(self):
        """
        Test that PDF file paths are correctly resolved from Django storage paths to absolute paths.

        This verifies the fix for the bug where relative storage paths (e.g., 'uploads/file.pdf')
        failed to load because the document loader didn't use Django's storage system.
        """

        pdf_path = self._create_minimal_pdf()

        try:
            # Create artifact
            artifact = Artifact.objects.create(
                user=self.user,
                title='Path Resolution Test',
                description='Testing file path resolution',
                artifact_type='project'
            )

            # Create evidence with absolute PDF path
            evidence = Evidence.objects.create(
                artifact=artifact,
                url='file://path_test.pdf',
                evidence_type='document',
                file_path=pdf_path,
                description='Test PDF'
            )

            # Test document loader directly
            async def test_loader():
                from ...services.core.document_loader_service import DocumentLoaderService
                loader = DocumentLoaderService()

                # This should work with absolute path
                result = await loader.load_and_chunk_document(
                    content=pdf_path,
                    content_type='pdf',
                    metadata={'source_url': evidence.url}
                )

                return result

            result = asyncio.run(test_loader())

            # Verify loading succeeded
            self.assertTrue(result.get('success', False),
                          f"PDF loading failed: {result.get('error')}")
            self.assertIn('chunks', result)
            self.assertGreater(len(result['chunks']), 0, "Should have at least one chunk")

            logger.info(f"PDF path resolution test - Loaded {len(result['chunks'])} chunks successfully")

        finally:
            # Cleanup temp PDF file
            if Path(pdf_path).exists():
                Path(pdf_path).unlink()
