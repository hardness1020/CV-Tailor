# ADR-043: Confidence Threshold Policy for Content Review

**File:** docs/adrs/adr-043-confidence-thresholds.md
**Status:** Draft
**Date:** 2025-11-04
**Decision Makers:** Engineering, Product, ML Team
**Related:** PRD v1.4.0, spec-llm.md v4.0.0, ft-030-anti-hallucination-improvements.md, adr-041, adr-042

## Context

With source attribution (ADR-041) and verification service (ADR-042) in place, we need to define **when** content should be flagged for manual review based on confidence scores.

**Problem 1: No Clear Quality Gates**
- Current system has confidence scores but no actionable thresholds
- All content returned to users regardless of quality
- No mechanism to prevent low-confidence content from being finalized
- Users cannot distinguish high-quality vs. uncertain content

**Problem 2: Balance Precision vs. Recall**
- Too strict threshold: Flag too many valid items → user fatigue, slow workflow
- Too lenient threshold: Let hallucinations through → defeats purpose
- Need data-driven approach to find optimal balance
- Different content types may need different thresholds

**Problem 3: Multiple Confidence Signals**
- Extraction confidence (source attribution quality)
- Generation confidence (LLM self-assessment)
- Verification confidence (fact-checking results)
- How to combine these into single decision?

**Current State:**
- Confidence scores exist but unused for decision-making
- No user-facing confidence indicators
- No review workflow for flagged content
- No data on optimal threshold values

**Requirements from PRD v1.4.0:**
- Hallucination rate ≤5%
- User acceptance rate ≥80% for flagged items
- Confidence threshold policy documented and enforced

## Decision

Implement a **multi-tier confidence threshold policy** with different treatment based on confidence level:

### Confidence Tiers

```python
class ConfidenceTier(Enum):
    HIGH = "high"        # ≥0.85: Auto-approve, show positive indicator
    MEDIUM = "medium"    # 0.70-0.84: Auto-approve, show neutral indicator
    LOW = "low"          # 0.50-0.69: FLAG for manual review
    CRITICAL = "critical" # <0.50: BLOCK, require re-generation or manual edit

# Thresholds
CONFIDENCE_THRESHOLDS = {
    'auto_approve': 0.70,      # Content passes without review
    'flag_for_review': 0.50,   # Content flagged but available
    'block': 0.50,             # Content blocked from finalization
}
```

### Enhanced Confidence Calculation

Combine multiple signals with weighted average:

```python
def calculate_overall_confidence(
    extraction_confidence: float,      # From source attribution quality
    generation_confidence: float,      # From LLM generation metadata
    verification_confidence: Optional[float] = None  # From verification service
) -> float:
    """
    Calculate overall confidence combining multiple signals.

    Weights:
    - Extraction: 30% (quality of source data)
    - Generation: 20% (LLM's own confidence)
    - Verification: 50% (fact-checking against sources) - HIGHEST WEIGHT
    """
    if verification_confidence is not None:
        # All three signals available
        return (
            0.30 * extraction_confidence +
            0.20 * generation_confidence +
            0.50 * verification_confidence
        )
    else:
        # Verification unavailable, adjust weights
        return (
            0.60 * extraction_confidence +
            0.40 * generation_confidence
        )
```

### Decision Rules

```python
def determine_content_status(confidence: float) -> Dict[str, Any]:
    """
    Determine content status based on confidence score.

    Returns:
        {
            'tier': ConfidenceTier,
            'requires_review': bool,
            'auto_approved': bool,
            'blocked': bool,
            'user_message': str
        }
    """
    if confidence >= 0.85:
        return {
            'tier': ConfidenceTier.HIGH,
            'requires_review': False,
            'auto_approved': True,
            'blocked': False,
            'user_message': 'High confidence - verified against sources'
        }
    elif confidence >= 0.70:
        return {
            'tier': ConfidenceTier.MEDIUM,
            'requires_review': False,
            'auto_approved': True,
            'blocked': False,
            'user_message': 'Good confidence - minor uncertainties'
        }
    elif confidence >= 0.50:
        return {
            'tier': ConfidenceTier.LOW,
            'requires_review': True,  # FLAG
            'auto_approved': False,
            'blocked': False,
            'user_message': 'Low confidence - please review before finalizing'
        }
    else:  # confidence < 0.50
        return {
            'tier': ConfidenceTier.CRITICAL,
            'requires_review': True,
            'auto_approved': False,
            'blocked': True,  # BLOCK
            'user_message': 'Critical issues detected - re-generation recommended'
        }
```

### Special Cases

**Unsupported Claims (from Verification):**
```python
# If ANY claim is classified as UNSUPPORTED
if any(claim.status == 'UNSUPPORTED' for claim in verification_result.claims):
    # Automatically downgrade to LOW confidence, flag for review
    confidence = min(confidence, 0.65)
```

**High Inferred Ratio (from Extraction):**
```python
# If >30% of extracted items are inferred (not direct)
if extraction_result.inferred_item_ratio > 0.30:
    # Penalty: reduce confidence by 0.15
    confidence -= 0.15
```

**Low Attribution Coverage:**
```python
# If <80% of claims have source attribution
if extraction_result.attribution_coverage < 0.80:
    # Penalty: reduce confidence by 0.10
    confidence -= 0.10
```

### Per-Content-Type Adjustments

Different content types may have different threshold sensitivities:

```python
CONTENT_TYPE_ADJUSTMENTS = {
    'achievement_bullet': {
        'requires_high_confidence': True,  # Achievements need strong evidence
        'threshold_adjustment': +0.05      # Slightly stricter
    },
    'technical_bullet': {
        'requires_high_confidence': False,  # Technology lists are lower risk
        'threshold_adjustment': -0.05       # Slightly more lenient
    },
    'impact_bullet': {
        'requires_high_confidence': True,   # Impact metrics need verification
        'threshold_adjustment': +0.10       # Much stricter
    }
}
```

## Consequences

### Positive

**Quality Assurance (++):**
- Automated quality gate prevents low-quality content from being finalized
- Users alerted to uncertain content before it's used
- Reduces hallucination rate by catching low-confidence items
- Data-driven threshold based on acceptable false positive rate

**User Control (+):**
- Users can override flags if they judge content acceptable
- Transparency about why content was flagged
- Empowers users to make informed decisions
- Balances automation with human judgment

**Continuous Improvement (+):**
- Track user acceptance rates per confidence tier
- Adjust thresholds based on real-world data
- A/B test different threshold values
- Measure impact on hallucination rate

**Risk Management (+):**
- Critical-quality content (confidence <0.50) blocked entirely
- Prevents obviously hallucinated content from reaching users
- Safety net for verification service failures

### Negative

**User Friction (-):**
- Flagged content requires manual review (adds time to workflow)
- False positives cause unnecessary interruptions
- Risk of user fatigue if too many items flagged
- May slow down power users who trust the system

**Threshold Tuning Complexity (--):**
- Optimal threshold depends on multiple factors
- Requires ongoing monitoring and adjustment
- Different users may have different tolerance levels
- Initial thresholds are educated guesses, need empirical validation

**Edge Cases (-):**
- Corner cases where confidence calculation is misleading
- Content may be correct but have low confidence due to inference
- Rare but high-quality content flagged incorrectly
- Need manual threshold overrides for special cases

## Alternatives

### Alternative 1: Single Fixed Threshold (Rejected)

**Idea**: Use single confidence threshold (e.g., 0.70) for all decisions.

**Rejected because**:
- Too simplistic - doesn't account for severity of low confidence
- No distinction between "needs review" vs. "should block"
- Cannot adapt to different content types
- Doesn't leverage multiple confidence signals effectively

### Alternative 2: Machine Learning Classifier (Considered but Deferred)

**Idea**: Train ML classifier to predict which content needs review based on features.

**Pros**:
- Could learn complex patterns
- Potentially more accurate than rule-based thresholds
- Adapts automatically over time

**Cons**:
- Requires significant training data (thousands of labeled examples)
- Adds ML ops complexity
- Less interpretable than explicit thresholds
- Overkill for initial launch

**Decision**: Start with rule-based thresholds, revisit ML approach after collecting 6+ months of data.

### Alternative 3: User-Configurable Thresholds (Rejected)

**Idea**: Let users set their own confidence thresholds.

**Rejected because**:
- Most users won't understand what confidence scores mean
- Risk of users setting overly lenient thresholds (defeats purpose)
- Added UI complexity
- Hard to maintain consistent quality standards

**Note**: May revisit for power users in future.

### Alternative 4: Always Flag for Review (Rejected)

**Idea**: Flag ALL content for manual review regardless of confidence.

**Rejected because**:
- Defeats purpose of automation
- Unacceptable user experience (slow workflow)
- Not scalable for high-volume usage
- Users would ignore flags (cry-wolf effect)

## Rollback Plan

**Phase 1: Feature Flag Disable**
```python
if not feature_flags.is_enabled('confidence_based_flagging'):
    # Disable flagging, return all content as auto-approved
    return auto_approve_all(content)
```

**Phase 2: Threshold Adjustment**
```python
# If false positive rate too high (>40% of flagged items accepted by users)
# Loosen threshold from 0.70 to 0.60
CONFIDENCE_THRESHOLDS['flag_for_review'] = 0.60

# If hallucination rate still high (>7%)
# Tighten threshold from 0.70 to 0.75
CONFIDENCE_THRESHOLDS['flag_for_review'] = 0.75
```

**Phase 3: Disable Blocking**
```python
# If too many items blocked (>10% of generations)
# Convert BLOCK to FLAG (allow with warning)
CONFIDENCE_THRESHOLDS['block'] = 0.30  # Much lower threshold
```

**Rollback Triggers:**
- False positive rate >40% (too many valid items flagged)
- User acceptance rate <60% (users reject flags as inaccurate)
- >15% of content flagged (too disruptive to workflow)
- User complaints about interruptions >10% of sessions

**Recovery Steps:**
1. Disable confidence-based flagging via feature flag
2. Analyze flagged items vs. user decisions
3. Recalibrate thresholds based on data
4. A/B test new thresholds on 10% of users
5. Re-enable with adjusted thresholds

## Implementation Notes

### Initial Threshold Values (Conservative Start)

Based on industry best practices and research:

- **Auto-approve threshold: 0.70**
  - Rationale: 70% confidence = ~30% uncertainty, acceptable for user review-optional content
  - Source: Similar to content moderation systems (70-80% confidence for auto-approval)

- **Flag threshold: 0.50**
  - Rationale: Below 50% confidence = more uncertain than certain, needs review
  - Source: Statistical convention (>50% = more likely true than false)

- **Block threshold: 0.50**
  - Rationale: Same as flag initially, but will separate after observing data
  - Plan: After 2 weeks, may lower block threshold to 0.40 if data supports

### A/B Testing Plan

**Week 1-2: Baseline Measurement**
- Implement with conservative thresholds (0.70 flag, 0.50 block)
- Measure: False positive rate, user acceptance rate, hallucination rate
- Collect: 500+ flagged item decisions

**Week 3-4: Threshold Experimentation**
- Test A: 0.70 flag (control)
- Test B: 0.65 flag (looser - flag more items)
- Test C: 0.75 flag (tighter - flag fewer items)
- Measure impact on quality vs. user experience

**Week 5: Threshold Finalization**
- Select optimal threshold based on data
- Target: 80%+ user acceptance, <5% hallucination rate
- Document final thresholds in runbook

### Monitoring Dashboard

**Key Metrics:**
- % of content in each confidence tier
- False positive rate (flagged items user approves)
- User acceptance rate per tier
- Hallucination rate per tier (spot checks)
- Average review time for flagged items

**Alerts:**
- >20% of content flagged → investigate threshold calibration
- User acceptance rate <70% → thresholds too strict
- Hallucination rate >7% in approved content → thresholds too lenient

## Success Criteria

After 4 weeks in production:

**Quality Metrics:**
- Hallucination rate ≤5% (including auto-approved content)
- <3% of auto-approved content contains hallucinations
- User acceptance rate ≥80% for flagged content

**User Experience Metrics:**
- <15% of content flagged for review
- Average review time <60 seconds per flagged item
- <5% user complaints about excessive flagging

**System Performance:**
- Confidence calculation adds <0.1s latency
- 100% of content receives confidence score
- <1% confidence calculation errors

## Links

**Related Documents:**
- **PRD**: `docs/prds/prd.md` v1.4.0 (confidence threshold requirements)
- **TECH-SPEC**: `docs/specs/spec-llm.md` v4.0.0 (enhanced confidence scoring)
- **FEATURE**: `docs/features/ft-030-anti-hallucination-improvements.md` (planned)
- **RELATED ADRs**:
  - `adr-041-source-attribution-schema.md` (provides extraction confidence)
  - `adr-042-verification-architecture.md` (provides verification confidence)
  - `adr-044-review-workflow-ux.md` (implements review UI for flagged content)

**Research References:**
- Confidence calibration in ML systems (Guo et al., 2017)
- Human-in-the-loop system design (Amershi et al., 2014)
- Content moderation threshold optimization (Gillespie, 2018)
- False positive vs. false negative trade-offs in AI systems
