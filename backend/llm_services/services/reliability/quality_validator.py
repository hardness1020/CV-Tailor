"""
Enrichment Quality Validator

Validates enrichment quality before marking as "completed".
Implements quality gates from adr-20251003-artifact-enrichment-quality-issues.md
"""

from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentValidationResult:
    """
    Validation result for enriched artifact.

    Attributes:
        passed: Overall validation passed (no blocking errors)
        errors: Blocking issues that cause validation to fail
        warnings: Quality concerns that don't block completion
        quality_score: Overall quality score (0-1, same as processing_confidence)
    """
    passed: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float


class EnrichmentQualityValidator:
    """
    Validates enrichment quality using multi-criteria thresholds.

    Quality Thresholds:
    - FAIL if processing_confidence < 0.5
    - FAIL if unified_description < 100 chars (likely fallback)
    - FAIL if all source extractions failed (0% success rate)
    - WARN if extraction success rate < 50%
    - WARN if no technologies extracted
    - WARN if no achievements extracted

    Usage:
        validator = EnrichmentQualityValidator()
        result = validator.validate(enriched_result)
        if not result.passed:
            print(f"Validation failed: {result.errors}")
    """

    # Thresholds
    MIN_CONFIDENCE = 0.6  # Raised from 0.5 to ensure higher quality
    MIN_DESCRIPTION_LENGTH = 100
    MIN_EXTRACTION_SUCCESS_RATE = 0.5
    MIN_SOURCES_REQUIRED = 1  # At least one evidence source must be provided

    def validate(self, enriched_result) -> EnrichmentValidationResult:
        """
        Validate enrichment quality.

        Args:
            enriched_result: EnrichedArtifactResult from ArtifactEnrichmentService

        Returns:
            EnrichmentValidationResult with errors and warnings
        """
        # Log input for debugging
        logger.info(
            f"[Quality Validation] Validating artifact {enriched_result.artifact_id}: "
            f"confidence={enriched_result.processing_confidence:.2f}, "
            f"description_length={len(enriched_result.unified_description)}, "
            f"sources_successful={enriched_result.sources_successful}/"
            f"{enriched_result.sources_processed}, "
            f"technologies={len(enriched_result.enriched_technologies)}, "
            f"achievements={len(enriched_result.enriched_achievements)}"
        )

        errors = []
        warnings = []

        # Check minimum sources requirement
        if enriched_result.sources_processed < self.MIN_SOURCES_REQUIRED:
            errors.append(
                f"No evidence sources processed - enrichment requires at least "
                f"{self.MIN_SOURCES_REQUIRED} source(s)"
            )
            # Early return - no point checking other metrics
            return EnrichmentValidationResult(
                passed=False,
                errors=errors,
                warnings=warnings,
                quality_score=0.0
            )

        # Check extraction success rate
        if enriched_result.sources_processed > 0:
            success_rate = enriched_result.sources_successful / enriched_result.sources_processed

            if success_rate == 0:
                errors.append("All source extractions failed (0% success rate)")
            elif success_rate < self.MIN_EXTRACTION_SUCCESS_RATE:
                warnings.append(
                    f"Low extraction success: {success_rate:.0%} "
                    f"({enriched_result.sources_successful}/{enriched_result.sources_processed} sources)"
                )

        # Check processing confidence
        if enriched_result.processing_confidence < self.MIN_CONFIDENCE:
            errors.append(
                f"Processing confidence too low: {enriched_result.processing_confidence:.0%} "
                f"(minimum: {self.MIN_CONFIDENCE:.0%})"
            )

        # Check description quality
        if len(enriched_result.unified_description) < self.MIN_DESCRIPTION_LENGTH:
            errors.append(
                f"Description too short ({len(enriched_result.unified_description)} chars) - "
                f"likely fallback content (minimum: {self.MIN_DESCRIPTION_LENGTH} chars)"
            )

        # Check extracted data (warnings only)
        if len(enriched_result.enriched_technologies) == 0:
            warnings.append("No technologies extracted from evidence sources")

        if len(enriched_result.enriched_achievements) == 0:
            warnings.append("No achievements extracted from evidence sources")

        passed = len(errors) == 0

        # Log validation result
        if not passed:
            logger.warning(
                f"[Quality Validation] FAILED for artifact {enriched_result.artifact_id}: "
                f"errors={errors}, warnings={warnings}"
            )
        elif warnings:
            logger.info(
                f"[Quality Validation] PASSED with warnings for artifact {enriched_result.artifact_id}: "
                f"warnings={warnings}"
            )
        else:
            logger.info(
                f"[Quality Validation] PASSED for artifact {enriched_result.artifact_id} "
                f"with no issues"
            )

        return EnrichmentValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            quality_score=enriched_result.processing_confidence
        )
