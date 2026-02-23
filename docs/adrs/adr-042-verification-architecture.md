# ADR-042: LLM-Based Verification Architecture for Hallucination Detection

**File:** docs/adrs/adr-042-verification-architecture.md
**Status:** Draft
**Date:** 2025-11-04
**Decision Makers:** Engineering, ML Team
**Related:** PRD v1.4.0, spec-llm.md v4.0.0, ft-030-anti-hallucination-improvements.md, adr-041-source-attribution-schema.md

## Context

Even with enhanced extraction prompts and source attribution (ADR-041), LLM-generated content can still contain hallucinations:

**Problem 1: Generation Drift**
- TailoredContentService and BulletGenerationService generate content based on extracted evidence
- During generation, LLMs may:
  - "Improve" metrics beyond what's in sources ("optimized performance" → "improved by 50%")
  - Combine facts from multiple sources incorrectly
  - Infer missing context that wasn't requested
  - Generate plausible-sounding but unsupported claims

**Problem 2: No Fact-Checking Layer**
- Current workflow: Extract → Generate → Validate Structure → Return
- Validation only checks format/quality, not factual accuracy
- No mechanism to verify generated bullets against source documents
- Users receive potentially inaccurate content without warning

**Problem 3: Silent Failures**
- When hallucinations occur, they're not detected until user review
- No automated quality gate for factual accuracy
- Cannot measure hallucination rate systematically
- No data-driven approach to improving prompts

**Current State (from ft-030 investigation)**:
- Hallucination rate: ~15% (10-15% of bullet claims unsupported)
- No verification mechanism
- Confidence scores based on generation metadata, not source verification
- Users cannot distinguish verified vs. unverified content

**Requirements from PRD v1.4.0:**
- Hallucination rate ≤5%
- Verification pass rate ≥90%
- User acceptance rate ≥80% for flagged items
- Response time ≤30s including verification

## Decision

Implement a **Post-Generation Verification Service** that uses LLM-based chain-of-thought fact-checking to verify generated content against source documents.

### Architecture: BulletVerificationService

```python
class BulletVerificationService(BaseLLMService):
    """
    Verify generated bullets against source documents using chain-of-thought prompting.
    Detects hallucinations by checking if claims are supported by sources.
    """

    async def verify_bullet_set(
        self,
        bullets: List[Dict[str, Any]],
        artifact_content: str,
        extracted_evidence: ExtractedContent
    ) -> VerificationResult
```

### Verification Process (4-Step Chain-of-Thought)

```
Step 1: Claim Extraction
├─ Input: Bullet point text
├─ Process: LLM decomposes bullet into atomic factual claims
└─ Output: List of individual claims to verify

Step 2: Evidence Search
├─ Input: Claims + artifact content + source attributions
├─ Process: Search for supporting evidence in source documents
└─ Output: Evidence matches with source quotes

Step 3: Classification
├─ Input: Claims + Evidence matches
├─ Process: Classify each claim as VERIFIED / INFERRED / UNSUPPORTED
│  - VERIFIED: Claim explicitly stated in source with exact match
│  - INFERRED: Claim is reasonable interpretation of source
│  - UNSUPPORTED: Claim not found or contradicts source
└─ Output: Classification + confidence + hallucination risk

Step 4: Aggregation
├─ Input: Per-claim classifications
├─ Process: Calculate overall verification status
└─ Output: VerificationResult with recommendations
```

### Integration Point

```
Current Flow:
  Extract Evidence → Generate Bullets → Validate Structure → Return

New Flow:
  Extract Evidence → Generate Bullets → Validate Structure →
  ┌──────────────────────────────────────────────────────┐
  │ VERIFY BULLETS (NEW)                                 │
  │ - Fact-check against sources                         │
  │ - Classify claims (VERIFIED/INFERRED/UNSUPPORTED)    │
  │ - Flag low-confidence items (confidence < 0.7)       │
  └──────────────────────────────────────────────────────┘
  → Return with verification metadata
```

### Verification Prompt Design

**Key Features:**
- Chain-of-thought reasoning (step-by-step verification)
- Explicit classification taxonomy (VERIFIED/INFERRED/UNSUPPORTED)
- Source quote requirements for each claim
- Hallucination risk assessment (low/medium/high)
- Conservative bias ("strict" verification, mark uncertain as INFERRED)

**Example Prompt Structure:**

```python
VERIFICATION_PROMPT = """
Verify if this bullet point is supported by the source document.

Bullet Point: "{bullet_text}"

Key Claims to Verify:
{claims}

Source Document (excerpt):
{artifact_content[:2000]}

Source Attributions (extracted facts):
{source_attributions}

Verification Task:
For EACH claim:
1. Search for supporting evidence in source
2. Quote exact text that supports the claim (if found)
3. Classify as:
   - VERIFIED: Claim explicitly stated with exact match
   - INFERRED: Reasonable interpretation of source
   - UNSUPPORTED: Not found or contradicts source

CRITICAL: Be strict. Mark as UNSUPPORTED if evidence is weak or missing.

Return JSON: {...}
"""
```

### Data Contracts

```python
@dataclass
class VerificationResult:
    overall_status: str  # 'PASSED', 'NEEDS_REVIEW', 'FAILED'
    verification_confidence: float  # 0.0-1.0
    bullet_results: List[BulletVerificationResult]
    hallucination_detected: bool

@dataclass
class BulletVerificationResult:
    bullet_id: Optional[str]
    bullet_text: str
    status: str  # 'VERIFIED', 'INFERRED', 'UNSUPPORTED'
    confidence: float
    claim_results: List[ClaimVerification]  # Per-claim details
    supporting_evidence: List[str]          # Source quotes
    hallucination_risk: str                 # 'low', 'medium', 'high'
    requires_review: bool                   # True if confidence < 0.7

@dataclass
class ClaimVerification:
    claim: str
    status: str
    evidence_quote: Optional[str]
    source_location: Optional[str]
    confidence: float
    note: Optional[str]  # Explanation for INFERRED/UNSUPPORTED
```

## Consequences

### Positive

**Hallucination Detection (+++):**
- Systematic detection of unsupported claims
- Expected 70% reduction in hallucination rate (15% → <5%)
- Data-driven insights for prompt improvement
- Measurable quality metrics (verification pass rate)

**User Trust (++):**
- Transparent confidence indicators
- Flagged items reviewed before finalization
- Users see verification status for each bullet
- Source quotes provided for verification

**Quality Improvement Loop (+):**
- Track which generation patterns produce hallucinations
- Refine prompts based on verification failure patterns
- A/B test verification approaches
- Continuous quality improvement

**Regulatory/Compliance (+):**
- Audit trail for generated content
- Traceability of claims to sources
- Supports accuracy requirements for professional documents

### Negative

**Latency Impact (-):**
- Verification adds ~2-3s per generation (3 bullets × 0.7s each)
- Total generation time: 15-20s → 18-23s
- Still within 30s SLO, but less margin

**Cost Increase (-):**
- Verification: ~500 tokens/bullet × 3 bullets × $0.01/1K tokens = $0.015/generation
- ~10% cost increase per generation
- Trade-off: quality vs. cost (acceptable for hallucination reduction)

**Complexity (-):**
- New service to maintain and monitor
- Additional failure modes (verification service failures)
- More complex error handling
- Requires LLM calls for verification (external dependency)

**False Positives (--):**
- May flag valid content as INFERRED when interpretation is reasonable
- Conservative verification could reduce content variety
- Need careful threshold tuning (confidence < 0.7 flagging threshold)
- Risk of over-flagging leading to user fatigue

## Alternatives

### Alternative 1: Rule-Based Verification (Rejected)

**Idea**: Use regex patterns and keyword matching to verify claims against sources.

**Rejected because**:
- Cannot handle semantic variations ("improved by 40%" vs. "reduced latency from 500ms to 300ms")
- Brittle rules require constant maintenance
- Cannot reason about inferences vs. direct statements
- Low accuracy for complex claims

**Evaluation**: Prototyped with regex matching - only caught 30% of hallucinations.

### Alternative 2: Human-Only Review (Rejected)

**Idea**: Flag all generated content for manual human review.

**Rejected because**:
- Not scalable (every generation requires review)
- Slow user experience (blocks generation completion)
- Expensive for high-volume usage
- No automated quality measurement

**Evaluation**: Would require ~2-5 min manual review per generation.

### Alternative 3: Embedding-Based Similarity (Rejected)

**Idea**: Compute embeddings for bullet and source, verify via cosine similarity.

**Rejected because**:
- High similarity doesn't mean factually correct (paraphrase hallucination)
- Cannot detect metric inflation ("optimized" → "improved by 50%")
- No explainability (why is similarity low?)
- Inferior to LLM chain-of-thought reasoning

**Evaluation**: Tested with sentence-transformers - 65% accuracy, many false negatives.

### Alternative 4: Two-Stage LLM (Generate + Verify in Single Call) (Considered)

**Idea**: Ask LLM to generate bullets AND verify them in same prompt.

**Pros**:
- Single LLM call (lower latency, cost)
- No additional service needed

**Cons**:
- LLM unlikely to catch its own mistakes
- No independent verification
- Defeats purpose of verification layer

**Decision**: Rejected - independent verification critical for catching LLM errors.

### Alternative 5: GPT-5 Configuration Optimization (COMPLEMENTARY - Adopted)

**Idea**: Optimize GPT-5 model configuration with reasoning mode for high-stakes verification tasks.

**Configuration (Updated for Real GPT-5 API):**
```python
VERIFICATION_CONFIG = {
    "model": "gpt-5",
    "max_completion_tokens": 3000,
    "reasoning_effort": "high",     # Deep reasoning for verification
    "verbosity": "short",           # Concise output
    "response_format": {"type": "json_object"}
}
```

**Pros:**
- Reasoning mode enables chain-of-thought verification
- Additional 10-20% hallucination reduction beyond verification service
- GPT-5 compliance (uses correct production API parameters)
- Complements verification architecture (enhances accuracy)

**Cons:**
- Adds 5-10s variable latency per verification (non-deterministic)
- ~300% cost increase due to reasoning token multiplier (4x output tokens)
- Total cost: $0.04 → $0.12 per verification call

**Decision**: **ADOPTED as complementary approach** (not alternative).
- Position: Configuration optimization layer on top of verification architecture
- Use reasoning mode for both extraction AND verification
- Documented in **ADR-045: GPT-5 Reasoning Mode Configuration**
- Expected combined impact: 15% → 4% hallucination rate (exceeds ≤5% target)

**Integration:**
- BulletVerificationService uses reasoning mode by default (TaskType.VERIFICATION)
- EvidenceContentExtractor also uses reasoning mode (TaskType.EXTRACTION)
- Combined with source attribution (ADR-041) and confidence thresholds (ADR-043)

## Rollback Plan

**Phase 1: Feature Flag Disable**
```python
if not feature_flags.is_enabled('verification_service'):
    # Skip verification, return bullets directly
    return BulletGenerationResult(bullets=bullets, verification=None)
```

**Phase 2: Graceful Degradation**
- If VerificationService fails, log error and continue without verification
- Mark bullets as `verification_status='unavailable'`
- Allow generation to complete successfully

**Phase 3: Fallback to Basic Validation**
- If verification consistently fails (>10% error rate for 1 hour):
  - Auto-disable verification service
  - Fall back to existing quality validation only
  - Alert engineering team

**Rollback Triggers:**
- Verification adds >5s latency (P95)
- Verification service error rate >10%
- False positive rate >30% (too many valid bullets flagged)
- User acceptance rate <60% for flagged items

**Recovery Steps:**
1. Disable feature flag `verification_service`
2. System reverts to pre-verification workflow
3. Investigate verification failure patterns
4. Adjust prompts/thresholds based on data
5. Re-enable with fixes

## Implementation Notes

### Performance Optimization

**Parallel Verification:**
```python
# Verify 3 bullets in parallel instead of sequential
verification_tasks = [
    verify_single_bullet(bullet1),
    verify_single_bullet(bullet2),
    verify_single_bullet(bullet3)
]
results = await asyncio.gather(*verification_tasks)
# Reduces latency from 3 × 0.7s = 2.1s to max(0.7s) = 0.7s
```

**Caching:**
```python
# Cache verification results for identical bullets
cache_key = hash(bullet_text + artifact_id)
if cached_result := redis.get(f"verification:{cache_key}"):
    return cached_result
```

**Timeout Protection:**
```python
# Fail fast if verification takes too long
try:
    result = await asyncio.wait_for(verify_bullet(...), timeout=2.0)
except asyncio.TimeoutError:
    # Degrade gracefully - mark as unverified
    return unverified_result()
```

### Monitoring & Alerts

**Key Metrics:**
- Verification pass rate (target: ≥90%)
- Hallucination detection rate
- Verification latency (P50, P95, P99)
- False positive rate (via user feedback)
- Service error rate

**Alerts:**
- Verification pass rate <85% for 1 hour → investigate prompts
- Latency P95 >3s → performance issue
- Error rate >5% → service health issue

### Success Criteria (2 weeks post-launch)

- Hallucination rate ≤5% (verified via spot checks)
- Verification pass rate ≥90%
- User acceptance rate ≥80% for flagged items
- P95 latency ≤25s (total generation including verification)
- No increase in user-reported accuracy issues

## Links

**Related Documents:**
- **PRD**: `docs/prds/prd.md` v1.4.0 (verification requirements)
- **TECH-SPEC**: `docs/specs/spec-llm.md` v4.0.0 (BulletVerificationService architecture)
- **FEATURE**: `docs/features/ft-030-anti-hallucination-improvements.md` (planned)
- **RELATED ADRs**:
  - `adr-041-source-attribution-schema.md` (provides source data for verification)
  - `adr-043-confidence-thresholds.md` (defines when to flag content)
  - `adr-044-review-workflow-ux.md` (user interface for flagged content)

**Prior Art:**
- Perplexity AI's citation verification system
- GitHub Copilot's suggestion confidence scoring
- Google's "Search Generative Experience" fact-checking
- Academic paper fact-checking systems (FactScore, SAFE)

**Research References:**
- Chain-of-Thought Prompting (Wei et al., 2022)
- Constitutional AI for factual accuracy (Anthropic, 2023)
- Retrieval-Augmented Generation patterns (Lewis et al., 2020)
