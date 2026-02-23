# ADR — Bullet Point Validation Architecture

**Status:** Accepted
**Date:** 2025-10-01
**Deciders:** Engineering Team, ML Team
**Technical Story:** Implement quality validation for ft-006 three-bullets-per-artifact

## Context and Problem Statement

The ft-006 feature requires generating exactly 3 high-quality bullet points per artifact. Without validation, the system may produce:
- **Generic content:** "Worked on various projects" (non-specific, valueless)
- **Redundant bullets:** Similar content across all 3 bullets (>80% similarity)
- **Poor structure:** Wrong hierarchy, missing metrics, weak action verbs
- **Length violations:** Too short (<60 chars) or too long (>150 chars)
- **Low ATS compatibility:** Missing job-relevant keywords

We need to decide:
1. **When** to validate (pre-LLM, post-LLM, both)?
2. **What** to validate (structure, content quality, similarity)?
3. **How** to enforce validation (block, warn, auto-regenerate)?
4. **Where** validation logic lives (service layer, validators module)?

## Decision Drivers

- **Quality Target:** ≥8/10 user satisfaction, <5% generic content rate (ft-006)
- **Success Rate:** ≥95% successful generation of exactly 3 quality bullets
- **User Experience:** Fast validation (<500ms), clear feedback messages
- **ATS Compatibility:** ≥0.7 average keyword relevance score
- **Maintainability:** Validation rules easy to update and extend
- **Performance:** Don't slow down generation pipeline significantly
- **Cost:** Minimize additional LLM calls for validation

## Considered Options

### Option A: Pre-LLM Validation Only
- **Approach:** Validate input artifacts and job context before LLM call
- **Pros:** Catch issues early, prevent bad LLM calls, save costs
- **Cons:** Can't validate output quality, doesn't catch LLM failures

### Option B: Post-LLM Validation Only (Recommended)
- **Approach:** Validate LLM output against quality criteria, regenerate if needed
- **Pros:** Validates actual output, catches all quality issues, enforces standards
- **Cons:** Wastes LLM calls on failed attempts, slower for bad outputs

### Option C: Multi-Stage Validation (Pre + Post + Continuous)
- **Approach:** Validate at every stage with different criteria
- **Pros:** Comprehensive, catches all issues, best quality
- **Cons:** Complex implementation, performance overhead, harder to maintain

### Option D: Statistical Sampling Validation
- **Approach:** Validate random sample, assume rest is acceptable
- **Pros:** Fast, low overhead, good for monitoring
- **Cons:** Misses quality issues, inconsistent user experience, not acceptable for feature

## Decision Outcome

**Chosen Option: Option B - Post-LLM Validation with Auto-Regeneration**

### Rationale

1. **Quality Focus:** Need to validate actual LLM output, not just inputs
2. **Clear Feedback:** Post-validation provides specific quality scores for user review
3. **Auto-Recovery:** Failed validation triggers regeneration (up to 3 attempts)
4. **Cost-Effective:** Prompt engineering + validation cheaper than multi-stage approach
5. **Proven Pattern:** `llm_services/` uses post-processing validation successfully
6. **User Testing:** Beta users prefer seeing validated output vs raw LLM responses

### Validation Architecture

```python
# Validation happens in BulletValidationService
class BulletValidationService:
    """
    Multi-criteria validation service for bullet points.

    Validation Stages:
    1. Structure Validation: Exactly 3 bullets with correct hierarchy
    2. Content Quality Scoring: 0-1 score based on weighted criteria
    3. Semantic Similarity: Detect redundancy between bullets (>80% = fail)
    4. ATS Optimization: Keyword relevance and action verb checking
    5. Length Compliance: 60-150 characters per bullet
    """

    def validate_bullet_set(
        self,
        bullets: List[BulletPoint],
        job_context: JobContext
    ) -> ValidationResult:
        """
        Comprehensive validation of bullet point set.

        Returns ValidationResult with:
        - is_valid: bool
        - quality_score: float (0-1)
        - issues: List[ValidationIssue]
        - suggestions: List[str]
        """

    def validate_three_bullet_structure(
        self,
        bullets: List[BulletPoint]
    ) -> StructureValidationResult:
        """
        Validate exactly 3 bullets with achievement → technical → impact hierarchy.

        Checks:
        - Count == 3
        - bullet_type in correct order
        - All required fields present
        """

    def validate_content_quality(
        self,
        bullet: BulletPoint,
        job_context: JobContext
    ) -> float:
        """
        Calculate quality score (0-1) based on weighted criteria.

        Scoring Weights:
        - Length (60-150 chars): 0.2
        - Action verb start: 0.2
        - Quantified metrics: 0.3
        - Keyword relevance: 0.2
        - Non-generic content: 0.1

        Returns: float score 0.0-1.0
        """

    def check_semantic_similarity(
        self,
        bullets: List[BulletPoint]
    ) -> List[SimilarityPair]:
        """
        Detect redundancy using embedding cosine similarity.

        Uses EmbeddingService to:
        1. Generate embeddings for each bullet
        2. Calculate pairwise cosine similarity
        3. Flag pairs with >0.80 similarity

        Returns: List of (bullet1_idx, bullet2_idx, similarity_score) tuples
        """
```

### Validation Criteria Details

#### 1. Structure Validation (BLOCKING)
**Purpose:** Ensure exactly 3 bullets with correct hierarchy
**Criteria:**
- `len(bullets) == 3` (REQUIRED)
- `bullets[0].bullet_type == "achievement"` (REQUIRED)
- `bullets[1].bullet_type == "technical"` (REQUIRED)
- `bullets[2].bullet_type == "impact"` (REQUIRED)
- All bullets have required fields (text, keywords, confidence_score)

**Failure Action:** BLOCK generation, trigger regeneration (up to 3 attempts)

#### 2. Content Quality Scoring (WARNING → BLOCK if < 0.5)
**Purpose:** Score overall bullet quality on 0-1 scale
**Scoring Algorithm:**

```python
def calculate_quality_score(bullet: BulletPoint, job_context: JobContext) -> float:
    score = 0.0

    # Length validation (0.2 weight)
    if 60 <= len(bullet.text) <= 150:
        score += 0.2
    elif 40 <= len(bullet.text) < 60:
        score += 0.1  # Partial credit for acceptable length

    # Action verb check (0.2 weight)
    if starts_with_action_verb(bullet.text):
        score += 0.2

    # Quantified metrics (0.3 weight)
    metric_count = count_metrics(bullet.text)
    if metric_count >= 2:
        score += 0.3
    elif metric_count == 1:
        score += 0.15

    # Keyword relevance (0.2 weight)
    keyword_score = calculate_keyword_relevance(bullet, job_context)
    score += keyword_score * 0.2

    # Generic content penalty (0.1 weight)
    if not is_generic_content(bullet.text):
        score += 0.1

    return min(score, 1.0)
```

**Thresholds:**
- `score >= 0.7`: PASS (high quality)
- `0.5 <= score < 0.7`: WARN (acceptable, show warning to user)
- `score < 0.5`: BLOCK (regenerate required)

#### 3. Semantic Similarity Detection (BLOCKING if > 0.80)
**Purpose:** Prevent redundant bullets
**Method:**
1. Generate embeddings using `EmbeddingService`
2. Calculate pairwise cosine similarity
3. Flag pairs with similarity > 0.80

**Failure Action:**
- If any pair > 0.80: BLOCK, regenerate with anti-redundancy prompt
- If all pairs ≤ 0.80: PASS

#### 4. ATS Optimization (WARNING)
**Purpose:** Ensure job-relevant keywords present
**Criteria:**
- At least 1 job keyword per bullet
- Action verb from approved list (200+ strong verbs)
- No weak phrases ("responsible for", "worked on")

**Failure Action:** WARN user, allow approval or regeneration

#### 5. Length Compliance (BLOCKING)
**Purpose:** Ensure bullets fit CV templates
**Criteria:**
- Minimum: 60 characters (prevent too-short bullets)
- Maximum: 150 characters (prevent CV bloat)
- Optimal: 80-120 characters

**Failure Action:**
- < 60 or > 150: BLOCK, auto-regenerate
- 60-79 or 121-150: WARN (acceptable range)

### Integration with Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│  BulletGenerationService.generate_bullets()                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │ Call TailoredContentService │
         │ generate_bullet_points()     │
         └──────────┬───────────────────┘
                    │ Returns 3 raw bullets
                    ▼
         ┌───────────────────────────────┐
         │ BulletValidationService        │
         │ .validate_bullet_set()         │
         └──────────┬────────────────────┘
                    │
           ┌────────▼─────────┐
           │ Structure Valid?  │
           └────────┬─────────┘
                    │
         YES ───────┼─────── NO → Regenerate (attempt 1/3)
                    │
                    ▼
         ┌──────────────────────┐
         │ Quality Scores?       │
         └──────────┬────────────┘
                    │
         ≥0.5 ──────┼────── <0.5 → Regenerate (attempt 2/3)
                    │
                    ▼
         ┌──────────────────────┐
         │ Similarity Check?     │
         └──────────┬────────────┘
                    │
         ≤0.80 ─────┼────── >0.80 → Regenerate (attempt 3/3)
                    │
                    ▼
         ┌──────────────────────┐
         │ Return Validated      │
         │ Bullets + Metadata    │
         └───────────────────────┘
```

### Regeneration Strategy

**Max Attempts:** 3
**Prompt Refinement:**
- Attempt 1: Standard prompt
- Attempt 2: Add explicit anti-redundancy instructions
- Attempt 3: Add quality examples and stricter constraints

**Failure After 3 Attempts:**
- Mark generation as "needs_review" status
- Return best attempt with quality warnings
- Allow user to manually edit or regenerate

## Positive Consequences

- **Quality Assurance:** ≥95% of bullets meet quality standards
- **User Trust:** Validation prevents obviously bad content
- **ATS Performance:** Keyword validation improves ATS scores
- **Maintainability:** Validation rules centralized in service
- **Extensibility:** Easy to add new validation criteria
- **Monitoring:** Quality metrics tracked for continuous improvement
- **Clear Feedback:** Users understand why bullets failed validation

## Negative Consequences

- **Latency:** Validation adds 200-500ms per bullet set
- **LLM Costs:** Regeneration attempts increase API costs (estimated +15%)
- **Complexity:** Multi-criteria validation complex to implement and maintain
- **False Positives:** May reject acceptable bullets occasionally
- **User Friction:** Failed validation requires user intervention

## Mitigation Strategies

### Latency Impact
- **Async Validation:** Run similarity checks in parallel
- **Caching:** Cache embeddings for reused content
- **Batching:** Validate multiple bullet sets together
- **Target:** Keep total validation time < 500ms

### Cost Management
- **Smart Regeneration:** Only regenerate specific failed bullets, not entire set
- **Prompt Optimization:** Better prompts reduce regeneration rate
- **Monitoring:** Track regeneration rate, target <15%
- **Model Selection:** Use cost-optimized models for validation embeddings

### False Positives
- **Threshold Tuning:** A/B test thresholds (0.7 vs 0.6 for quality)
- **User Feedback:** Learn from user overrides
- **Manual Override:** Allow users to approve "failed" bullets with confirmation

### User Friction
- **Clear Messages:** Explain why bullets failed with specific feedback
- **Suggestions:** Provide edit suggestions for failed bullets
- **Quick Fixes:** Offer one-click regeneration with refined prompts
- **Status Visibility:** Show validation progress in real-time

## Monitoring and Success Metrics

**Quality Metrics:**
- Average quality score: target ≥0.8
- Generic content rate: target <5%
- Redundancy detection accuracy: target ≥90%
- User satisfaction: target ≥8/10

**Performance Metrics:**
- Validation latency: target <500ms
- Regeneration rate: target <15%
- Success rate after 3 attempts: target ≥95%
- False positive rate: target <10%

**Cost Metrics:**
- Cost per validated bullet set: track and optimize
- Regeneration cost impact: target <20% overhead
- Embedding cache hit rate: target ≥60%

## References

- **ft-006 Feature Spec:** Lines 95-135 define validation requirements
- **Cognitive Load Theory:** Miller's 7±2 rule supports 3-bullet limit
- **ATS Research:** Keyword optimization improves parsing by 25-40%
- **Embedding Similarity:** Cosine similarity standard for text redundancy detection

## Related ADRs

- [ADR-016-three-bullets-per-artifact](adr-016-three-bullets-per-artifact.md)
- [ADR-018-generation-service-layer-extraction](adr-018-generation-service-layer-extraction.md)
- [ADR-014-llm-prompt-design-strategy](adr-014-llm-prompt-design-strategy.md)

