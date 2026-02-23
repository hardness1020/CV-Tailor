"""
Confidence Calculator (ft-030 - Anti-Hallucination Improvements).

Calculates overall confidence scores and determines content status/tier classification.
Implements multi-signal confidence calculation with weighted averages and penalties.

Implements ADR-043: Confidence Thresholds
"""

import logging
from typing import Dict, Any, List
from django.conf import settings

logger = logging.getLogger(__name__)


# Confidence tier thresholds (from ADR-043)
# Can be overridden via environment variables (FT030_THRESHOLD_HIGH, etc.)
def _get_threshold_high() -> float:
    return getattr(settings, 'FT030_THRESHOLDS', {}).get('high', 0.85)

def _get_threshold_medium() -> float:
    return getattr(settings, 'FT030_THRESHOLDS', {}).get('medium', 0.70)

def _get_threshold_low() -> float:
    return getattr(settings, 'FT030_THRESHOLDS', {}).get('low', 0.50)

THRESHOLD_HIGH = _get_threshold_high()       # ≥ 0.85: HIGH tier (auto-approve)
THRESHOLD_MEDIUM = _get_threshold_medium()   # ≥ 0.70: MEDIUM tier (auto-approve with neutral indicator)
THRESHOLD_LOW = _get_threshold_low()         # ≥ 0.50: LOW tier (flag for review)
# < 0.50: CRITICAL tier (block from finalization)

# Confidence weights (from ADR-043)
WEIGHT_EXTRACTION = 0.30    # 30% weight for extraction confidence
WEIGHT_GENERATION = 0.20    # 20% weight for generation confidence
WEIGHT_VERIFICATION = 0.50  # 50% weight for verification confidence (highest)

# Penalty thresholds
INFERRED_RATIO_THRESHOLD = getattr(settings, 'FT030_INFERRED_RATIO_THRESHOLD', 0.30)  # >30% inferred items triggers penalty


def calculate_overall_confidence(
    extraction_confidence: float,
    generation_confidence: float,
    verification_confidence: float
) -> float:
    """
    Calculate weighted average confidence from multiple signals.

    Weights (from ADR-043):
    - Extraction: 30% - Source quality and attribution coverage
    - Generation: 20% - Content quality and validation scores
    - Verification: 50% - Fact-checking results (most important)

    Args:
        extraction_confidence: 0.0-1.0 confidence from extraction phase
        generation_confidence: 0.0-1.0 confidence from generation phase
        verification_confidence: 0.0-1.0 confidence from verification phase

    Returns:
        Weighted average confidence (0.0-1.0)
    """
    overall = (
        extraction_confidence * WEIGHT_EXTRACTION +
        generation_confidence * WEIGHT_GENERATION +
        verification_confidence * WEIGHT_VERIFICATION
    )

    # Ensure confidence stays within bounds
    overall = max(0.0, min(1.0, overall))

    logger.debug(
        f"[ft-030] Calculated overall confidence: {overall:.3f} "
        f"(extraction={extraction_confidence:.2f}*{WEIGHT_EXTRACTION}, "
        f"generation={generation_confidence:.2f}*{WEIGHT_GENERATION}, "
        f"verification={verification_confidence:.2f}*{WEIGHT_VERIFICATION})"
    )

    return overall


def apply_verification_penalty(
    base_confidence: float,
    unsupported_claims: int,
    total_claims: int
) -> float:
    """
    Apply penalty for unsupported claims detected by verification.

    Penalty formula:
    - Each unsupported claim reduces confidence proportionally
    - Penalty = (unsupported_claims / total_claims) * 0.5

    Args:
        base_confidence: Starting confidence
        unsupported_claims: Number of claims marked UNSUPPORTED
        total_claims: Total number of claims

    Returns:
        Confidence after penalty (0.0-1.0)
    """
    if total_claims == 0:
        return base_confidence

    unsupported_ratio = unsupported_claims / total_claims
    penalty = unsupported_ratio * 0.5  # Up to 50% penalty for all unsupported

    penalized = base_confidence - penalty
    penalized = max(0.0, min(1.0, penalized))

    if penalty > 0:
        logger.info(
            f"[ft-030] Applied verification penalty: -{penalty:.3f} "
            f"({unsupported_claims}/{total_claims} unsupported claims)"
        )

    return penalized


def apply_inferred_ratio_penalty(
    base_confidence: float,
    inferred_ratio: float
) -> float:
    """
    Apply penalty for high inferred item ratio (>30%).

    Inferred items are those with confidence < 0.5 during extraction,
    indicating they were guessed rather than directly found in source.

    Penalty formula:
    - No penalty if inferred_ratio ≤ 30%
    - Penalty = (inferred_ratio - 0.30) * 0.5 if > 30%

    Args:
        base_confidence: Starting confidence
        inferred_ratio: Ratio of inferred items (0.0-1.0)

    Returns:
        Confidence after penalty (0.0-1.0)
    """
    if inferred_ratio <= INFERRED_RATIO_THRESHOLD:
        return base_confidence  # No penalty for acceptable inferred ratio

    excess_ratio = inferred_ratio - INFERRED_RATIO_THRESHOLD
    penalty = excess_ratio * 0.5  # Up to 35% penalty for 100% inferred

    penalized = base_confidence - penalty
    penalized = max(0.0, min(1.0, penalized))

    logger.info(
        f"[ft-030] Applied inferred ratio penalty: -{penalty:.3f} "
        f"(inferred_ratio={inferred_ratio:.2%} exceeds {INFERRED_RATIO_THRESHOLD:.0%} threshold)"
    )

    return penalized


def apply_content_type_adjustment(
    base_confidence: float,
    content_type: str,
    has_metrics: bool
) -> float:
    """
    Apply content-type-specific confidence adjustments.

    Content types:
    - achievement: Requires metrics/quantification (higher bar)
    - technical: Technical skills/tools (more lenient)
    - responsibility: Role descriptions (moderate bar)

    Args:
        base_confidence: Starting confidence
        content_type: 'achievement', 'technical', or 'responsibility'
        has_metrics: Whether content includes quantified metrics

    Returns:
        Adjusted confidence (0.0-1.0)
    """
    if content_type == 'achievement':
        if not has_metrics:
            # Achievement without metrics should have lower confidence
            penalty = 0.10
            adjusted = base_confidence - penalty
            logger.debug(
                f"[ft-030] Achievement without metrics: -{penalty:.2f} penalty"
            )
        else:
            # Achievement with metrics - no adjustment needed
            adjusted = base_confidence
    elif content_type == 'technical':
        # Technical content is more straightforward - slight boost if very low
        if base_confidence < 0.60:
            boost = 0.05
            adjusted = base_confidence + boost
            logger.debug(
                f"[ft-030] Technical content boost: +{boost:.2f}"
            )
        else:
            adjusted = base_confidence
    else:
        # Default: no adjustment
        adjusted = base_confidence

    # Ensure bounds
    adjusted = max(0.0, min(1.0, adjusted))

    return adjusted


def determine_content_status(confidence: float) -> Dict[str, Any]:
    """
    Determine content status and tier based on confidence threshold.

    Tiers (from ADR-043):
    - HIGH (≥0.85): Auto-approve, green indicator
    - MEDIUM (0.70-0.84): Auto-approve with neutral indicator (blue)
    - LOW (0.50-0.69): Flag for review, amber warning
    - CRITICAL (<0.50): Block from finalization, red alert

    Args:
        confidence: Overall confidence score (0.0-1.0)

    Returns:
        Dict with tier, flags, colors, and user message
    """
    if confidence >= THRESHOLD_HIGH:
        tier = 'HIGH'
        color = 'green'
        requires_review = False
        is_blocked = False
        flags = ['auto_approve']
        message = "High confidence - content verified against sources"

    elif confidence >= THRESHOLD_MEDIUM:
        tier = 'MEDIUM'
        color = 'blue'
        requires_review = False
        is_blocked = False
        flags = ['auto_approve_neutral']
        message = "Medium confidence - content appears reasonable"

    elif confidence >= THRESHOLD_LOW:
        tier = 'LOW'
        color = 'amber'
        requires_review = True
        is_blocked = False
        flags = ['flag_for_review']
        message = "Low confidence - please review for accuracy"

    else:  # < THRESHOLD_LOW
        tier = 'CRITICAL'
        color = 'red'
        requires_review = True
        is_blocked = True
        flags = ['block_finalization', 'requires_edit']
        message = "Critical confidence - blocked from use, requires review and editing"

    status = {
        'tier': tier,
        'confidence': confidence,
        'requires_review': requires_review,
        'is_blocked': is_blocked,
        'flags': flags,
        'color': color,
        'message': message
    }

    logger.info(
        f"[ft-030] Content status: {tier} tier (confidence={confidence:.2f}, "
        f"requires_review={requires_review}, blocked={is_blocked})"
    )

    return status


def calculate_bullet_confidence(
    extraction_data: Dict[str, Any],
    generation_data: Dict[str, Any],
    verification_data: Dict[str, Any],
    content_type: str = 'achievement'
) -> Dict[str, Any]:
    """
    Complete confidence calculation pipeline for a bullet point.

    Orchestrates all confidence calculations:
    1. Calculate base confidence from three signals
    2. Apply verification penalty (unsupported claims)
    3. Apply inferred ratio penalty (>30% inferred)
    4. Apply content type adjustment
    5. Determine final status/tier

    Args:
        extraction_data: Dict with 'confidence', 'inferred_ratio'
        generation_data: Dict with 'confidence'
        verification_data: Dict with 'confidence', 'unsupported_claims', 'total_claims'
        content_type: 'achievement', 'technical', or 'responsibility'

    Returns:
        Dict with final confidence, tier, status, and all intermediate values
    """
    # Step 1: Calculate base confidence
    base_confidence = calculate_overall_confidence(
        extraction_confidence=extraction_data.get('confidence', 0.5),
        generation_confidence=generation_data.get('confidence', 0.5),
        verification_confidence=verification_data.get('confidence', 0.5)
    )

    # Step 2: Apply verification penalty
    after_verification = apply_verification_penalty(
        base_confidence=base_confidence,
        unsupported_claims=verification_data.get('unsupported_claims', 0),
        total_claims=verification_data.get('total_claims', 1)
    )

    # Step 3: Apply inferred ratio penalty
    after_inferred = apply_inferred_ratio_penalty(
        base_confidence=after_verification,
        inferred_ratio=extraction_data.get('inferred_ratio', 0.0)
    )

    # Step 4: Apply content type adjustment
    has_metrics = any(
        metric in str(generation_data.get('text', '')).lower()
        for metric in ['%', 'x', 'million', 'thousand', '$']
    )

    final_confidence = apply_content_type_adjustment(
        base_confidence=after_inferred,
        content_type=content_type,
        has_metrics=has_metrics
    )

    # Step 5: Determine status
    status = determine_content_status(final_confidence)

    # Combine all information
    result = {
        **status,
        'confidence_breakdown': {
            'base': base_confidence,
            'after_verification_penalty': after_verification,
            'after_inferred_penalty': after_inferred,
            'final': final_confidence
        },
        'signals': {
            'extraction': extraction_data.get('confidence', 0.5),
            'generation': generation_data.get('confidence', 0.5),
            'verification': verification_data.get('confidence', 0.5)
        }
    }

    logger.info(
        f"[ft-030] Bullet confidence calculation complete: "
        f"{final_confidence:.3f} ({status['tier']} tier)"
    )

    return result
