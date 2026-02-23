"""
Unit tests for confidence calculation and thresholds (ft-030 - Anti-Hallucination Improvements).
Tests weighted confidence calculation, tier classification, and flagging logic.

Implements ADR-043: Confidence Thresholds
"""

import pytest
from django.test import TestCase, tag
from typing import Dict, Any


@tag('medium', 'integration', 'generation', 'confidence')
class ConfidenceThresholdsTestCase(TestCase):
    """Test confidence calculation and tier classification"""

    def test_calculate_overall_confidence_weighted_average(self):
        """Test weighted average: extraction 30%, generation 20%, verification 50%"""
        from generation.services.confidence_calculator import calculate_overall_confidence

        extraction_confidence = 0.90
        generation_confidence = 0.85
        verification_confidence = 0.75

        overall = calculate_overall_confidence(
            extraction_confidence=extraction_confidence,
            generation_confidence=generation_confidence,
            verification_confidence=verification_confidence
        )

        # Calculate expected: 0.90*0.3 + 0.85*0.2 + 0.75*0.5 = 0.27 + 0.17 + 0.375 = 0.815
        expected = 0.815
        assert abs(overall - expected) < 0.01, f"Expected {expected}, got {overall}"

    def test_calculate_overall_confidence_high_verification_weight(self):
        """Test that verification has highest weight (50%)"""
        from generation.services.confidence_calculator import calculate_overall_confidence

        # High verification should pull overall up even with low extraction/generation
        result = calculate_overall_confidence(
            extraction_confidence=0.50,
            generation_confidence=0.50,
            verification_confidence=0.95
        )

        # 0.50*0.3 + 0.50*0.2 + 0.95*0.5 = 0.15 + 0.10 + 0.475 = 0.725
        assert result > 0.70, "High verification should significantly boost confidence"

    def test_determine_content_status_high_tier(self):
        """Test HIGH tier classification (confidence ≥ 0.85)"""
        from generation.services.confidence_calculator import determine_content_status

        confidence = 0.90
        status = determine_content_status(confidence)

        assert status['tier'] == 'HIGH'
        assert status['requires_review'] is False
        assert status['is_blocked'] is False
        assert 'auto_approve' in status['flags']

    def test_determine_content_status_medium_tier(self):
        """Test MEDIUM tier classification (0.70 ≤ confidence < 0.85)"""
        from generation.services.confidence_calculator import determine_content_status

        confidence = 0.75
        status = determine_content_status(confidence)

        assert status['tier'] == 'MEDIUM'
        assert status['requires_review'] is False  # Auto-approve but with neutral indicator
        assert status['is_blocked'] is False
        assert 'auto_approve_neutral' in status['flags']

    def test_determine_content_status_low_tier(self):
        """Test LOW tier classification (0.50 ≤ confidence < 0.70)"""
        from generation.services.confidence_calculator import determine_content_status

        confidence = 0.60
        status = determine_content_status(confidence)

        assert status['tier'] == 'LOW'
        assert status['requires_review'] is True  # Flag for review
        assert status['is_blocked'] is False
        assert 'flag_for_review' in status['flags']

    def test_determine_content_status_critical_tier(self):
        """Test CRITICAL tier classification (confidence < 0.50)"""
        from generation.services.confidence_calculator import determine_content_status

        confidence = 0.40
        status = determine_content_status(confidence)

        assert status['tier'] == 'CRITICAL'
        assert status['requires_review'] is True
        assert status['is_blocked'] is True  # Block from finalization
        assert 'block_finalization' in status['flags']

    def test_confidence_threshold_boundaries(self):
        """Test exact threshold boundaries"""
        from generation.services.confidence_calculator import determine_content_status

        # Test boundary cases
        status_085 = determine_content_status(0.85)
        assert status_085['tier'] == 'HIGH'

        status_084 = determine_content_status(0.84)
        assert status_084['tier'] == 'MEDIUM'

        status_070 = determine_content_status(0.70)
        assert status_070['tier'] == 'MEDIUM'

        status_069 = determine_content_status(0.69)
        assert status_069['tier'] == 'LOW'

        status_050 = determine_content_status(0.50)
        assert status_050['tier'] == 'LOW'

        status_049 = determine_content_status(0.49)
        assert status_049['tier'] == 'CRITICAL'

    def test_unsupported_claim_penalty(self):
        """Test that unsupported claims reduce confidence"""
        from generation.services.confidence_calculator import apply_verification_penalty

        base_confidence = 0.85
        unsupported_claim_count = 2
        total_claims = 5

        penalized = apply_verification_penalty(
            base_confidence=base_confidence,
            unsupported_claims=unsupported_claim_count,
            total_claims=total_claims
        )

        # Should apply penalty for unsupported claims
        assert penalized < base_confidence
        # 2 out of 5 unsupported = 40% unsupported rate
        # Should significantly reduce confidence
        assert penalized < 0.70

    def test_high_inferred_ratio_penalty(self):
        """Test that high inferred ratio (>30%) reduces confidence"""
        from generation.services.confidence_calculator import apply_inferred_ratio_penalty

        base_confidence = 0.80
        inferred_ratio = 0.50  # 50% inferred

        penalized = apply_inferred_ratio_penalty(
            base_confidence=base_confidence,
            inferred_ratio=inferred_ratio
        )

        # Should apply penalty for high inferred ratio
        assert penalized < base_confidence
        # 50% inferred is 20% over the 30% threshold
        # Should have noticeable penalty
        assert penalized < 0.75

    def test_no_penalty_for_low_inferred_ratio(self):
        """Test that low inferred ratio (≤30%) does not reduce confidence"""
        from generation.services.confidence_calculator import apply_inferred_ratio_penalty

        base_confidence = 0.80
        inferred_ratio = 0.20  # 20% inferred (below 30% threshold)

        penalized = apply_inferred_ratio_penalty(
            base_confidence=base_confidence,
            inferred_ratio=inferred_ratio
        )

        # No penalty for acceptable inferred ratio
        assert penalized == base_confidence

    def test_achievement_vs_technical_adjustment(self):
        """Test per-content-type confidence adjustments"""
        from generation.services.confidence_calculator import apply_content_type_adjustment

        # Achievement bullets have higher bar
        achievement_conf = apply_content_type_adjustment(
            base_confidence=0.80,
            content_type='achievement',
            has_metrics=True
        )

        # Technical bullets more lenient
        technical_conf = apply_content_type_adjustment(
            base_confidence=0.80,
            content_type='technical',
            has_metrics=False
        )

        # Achievement with metrics should maintain confidence
        assert achievement_conf >= 0.75

        # Technical without metrics should not be penalized as much
        assert technical_conf >= 0.75

    def test_missing_metrics_penalty_for_achievements(self):
        """Test that achievements without metrics get confidence penalty"""
        from generation.services.confidence_calculator import apply_content_type_adjustment

        confidence_with_metrics = apply_content_type_adjustment(
            base_confidence=0.85,
            content_type='achievement',
            has_metrics=True
        )

        confidence_without_metrics = apply_content_type_adjustment(
            base_confidence=0.85,
            content_type='achievement',
            has_metrics=False
        )

        # Achievements without metrics should have lower confidence
        assert confidence_without_metrics < confidence_with_metrics

    def test_full_confidence_pipeline(self):
        """Test complete confidence calculation pipeline"""
        from generation.services.confidence_calculator import (
            calculate_overall_confidence,
            apply_verification_penalty,
            apply_inferred_ratio_penalty,
            apply_content_type_adjustment,
            determine_content_status
        )

        # Step 1: Calculate base confidence
        base = calculate_overall_confidence(
            extraction_confidence=0.85,
            generation_confidence=0.80,
            verification_confidence=0.75
        )

        # Step 2: Apply verification penalty
        after_verification = apply_verification_penalty(
            base_confidence=base,
            unsupported_claims=1,
            total_claims=5
        )

        # Step 3: Apply inferred ratio penalty
        after_inferred = apply_inferred_ratio_penalty(
            base_confidence=after_verification,
            inferred_ratio=0.25
        )

        # Step 4: Apply content type adjustment
        final = apply_content_type_adjustment(
            base_confidence=after_inferred,
            content_type='achievement',
            has_metrics=True
        )

        # Step 5: Determine status
        status = determine_content_status(final)

        # Verify pipeline works end-to-end
        assert 'tier' in status
        assert 'requires_review' in status
        assert isinstance(final, float)
        assert 0.0 <= final <= 1.0

    def test_confidence_never_exceeds_1_0(self):
        """Test that confidence is capped at 1.0"""
        from generation.services.confidence_calculator import calculate_overall_confidence

        # Even with perfect scores, should not exceed 1.0
        result = calculate_overall_confidence(
            extraction_confidence=1.0,
            generation_confidence=1.0,
            verification_confidence=1.0
        )

        assert result <= 1.0

    def test_confidence_never_below_0_0(self):
        """Test that confidence is floored at 0.0"""
        from generation.services.confidence_calculator import apply_verification_penalty

        # Even with severe penalties, should not go below 0.0
        result = apply_verification_penalty(
            base_confidence=0.30,
            unsupported_claims=10,
            total_claims=10
        )

        assert result >= 0.0

    def test_tier_color_mapping(self):
        """Test that each tier has correct color coding"""
        from generation.services.confidence_calculator import determine_content_status

        high_status = determine_content_status(0.90)
        assert high_status['color'] == 'green'

        medium_status = determine_content_status(0.75)
        assert medium_status['color'] == 'blue'

        low_status = determine_content_status(0.60)
        assert low_status['color'] == 'amber'

        critical_status = determine_content_status(0.40)
        assert critical_status['color'] == 'red'

    def test_user_message_generation(self):
        """Test that status includes user-friendly message"""
        from generation.services.confidence_calculator import determine_content_status

        high_status = determine_content_status(0.90)
        assert 'message' in high_status
        assert len(high_status['message']) > 0
        assert 'verified' in high_status['message'].lower() or 'high' in high_status['message'].lower()

        critical_status = determine_content_status(0.40)
        assert 'message' in critical_status
        assert 'review' in critical_status['message'].lower() or 'blocked' in critical_status['message'].lower()
