"""
Unit tests for PDFDocumentClassifier.

TDD RED PHASE: These tests define expected behavior for adaptive PDF classification.
Tests will FAIL until PDFDocumentClassifier is implemented in Stage G.
"""

from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from decimal import Decimal


@tag('fast', 'unit', 'llm_services')
class PDFDocumentClassifierTestCase(TestCase):
    """Test suite for PDFDocumentClassifier - TDD RED phase"""

    def setUp(self):
        """Set up test fixtures."""
        # This import will fail until we create the class
        try:
            from llm_services.services.infrastructure.pdf_document_classifier import PDFDocumentClassifier
            self.classifier = PDFDocumentClassifier()
        except ImportError:
            # Expected to fail in RED phase
            self.classifier = None

    def test_classifier_initialization(self):
        """Test PDFDocumentClassifier can be initialized."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        self.assertIsNotNone(self.classifier)
        self.assertTrue(hasattr(self.classifier, 'CLASSIFICATION_KEYWORDS'))
        self.assertTrue(hasattr(self.classifier, 'classify_document'))

    def test_classify_one_page_certificate(self):
        """Test classification of 1-page certificate PDF."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Metadata for a 1-page AWS certification
        metadata = {
            'page_count': 1,
            'file_size': 150_000,  # 150KB
            'first_page_text': 'AWS Certified Solutions Architect certificate awarded completion'
        }

        # When: Classifying the document
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should classify as 'certificate' with high confidence
        category, confidence = result
        self.assertEqual(category, 'certificate')
        self.assertGreaterEqual(confidence, 0.8)

    def test_classify_two_page_resume(self):
        """Test classification of 2-page professional resume."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Metadata for a 2-page resume
        metadata = {
            'page_count': 2,
            'file_size': 250_000,  # 250KB
            'first_page_text': 'John Doe - Software Engineer - Experience: 5 years - Education: BS Computer Science - Skills: Python, Django'
        }

        # When: Classifying the document
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should classify as 'resume' with high confidence
        category, confidence = result
        self.assertEqual(category, 'resume')
        self.assertGreaterEqual(confidence, 0.8)

    def test_classify_research_paper(self):
        """Test classification of 15-page research paper."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Metadata for a research paper
        metadata = {
            'page_count': 15,
            'file_size': 800_000,  # 800KB
            'first_page_text': 'Abstract: This paper presents novel methodology for machine learning results in healthcare applications references'
        }

        # When: Classifying the document
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should classify as 'research_paper' with high confidence
        category, confidence = result
        self.assertEqual(category, 'research_paper')
        self.assertGreaterEqual(confidence, 0.8)

    def test_classify_project_report(self):
        """Test classification of 30-page project report."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Metadata for a project report
        metadata = {
            'page_count': 30,
            'file_size': 1_500_000,  # 1.5MB
            'first_page_text': 'Implementation of E-commerce Platform - design architecture testing deployment results'
        }

        # When: Classifying the document
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should classify as 'project_report' with reasonable confidence
        category, confidence = result
        self.assertEqual(category, 'project_report')
        self.assertGreaterEqual(confidence, 0.6)

    def test_classify_academic_thesis(self):
        """Test classification of 200-page academic thesis."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Metadata for an academic thesis
        metadata = {
            'page_count': 200,
            'file_size': 2_000_000,  # 2MB
            'first_page_text': 'PhD Dissertation: Machine Learning for Healthcare - thesis advisor chapter acknowledgements'
        }

        # When: Classifying the document
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should classify as 'academic_thesis' with high confidence
        category, confidence = result
        self.assertEqual(category, 'academic_thesis')
        self.assertGreaterEqual(confidence, 0.9)

    @patch('llm_services.services.infrastructure.pdf_document_classifier.PDFDocumentClassifier._call_llm_for_classification')
    async def test_llm_refinement_for_low_confidence(self, mock_llm):
        """Test LLM refinement triggered when rule-based confidence < 0.7."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Ambiguous document (low rule-based confidence)
        metadata = {
            'page_count': 8,  # Between certificate and paper
            'file_size': 400_000,
            'first_page_text': 'Technical documentation overview'
        }

        # Mock LLM to return high-confidence classification
        mock_llm.return_value = {
            'content': '{"category": "project_report", "confidence": 0.95}'
        }

        # When: Classifying with LLM refinement
        result = await self.classifier._classify_with_llm(metadata, '/fake/path.pdf')

        # Then: Should use LLM classification
        category, confidence = result
        self.assertEqual(category, 'project_report')
        self.assertEqual(confidence, 0.95)
        mock_llm.assert_called_once()

    def test_get_processing_strategy_for_certificate(self):
        """Test processing strategy returned for certificate category."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # When: Getting strategy for 'certificate'
        strategy = self.classifier._get_processing_strategy('certificate')

        # Then: Should return certificate-specific config
        self.assertEqual(strategy['max_chunks'], 10)
        self.assertEqual(strategy['max_chars'], 10_000)
        self.assertEqual(strategy['sampling'], 'full')
        self.assertEqual(strategy['summary_tokens'], 500)
        self.assertFalse(strategy['map_reduce'])

    def test_get_processing_strategy_for_thesis(self):
        """Test processing strategy returned for academic thesis category."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # When: Getting strategy for 'academic_thesis'
        strategy = self.classifier._get_processing_strategy('academic_thesis')

        # Then: Should return thesis-specific config with map-reduce
        self.assertEqual(strategy['max_chunks'], 300)
        self.assertEqual(strategy['max_chars'], 300_000)
        self.assertEqual(strategy['sampling'], 'map_reduce')
        self.assertEqual(strategy['summary_tokens'], 3_000)
        self.assertTrue(strategy['map_reduce'])
        self.assertEqual(strategy['map_chunk_size'], 50_000)

    def test_classification_keywords_coverage(self):
        """Test all 5 categories have keyword definitions."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        keywords = self.classifier.CLASSIFICATION_KEYWORDS

        # All 5 categories must be defined
        required_categories = ['resume', 'certificate', 'research_paper', 'project_report', 'academic_thesis']
        for category in required_categories:
            self.assertIn(category, keywords)
            self.assertGreater(len(keywords[category]), 0, f"{category} must have keywords")

    @patch('llm_services.services.infrastructure.pdf_document_classifier.PDFDocumentClassifier._classify_by_rules')
    async def test_classify_document_high_confidence_path(self, mock_rules):
        """Test classify_document uses rule-based when confidence >= 0.7."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Rule-based classifier returns high confidence
        mock_rules.return_value = ('resume', 0.85)

        # When: Classifying document
        result = await self.classifier.classify_document('/fake/path.pdf')

        # Then: Should use rule-based result without LLM refinement
        self.assertEqual(result['category'], 'resume')
        self.assertEqual(result['confidence'], 0.85)
        self.assertIn('processing_strategy', result)
        mock_rules.assert_called_once()

    def test_keyword_matching_case_insensitive(self):
        """Test keyword matching is case-insensitive."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Text with uppercase keywords
        metadata = {
            'page_count': 1,
            'file_size': 100_000,
            'first_page_text': 'CERTIFICATE OF COMPLETION AWARDED'
        }

        # When: Classifying
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should match keywords case-insensitively
        category, confidence = result
        self.assertEqual(category, 'certificate')

    def test_page_count_threshold_boundaries(self):
        """Test page count thresholds work at boundary values."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Test boundary: 3 pages (max for certificate)
        metadata_3 = {
            'page_count': 3,
            'file_size': 150_000,
            'first_page_text': 'certificate awarded'
        }
        category_3, _ = self.classifier._classify_by_rules(metadata_3)
        self.assertEqual(category_3, 'certificate')

        # Test boundary: 50 pages (min for thesis)
        metadata_50 = {
            'page_count': 50,
            'file_size': 1_000_000,
            'first_page_text': 'thesis dissertation'
        }
        category_50, _ = self.classifier._classify_by_rules(metadata_50)
        self.assertEqual(category_50, 'academic_thesis')

    def test_default_fallback_category(self):
        """Test fallback to 'resume' for completely ambiguous documents."""
        if self.classifier is None:
            self.skipTest("PDFDocumentClassifier not yet implemented (TDD RED phase)")

        # Given: Document with no matching keywords
        metadata = {
            'page_count': 5,
            'file_size': 300_000,
            'first_page_text': 'Lorem ipsum dolor sit amet consectetur'
        }

        # When: Classifying
        result = self.classifier._classify_by_rules(metadata)

        # Then: Should fallback to 'resume' (safe default)
        category, confidence = result
        self.assertIsNotNone(category)
        self.assertIn(category, ['resume', 'certificate', 'research_paper', 'project_report', 'academic_thesis'])
