"""
Unit tests for Enrichment Quality Validator (reliability layer).

Following TDD: These tests define expected behavior before implementation.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from django.test import TestCase, tag

from llm_services.services.reliability.quality_validator import (
    EnrichmentQualityValidator,
    EnrichmentValidationResult
)


# Mock EnrichedArtifactResult for testing
@dataclass
class MockEnrichedArtifactResult:
    """Mock result for testing quality validator"""
    artifact_id: int
    unified_description: str = ""
    enriched_technologies: List[str] = field(default_factory=list)
    enriched_achievements: List[str] = field(default_factory=list)
    processing_confidence: float = 0.0
    sources_processed: int = 0
    sources_successful: int = 0


@tag('fast', 'unit', 'llm_services')
class EnrichmentQualityValidatorTestCase(TestCase):
    """Test quality validation for enriched artifacts"""

    def setUp(self):
        self.validator = EnrichmentQualityValidator()

    def test_validation_passes_with_good_quality(self):
        """
        Given: High-quality enrichment result
        - confidence = 0.8 (>= 0.5 threshold)
        - description = 200 chars (>= 100 threshold)
        - 3/3 sources successful (100% success rate)

        Expect: Validation passes with no errors or warnings
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,  # 200 characters
            enriched_technologies=["Python", "Django", "React"],
            enriched_achievements=["Built feature X", "Improved performance"],
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertTrue(validation_result.passed)
        self.assertEqual(validation_result.errors, [])
        self.assertEqual(validation_result.warnings, [])
        self.assertEqual(validation_result.quality_score, 0.8)

    def test_validation_fails_low_confidence(self):
        """
        Given: Enrichment result with low confidence
        - confidence = 0.3 (< 0.5 threshold)

        Expect: Validation fails with error message about low confidence
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            processing_confidence=0.3,  # Below threshold
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertFalse(validation_result.passed)
        self.assertEqual(len(validation_result.errors), 1)
        self.assertIn("Processing confidence too low: 30%", validation_result.errors[0])
        self.assertIn("minimum: 60%", validation_result.errors[0])

    def test_validation_fails_short_description(self):
        """
        Given: Enrichment result with very short description
        - description = "Test." (5 chars, < 100 threshold)

        Expect: Validation fails with error about fallback content
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="Test.",  # Only 5 characters
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertFalse(validation_result.passed)
        self.assertEqual(len(validation_result.errors), 1)
        self.assertIn("Description too short (5 chars)", validation_result.errors[0])
        self.assertIn("likely fallback content", validation_result.errors[0])

    def test_validation_fails_all_extractions_failed(self):
        """
        Given: Enrichment result where all source extractions failed
        - sources_processed = 3
        - sources_successful = 0 (0% success rate)

        Expect: Validation fails with error about extraction failure
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=0  # All failed
        )

        validation_result = self.validator.validate(result)

        self.assertFalse(validation_result.passed)
        self.assertEqual(len(validation_result.errors), 1)
        self.assertIn("All source extractions failed", validation_result.errors[0])
        self.assertIn("0% success rate", validation_result.errors[0])

    def test_validation_warns_low_extraction_rate(self):
        """
        Given: Enrichment result with low extraction success rate
        - sources_processed = 3
        - sources_successful = 1 (33% success rate, < 50% threshold)

        Expect: Validation passes but includes warning about low success rate
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            enriched_technologies=["Python"],  # Has some technologies
            enriched_achievements=["Built X"],  # Has some achievements
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=1  # 33% success rate
        )

        validation_result = self.validator.validate(result)

        self.assertTrue(validation_result.passed)
        self.assertEqual(validation_result.errors, [])
        self.assertEqual(len(validation_result.warnings), 1)
        self.assertIn("Low extraction success: 33%", validation_result.warnings[0])
        self.assertIn("(1/3 sources)", validation_result.warnings[0])

    def test_validation_warns_no_technologies(self):
        """
        Given: Enrichment result with no technologies extracted
        - enriched_technologies = []

        Expect: Validation passes but includes warning about missing technologies
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            enriched_technologies=[],  # Empty
            enriched_achievements=["Built X"],  # Has achievements (to isolate this test)
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertTrue(validation_result.passed)
        self.assertEqual(validation_result.errors, [])
        self.assertEqual(len(validation_result.warnings), 1)
        self.assertIn("No technologies extracted", validation_result.warnings[0])

    def test_validation_warns_no_achievements(self):
        """
        Given: Enrichment result with no achievements extracted
        - enriched_achievements = []

        Expect: Validation passes but includes warning about missing achievements
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            enriched_technologies=["Python"],  # Has technologies (to isolate this test)
            enriched_achievements=[],  # Empty
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertTrue(validation_result.passed)
        self.assertEqual(validation_result.errors, [])
        self.assertEqual(len(validation_result.warnings), 1)
        self.assertIn("No achievements extracted", validation_result.warnings[0])

    def test_validation_multiple_errors(self):
        """
        Given: Enrichment result with multiple quality issues
        - Low confidence (0.3)
        - Short description (5 chars)
        - All extractions failed (0/3)

        Expect: Validation fails with all three error messages
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="Test.",  # Short
            processing_confidence=0.3,  # Low
            sources_processed=3,
            sources_successful=0  # All failed
        )

        validation_result = self.validator.validate(result)

        self.assertFalse(validation_result.passed)
        self.assertEqual(len(validation_result.errors), 3)
        # Check all three errors are present
        errors_str = ' '.join(validation_result.errors)
        self.assertIn("All source extractions failed", errors_str)
        self.assertIn("Processing confidence too low", errors_str)
        self.assertIn("Description too short", errors_str)

    def test_validation_passes_with_warnings(self):
        """
        Given: Good quality enrichment but missing optional data
        - Good confidence (0.8)
        - Good description (200 chars)
        - Good extraction rate (3/3)
        - But: No technologies or achievements

        Expect: Validation passes with warnings (not errors)
        """
        result = MockEnrichedArtifactResult(
            artifact_id=1,
            unified_description="A" * 200,
            enriched_technologies=[],  # Empty
            enriched_achievements=[],  # Empty
            processing_confidence=0.8,
            sources_processed=3,
            sources_successful=3
        )

        validation_result = self.validator.validate(result)

        self.assertTrue(validation_result.passed)
        self.assertEqual(validation_result.errors, [])
        self.assertEqual(len(validation_result.warnings), 2)
        warnings_str = ' '.join(validation_result.warnings)
        self.assertIn("No technologies extracted", warnings_str)
        self.assertIn("No achievements extracted", warnings_str)
