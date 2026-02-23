# Feature — ft-030: Anti-Hallucination Quality Improvements

**File:** docs/features/ft-030-anti-hallucination-improvements.md
**Owner:** Engineering, ML Team
**Status:** Planning Complete → Ready for Implementation
**Priority:** P0 (Critical Quality Issue)
**Complexity:** Large (System-wide changes with new services)
**Estimated Effort:** 12-17 days

**TECH-SPECs:**
- `spec-llm.md` (v4.0.0) - Anti-hallucination architecture, source attribution, verification service
- `spec-api.md` (v4.2.0 → v5.0.0 planned) - Review workflow endpoints
- `spec-cv-generation.md` (v1.0.0 → v2.0.0 planned) - Verification integration
- `spec-frontend.md` (v2.3.0 → v3.0.0 planned) - Review UI components

**PRD:** `prd.md` v1.4.0 (anti-hallucination requirements)

**ADRs:**
- `adr-041-source-attribution-schema.md` - Source traceability design
- `adr-042-verification-architecture.md` - LLM-based fact-checking
- `adr-043-confidence-thresholds.md` - Flagging policy
- `adr-044-review-workflow-ux.md` - User interface design

---

## Problem Statement

**Current State:** Generated CV/cover letter content contains ~15% hallucinations (false or unsupported claims). Hallucinations occur primarily in evidence extraction phase and propagate through generation pipeline.

**Impact:**
- Users cannot trust generated content accuracy
- No mechanism to detect or prevent hallucinations
- No traceability of claims to source documents
- All content presented equally regardless of confidence

**Root Causes (from Stage B Discovery):**
1. **Evidence Extraction**: Lacks source grounding, LLM infers/expands information (15-20% hallucination rate)
2. **Content Enrichment**: "Use to enhance" guidance allows adding unrequested details (10-15% hallucination rate)
3. **Bullet Generation**: No source verification, can infer metrics not in sources (10-15% hallucination rate)
4. **No Fact-Checking**: Generated content never validated against source documents

**Target State:** Hallucination rate ≤5%, with source attribution for all claims, verification layer for detection, and user review workflow for flagged content.

---

## Stage B Discovery Findings

### Test Impact Analysis

**Tests to Update:**

1. **Evidence Extraction Tests** (`backend/llm_services/tests/test_evidence_content_extractor.py`)
   - Update mocked LLM responses to include source attribution fields
   - Add tests for attribution_coverage and inferred_item_ratio calculations
   - Update extraction prompt assertions to check for "ONLY extract" instructions
   - **Coverage Gap**: Confidence scoring logic (current: 45%) - need comprehensive unit tests

2. **Artifact Enrichment Tests** (`backend/llm_services/tests/test_artifact_enrichment.py`)
   - Update tests to verify "GROUND TRUTH" prompt structure
   - Add tests for enhanced confidence calculation
   - Test handling of missing attribution data
   - **Coverage Gap**: Multi-source merging logic (current: 60%)

3. **Bullet Generation Tests** (`backend/generation/tests/test_bullet_generation_service.py`)
   - Update expected responses to include verification metadata
   - Mock verification service calls
   - Test integration with BulletVerificationService
   - **Coverage Gap**: Retry logic with verification failures (current: 50%)

4. **API Tests** (`backend/generation/tests/test_api.py`, `backend/accounts/tests/test_profile_api.py`)
   - Update response schema assertions for new verification fields
   - Add tests for review workflow endpoints
   - Test bulk approve/reject operations

**Tests to Add (New Components):**

5. **BulletVerificationService Tests** (`backend/generation/tests/test_verification_service.py`)
   - NEW: Chain-of-thought claim extraction
   - NEW: Evidence search and matching
   - NEW: Claim classification (VERIFIED/INFERRED/UNSUPPORTED)
   - NEW: Verification result aggregation
   - NEW: Parallel verification performance

6. **Confidence Threshold Tests** (`backend/generation/tests/test_confidence_thresholds.py`)
   - NEW: Multi-signal confidence calculation
   - NEW: Tier classification logic
   - NEW: Special case handling (unsupported claims, high inferred ratio)
   - NEW: Per-content-type adjustments

7. **Frontend Review Workflow Tests** (`frontend/src/components/review/__tests__/`)
   - NEW: ConfidenceBadge rendering for all tiers
   - NEW: ReviewModal interactions (approve/reject/edit)
   - NEW: Bulk action behavior
   - NEW: Source attribution display

**Tests to Remove:**
- None (no deprecated functionality)

**Test Update Checklist:**
- [ ] Update extraction tests with source attribution (Stage F)
- [ ] Update enrichment tests with enhanced confidence (Stage F)
- [ ] Update bullet generation tests with verification (Stage F)
- [ ] Create BulletVerificationService unit tests (Stage F)
- [ ] Create confidence threshold unit tests (Stage F)
- [ ] Create frontend review workflow tests (Stage F)
- [ ] Add integration tests for end-to-end verification flow (Stage H)
- [ ] Add API integration tests for review endpoints (Stage H)
- [ ] Performance tests for parallel verification (Stage H)

**Coverage Targets:**
- Evidence extraction: 85% → 90%
- Bullet generation: 89.6% (current - maintain)
- NEW verification service: ≥85%
- Frontend review components: ≥80%

### Existing Implementation Analysis

**Similar Features:**
- **llm_services/services/core/evidence_content_extractor.py** (lines 252-508)
  - Existing extraction with regex metrics extraction
  - Pattern to follow: Structured extraction with confidence scoring
  - Will enhance: Add source attribution requirements to prompts

- **generation/services/bullet_generation_service.py** (613 lines)
  - Existing generation with retry logic
  - Pattern to follow: Service composition with error handling
  - Will enhance: Add verification step after generation

- **generation/services/bullet_validation_service.py** (495 lines)
  - Existing structure/quality validation
  - Pattern to reuse: Multi-criteria validation framework
  - Will augment: Add factual accuracy validation alongside structure checks

**Reusable Components:**

1. **Circuit Breaker** (`llm_services/services/reliability/circuit_breaker.py`)
   - Use for verification service LLM calls
   - Existing fault tolerance patterns

2. **Task Executor** (`llm_services/services/base/task_executor.py`)
   - Use for retry logic in verification
   - Existing timeout handling

3. **Model Selector** (`llm_services/services/infrastructure/model_selector.py`)
   - Use for verification model selection
   - Existing fallback chains

4. **Base Service** (`llm_services/services/base/base_service.py`)
   - Inherit for BulletVerificationService
   - Existing LLM call infrastructure

**Patterns to Follow:**

1. **Service Layer Architecture** (from `llm_services/`)
   ```
   generation/services/
   └── bullet_verification_service.py  ← NEW, follows llm_services pattern
       ├── Inherits from BaseLLMService
       ├── Uses CircuitBreaker for reliability
       ├── Uses TaskExecutor for retries
       └── Implements async verification methods
   ```

2. **Prompt Engineering** (from `evidence_content_extractor.py`)
   - Structured JSON output with validation
   - Explicit constraints in prompts
   - Confidence scoring per item

3. **Multi-Criteria Validation** (from `bullet_validation_service.py`)
   - Multiple validation checks
   - Aggregated results with detailed feedback
   - Boolean + warning/error categorization

**Code to Refactor:**
- None (all new additions, no breaking changes to existing code)

### Dependency & Side Effect Mapping

**Dependencies:**

**Backend:**
- `llm_services.services.base.BaseLLMService` - Base class for verification service
- `llm_services.services.reliability.CircuitBreaker` - Fault tolerance
- `llm_services.services.infrastructure.ModelSelector` - Model routing
- `generation.models.BulletPoint` - Will add verification fields
- `artifacts.models.Artifact` - Reads artifact content for verification
- OpenAI API - Verification LLM calls

**Frontend:**
- `@radix-ui/react-dialog` - Review modal
- `@radix-ui/react-accordion` - Verification details
- `react-hook-form` - Edit bullet form
- `zustand` - Review state management
- Existing `BulletCard` component - Will enhance with confidence indicators

**Side Effects:**

**Database:**
- **NO schema migrations** - Source attribution stored in existing JSON fields
- Writes to `BulletPoint` records with new verification metadata
- Redis cache writes for verification results (TTL: 1 hour)
- No impact on existing tables/columns

**API:**
- **NEW endpoints**: `/api/generation/{id}/bullets/{id}/approve`, `/reject`, bulk operations
- **Enhanced responses**: Existing bullet endpoints include verification metadata
- Backward compatible: New fields optional, existing clients unaffected

**External Services:**
- **Increased LLM API usage**: +10-15% token usage for attribution, +10% for verification
- **Cost impact**: ~$0.021/generation total increase (within acceptable limits)
- **Latency impact**: +2-3s for verification (total 18-23s, within 30s SLO)

**Impact Radius:**

**High Impact (Breaking Changes):**
- None - All changes backward compatible

**Medium Impact (Enhanced Functionality):**
- `evidence_content_extractor.py` - Enhanced prompts, new output fields
- `bullet_generation_service.py` - Integration with verification service
- `generation/views.py` - New review endpoints
- Frontend wizard - New conditional review step

**Low Impact (Isolated Additions):**
- NEW `bullet_verification_service.py` - Isolated new service
- NEW frontend review components - Isolated new UI
- Enhanced confidence scoring - Internal logic only

**Risk Areas:**

1. **Verification Service LLM Calls** (HIGH RISK)
   - External dependency, can fail or timeout
   - Mitigation: Circuit breaker, graceful degradation, timeout protection
   - Test coverage needed: >85%

2. **Confidence Threshold Calibration** (MEDIUM RISK)
   - Initial thresholds are estimates, may need adjustment
   - Mitigation: Feature flags, A/B testing, monitoring
   - Plan: 2-week calibration period with data collection

3. **User Experience Friction** (MEDIUM RISK)
   - Review workflow adds steps, may slow users down
   - Mitigation: Non-blocking design, bulk actions, skip for high-confidence
   - Monitor: Abandon rate at review step, user feedback

4. **Performance Degradation** (LOW RISK)
   - Verification adds latency
   - Mitigation: Parallel verification, caching, timeout protection
   - Target: Keep P95 <25s

---

## Architecture Conformance

### Layer Assignment

Following `docs/architecture/patterns.md` and llm_services structure:

**Backend Services:**
```
generation/services/
└── bullet_verification_service.py    # Core layer
    ├── Inherits: BaseLLMService
    ├── Uses: CircuitBreaker (reliability)
    ├── Uses: TaskExecutor (base)
    └── Uses: ModelSelector (infrastructure)

generation/views.py                    # Interface layer
├── ReviewBulletView (approve/reject)
└── BulkReviewView (bulk operations)

llm_services/services/core/
└── evidence_content_extractor.py     # Core layer (enhanced)
    └── Enhanced prompts with source attribution
```

**Frontend Components:**
```
frontend/src/components/
├── review/                            # Feature-specific components
│   ├── ConfidenceBadge.tsx
│   ├── ReviewModal.tsx
│   ├── SourceAttributionCard.tsx
│   └── ReviewActionBar.tsx
└── generation/
    └── GenerationWizard.tsx           # Enhanced with review step
```

### Pattern Compliance

**✓ Service Layer Pattern**
- `BulletVerificationService` follows llm_services architecture
- Inherits from `BaseLLMService`
- Uses composition for circuit breaker, task executor
- Async/await for LLM calls

**✓ Reliability Patterns**
- Circuit breaker for external LLM calls
- Retry logic with exponential backoff
- Timeout protection (2s per bullet verification)
- Graceful degradation (continue if verification fails)

**✓ Error Handling**
- Try/catch with specific exception types
- Logging with context (bullet ID, artifact ID)
- User-friendly error messages
- Fallback behavior defined

**✓ Testing Strategy (TDD)**
- Write failing tests first (Stage F)
- Unit tests for all business logic
- Integration tests for API + service interactions
- Frontend component tests for review UI

### Dependencies

**Service Dependencies:**
```python
from llm_services.services.base import BaseLLMService
from llm_services.services.reliability import CircuitBreaker
from llm_services.services.infrastructure import ModelSelector
from generation.models import BulletPoint
from artifacts.models import Artifact
```

**No Circular Dependencies:**
- Verification service depends on models (✓ allowed)
- Models don't depend on services (✓ correct)
- Clear dependency direction: views → services → models

---

## Acceptance Criteria

### Functional Requirements

**Evidence Extraction:**
- [ ] F1.1: All extracted technologies include source attribution (location, quote, confidence)
- [ ] F1.2: All extracted achievements include exact source quotes from documents
- [ ] F1.3: Items marked as 'direct' vs. 'inferred' based on source evidence
- [ ] F1.4: Attribution coverage ≥95% for all extractions
- [ ] F1.5: Inferred item ratio ≤20% for all extractions

**Verification Service:**
- [ ] F2.1: BulletVerificationService verifies all bullets against source documents
- [ ] F2.2: Each claim classified as VERIFIED, INFERRED, or UNSUPPORTED
- [ ] F2.3: Verification includes source quotes supporting each claim
- [ ] F2.4: Parallel verification completes in ≤2.5s for 3 bullets
- [ ] F2.5: Verification pass rate ≥90% for generated content

**Confidence Scoring:**
- [ ] F3.1: Overall confidence combines extraction (30%) + generation (20%) + verification (50%)
- [ ] F3.2: Content with confidence <0.70 flagged for review
- [ ] F3.3: Content with confidence <0.50 blocked from finalization
- [ ] F3.4: Unsupported claims automatically downgrade confidence
- [ ] F3.5: High inferred ratio (>30%) applies confidence penalty

**Review Workflow:**
- [ ] F4.1: Generation wizard inserts review step when content flagged
- [ ] F4.2: Users see confidence indicators (color-coded: green/blue/amber/red)
- [ ] F4.3: Review modal shows source evidence and verification details
- [ ] F4.4: Users can approve, reject, or edit flagged bullets
- [ ] F4.5: Bulk approve/reject available for multiple flags
- [ ] F4.6: Review decisions persist (approved bullets not re-flagged)

**GPT-5 Configuration:**
- [ ] F5.1: EvidenceContentExtractor uses reasoning mode (reasoning=True, thinking_tokens=2000)
- [ ] F5.2: BulletVerificationService uses reasoning mode (reasoning=True, thinking_tokens=3000)
- [ ] F5.3: Generation services use standard mode (reasoning=False) for speed
- [ ] F5.4: Deprecated temperature parameter removed from all LLM calls
- [ ] F5.5: BaseLLMService accepts TaskType parameter to determine config
- [ ] F5.6: Environment variables control reasoning mode (GPT5_REASONING_EXTRACTION, GPT5_REASONING_VERIFICATION)

### Quality Requirements

**Hallucination Rate:**
- [ ] Q1: Overall hallucination rate ≤5% (measured via spot checks of 100 samples)
- [ ] Q2: Auto-approved content (confidence ≥0.70) has <3% hallucination rate
- [ ] Q3: Flagged content (confidence 0.50-0.69) has <10% hallucination rate
- [ ] Q4: Blocked content (confidence <0.50) has >30% hallucination rate (correctly blocked)

**User Experience:**
- [ ] Q5: User acceptance rate ≥80% for flagged content
- [ ] Q6: <15% of total content flagged for review
- [ ] Q7: Average review time <90 seconds per flagged item
- [ ] Q8: <5% of users abandon at review step

**Performance:**
- [ ] Q9: Total generation time ≤30s (P95) including verification and reasoning mode
- [ ] Q10: Verification service P95 latency ≤5s for 3 bullets (with reasoning mode)
- [ ] Q11: Extraction P95 latency ≤4s per artifact (with reasoning mode)
- [ ] Q12: Review modal load time <1s (P95)
- [ ] Q13: Review action API response <500ms (P95)

**Reliability:**
- [ ] Q14: Verification service error rate <5%
- [ ] Q15: Graceful degradation when verification unavailable (content marked as unverified)
- [ ] Q16: Zero frontend crashes related to review workflow
- [ ] Q17: Circuit breaker activates after 5 consecutive verification failures

**Cost (GPT-5 Reasoning Mode):**
- [ ] Q18: Cost per generation ≤$0.15 (acceptable for quality improvement)
- [ ] Q19: Reasoning mode usage tracked in CloudWatch (extraction + verification calls)
- [ ] Q20: No runaway cost spikes detected (alert threshold: >$0.20/generation)

---

## Design Changes

### Backend Changes

#### 1. Enhanced ExtractedContent Schema (adr-041)

**Current:**
```python
@dataclass
class ExtractedContent:
    source_type: str
    source_url: Optional[str]
    success: bool
    data: Dict[str, Any]
    confidence: float
    processing_cost: float
```

**New (v4.0):**
```python
@dataclass
class ExtractedContent:
    source_type: str
    source_url: Optional[str]
    success: bool
    data: Dict[str, Any]
    confidence: float
    processing_cost: float

    # NEW: Source attribution fields
    source_attributions: List[SourceAttribution]
    attribution_coverage: float  # % with attribution (≥95%)
    inferred_item_ratio: float   # % inferred (≤20%)
    verification_metadata: Dict[str, Any]

@dataclass
class SourceAttribution:
    source_type: str
    source_location: str
    exact_quote: Optional[str]
    section_heading: Optional[str]
    confidence: float
    attribution_type: str  # 'direct' or 'inferred'
    hallucination_risk: str  # 'low', 'medium', 'high'
```

#### 2. BulletVerificationService (adr-042)

**New Service:**
```python
# File: backend/generation/services/bullet_verification_service.py

class BulletVerificationService(BaseLLMService):
    """
    Verify generated bullets against source documents.
    Uses chain-of-thought prompting for fact-checking.
    """

    async def verify_bullet_set(
        self,
        bullets: List[Dict[str, Any]],
        artifact_content: str,
        extracted_evidence: ExtractedContent
    ) -> VerificationResult:
        """Main entry point - verify all bullets"""

    async def verify_single_bullet(...) -> BulletVerificationResult:
        """Verify one bullet with claim extraction"""

    async def _extract_claims(...) -> List[str]:
        """Decompose bullet into atomic claims"""

    def _build_verification_prompt(...) -> str:
        """Build chain-of-thought verification prompt"""
```

#### 3. New API Endpoints (spec-api.md v5.0.0)

**Review Actions:**
```
POST /api/generation/{generationId}/bullets/{bulletId}/approve
POST /api/generation/{generationId}/bullets/{bulletId}/reject
PUT  /api/generation/{generationId}/bullets/{bulletId}
POST /api/generation/{generationId}/bullets/bulk-approve
POST /api/generation/{generationId}/bullets/bulk-reject
```

**Response Format:**
```json
{
  "id": "bullet-123",
  "text": "Led team of 5 engineers...",
  "bulletType": "achievement",

  "confidence": 0.85,
  "confidenceTier": "high",
  "requiresReview": false,

  "verificationStatus": "VERIFIED",
  "verificationConfidence": 0.92,
  "hallucinationRisk": "low",

  "sourceAttribution": {
    "sourceType": "pdf",
    "sourceLocation": "page 2, Work Experience",
    "exactQuote": "Managed 5-person engineering team...",
    "attributionType": "direct"
  },

  "claimResults": [
    {
      "claim": "Led team of 5 engineers",
      "status": "VERIFIED",
      "evidenceQuote": "Managed 5-person engineering team",
      "confidence": 0.95
    }
  ]
}
```

#### 4. GPT-5 Configuration Optimization (Updated from adr-045)

⚠️ **Note:** This section reflects corrected GPT-5 API parameters (see spec-llm.md v4.2.0).

**Task-Specific Model Configuration:**
```python
# File: backend/llm_services/services/base/config_registry.py (NEW)

from enum import Enum
from typing import Dict, Any

class TaskType(Enum):
    EXTRACTION = "extraction"      # Evidence extraction - HIGH STAKES
    VERIFICATION = "verification"  # Fact-checking - HIGH STAKES
    GENERATION = "generation"      # Content creation - STANDARD
    RANKING = "ranking"           # Artifact ranking - STANDARD

GPT5_CONFIGS: Dict[TaskType, Dict[str, Any]] = {
    TaskType.EXTRACTION: {
        "model": "gpt-5",
        "max_completion_tokens": 4000,
        "reasoning_effort": "high",     # Deep reasoning for accuracy
        "verbosity": "medium",
        "response_format": {"type": "json_object"}
    },

    TaskType.VERIFICATION: {
        "model": "gpt-5",
        "max_completion_tokens": 3000,
        "reasoning_effort": "high",     # Maximum accuracy for verification
        "verbosity": "short",           # Concise yes/no + reasoning
        "response_format": {"type": "json_object"}
    },

    TaskType.GENERATION: {
        "model": "gpt-5-mini",          # Cost-optimized for generation
        "max_completion_tokens": 2000,
        "reasoning_effort": "low",      # Speed priority
        "verbosity": "medium",
        "response_format": {"type": "json_object"}
    },

    TaskType.RANKING: {
        "model": "gpt-5-nano",          # Ultra-cheap for ranking
        "max_completion_tokens": 1000,
        "reasoning_effort": "minimal",  # Minimal reasoning needed
        "verbosity": "short",
        "response_format": {"type": "json_object"}
    }
}
```

**Updated BaseLLMService:**
```python
# File: backend/llm_services/services/base/base_service.py (UPDATED)

class BaseLLMService:
    def __init__(
        self,
        task_type: Optional[TaskType] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            task_type: Type of task (determines config)
            custom_config: Override specific config parameters
        """
        self.task_type = task_type or TaskType.GENERATION
        self.config = self._build_config(custom_config)

    def _build_config(self, custom_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build final configuration by merging task-specific + custom overrides."""
        base_config = GPT5_CONFIGS.get(self.task_type, GPT5_CONFIGS[TaskType.GENERATION])

        if custom_config:
            config = {**base_config, **custom_config}
        else:
            config = base_config.copy()

        # Validate GPT-5 parameters (remove any legacy/deprecated params)
        deprecated_params = ['temperature', 'top_p', 'frequency_penalty',
                           'presence_penalty', 'reasoning', 'thinking_tokens', 'max_tokens']
        for param in deprecated_params:
            if param in config:
                logger.warning(
                    f"[DEPRECATED] '{param}' parameter not supported in GPT-5 API. "
                    f"See spec-llm.md v4.2.0 for correct parameters."
                )
                config.pop(param)

        return config
```

**Service Updates:**
```python
# File: backend/llm_services/services/core/evidence_content_extractor.py
class EvidenceContentExtractor(BaseLLMService):
    def __init__(self):
        super().__init__(task_type=TaskType.EXTRACTION)
        # Uses gpt-5 + reasoning_effort="high"

# File: backend/generation/services/bullet_verification_service.py
class BulletVerificationService(BaseLLMService):
    def __init__(self):
        super().__init__(task_type=TaskType.VERIFICATION)
        # Uses gpt-5 + reasoning_effort="high"

# File: backend/generation/services/tailored_content_service.py
class TailoredContentService(BaseLLMService):
    def __init__(self):
        super().__init__(task_type=TaskType.GENERATION)
        # Uses gpt-5-mini + reasoning_effort="low" (cost-optimized)

# File: backend/generation/services/bullet_generation_service.py
class BulletGenerationService(BaseLLMService):
    def __init__(self):
        super().__init__(task_type=TaskType.GENERATION)
        # Uses gpt-5-mini + reasoning_effort="low"
```

**Environment Configuration:**
```python
# settings/base.py
GPT5_REASONING_CONFIG = {
    'extraction': {
        'reasoning_effort': env.str('GPT5_REASONING_EXTRACTION', default='high'),
        'model': env.str('GPT5_MODEL_EXTRACTION', default='gpt-5')
    },
    'verification': {
        'reasoning_effort': env.str('GPT5_REASONING_VERIFICATION', default='high'),
        'model': env.str('GPT5_MODEL_VERIFICATION', default='gpt-5')
    },
    'generation': {
        'reasoning_effort': env.str('GPT5_REASONING_GENERATION', default='low'),
        'model': env.str('GPT5_MODEL_GENERATION', default='gpt-5-mini')
    }
}
```

**Performance & Cost Impact:**

| Metric | Before | After (Reasoning Mode) | Change |
|--------|--------|----------------------|--------|
| Extraction Latency | 1-2s | 5-10s (variable) | +4-9s |
| Verification Latency | N/A | 5-10s (variable) | +5-10s (new service) |
| Extraction Cost (per call) | $0.04 | $0.16 | +300% (4x token multiplier) |
| Verification Cost (per call) | N/A | $0.12 | New cost |
| Generation Cost (per call, gpt-5-mini) | $0.01 | $0.005 | -50% (cost-optimized model) |
| Total Generation Cost (3 artifacts + 1 gen + 1 verify) | $0.13 | $0.26 | +100% |
| Hallucination Rate (Extraction) | 15-20% | 5-8% | -50-60% reduction |
| **Combined Hallucination Rate** | **15%** | **~4%** | **-73% (exceeds ≤5% target)** |

**Key Changes:**
- **Latency:** reasoning_effort="high" adds variable latency (5-10s, non-deterministic)
- **Cost:** Reasoning tokens multiply output cost by 3-4x for gpt-5
- **Optimization:** Use gpt-5-mini for generation (80% cost savings vs gpt-5)
- **Budget:** Per-CV generation increased from $0.13 to $0.26 (acceptable for quality gains)

**Migration Notes:**
- ❌ `temperature`, `top_p`, `frequency_penalty`, `presence_penalty` - ALL REMOVED in GPT-5
- ❌ `reasoning: True`, `thinking_tokens` - HALLUCINATED parameters, do not exist
- ✅ `reasoning_effort: "high"` - Real GPT-5 parameter for high-stakes tasks
- ✅ `max_completion_tokens` - Renamed from `max_tokens`
- ✅ Model tiering: gpt-5 (extraction/verification), gpt-5-mini (generation), gpt-5-nano (ranking)
- ✅ Environment-specific: lower reasoning_effort in dev (cost), high in prod (quality)

### Frontend Changes

#### 1. Confidence Indicator Component

**New Component:**
```typescript
// File: frontend/src/components/review/ConfidenceBadge.tsx

interface ConfidenceBadgeProps {
  confidence: number;
  tier: 'high' | 'medium' | 'low' | 'critical';
  showDetails?: boolean;
}

export function ConfidenceBadge({ confidence, tier, showDetails }: Props) {
  const config = TIER_CONFIG[tier]; // icon, color, label, message

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full
                     bg-${config.background} border border-${config.border}`}>
      <span className={`text-${config.color}`}>{config.icon}</span>
      {showDetails && (
        <>
          <span className="text-sm font-medium">{config.label}</span>
          <Tooltip content={config.message} />
        </>
      )}
    </div>
  );
}
```

#### 2. Review Modal Component

**New Component:**
```typescript
// File: frontend/src/components/review/ReviewModal.tsx

interface ReviewModalProps {
  bullet: BulletWithVerification;
  onApprove: (bulletId: string) => void;
  onReject: (bulletId: string) => void;
  onEdit: (bulletId: string, newText: string) => void;
  onClose: () => void;
}

export function ReviewModal({ bullet, onApprove, onReject, onEdit, onClose }: Props) {
  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Review Bullet Point</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Bullet text */}
          <div className="text-lg font-medium">{bullet.text}</div>

          {/* Flagging reason */}
          <Alert variant="warning">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Why flagged</AlertTitle>
            <AlertDescription>
              {getFlaggingReason(bullet)}
            </AlertDescription>
          </Alert>

          {/* Source evidence */}
          <SourceAttributionCard attribution={bullet.sourceAttribution} />

          {/* Detailed verification (collapsible) */}
          <Accordion type="single" collapsible>
            <AccordionItem value="details">
              <AccordionTrigger>View detailed verification</AccordionTrigger>
              <AccordionContent>
                <ClaimResultsList claims={bullet.claimResults} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          {/* Actions */}
          <ReviewActionBar
            onApprove={() => onApprove(bullet.id)}
            onReject={() => onReject(bullet.id)}
            onEdit={() => setEditMode(true)}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

#### 3. Generation Wizard Enhancement

**Modified Flow:**
```typescript
// File: frontend/src/components/generation/GenerationWizard.tsx

export function GenerationWizard() {
  const [step, setStep] = useState(0);
  const { flaggedBullets, allBullets } = useGenerationStatus();

  const steps = [
    { id: 'job', component: <JobDescriptionForm /> },
    { id: 'artifacts', component: <ArtifactSelectionForm /> },
    { id: 'generate', component: <GenerationForm /> },

    // NEW: Conditional review step
    ...(flaggedBullets.length > 0 ? [{
      id: 'review',
      component: <ReviewInterface bullets={flaggedBullets} />
    }] : []),

    { id: 'finalize', component: <FinalizeForm /> }
  ];

  return <WizardContainer steps={steps} currentStep={step} />;
}
```

---

## Test & Eval Plan

### Unit Tests (Stage F - TDD RED Phase)

**Backend:**

1. **Source Attribution Tests** (`test_source_attribution.py`)
   ```python
   def test_extract_with_attribution():
       """Verify extraction includes source quotes"""
       # Arrange: Mock PDF with clear source data
       # Act: Extract content
       # Assert: All items have source_attribution with quotes

   def test_inferred_item_ratio_calculation():
       """Verify inferred ratio calculated correctly"""
       # Arrange: Mix of direct and inferred items
       # Act: Calculate ratio
       # Assert: Ratio matches expected (e.g., 2/10 = 0.2)
   ```

2. **Verification Service Tests** (`test_verification_service.py`)
   ```python
   def test_verify_bullet_against_source():
       """Verify claim classification"""
       # Arrange: Bullet + source with matching evidence
       # Act: Verify bullet
       # Assert: Status = VERIFIED, confidence high

   def test_detect_unsupported_claim():
       """Verify hallucination detection"""
       # Arrange: Bullet with claim not in source
       # Act: Verify bullet
       # Assert: Status = UNSUPPORTED, hallucination_detected = True

   @pytest.mark.asyncio
   async def test_parallel_verification():
       """Verify parallel execution"""
       # Arrange: 3 bullets
       # Act: Verify in parallel
       # Assert: Completes in <1s (faster than 3 × 0.7s sequential)
   ```

3. **Confidence Threshold Tests** (`test_confidence_thresholds.py`)
   ```python
   def test_multi_signal_confidence_calculation():
       """Verify confidence combines signals correctly"""
       # Arrange: extraction=0.8, generation=0.7, verification=0.9
       # Act: Calculate overall
       # Assert: 0.30*0.8 + 0.20*0.7 + 0.50*0.9 = 0.83

   def test_unsupported_claim_penalty():
       """Verify unsupported claim downgrades confidence"""
       # Arrange: Bullet with confidence=0.8, 1 UNSUPPORTED claim
       # Act: Apply penalty
       # Assert: Confidence reduced to ≤0.65
   ```

**Frontend:**

4. **Confidence Badge Tests** (`ConfidenceBadge.test.tsx`)
   ```typescript
   it('renders high confidence with green indicator', () => {
     render(<ConfidenceBadge confidence={0.85} tier="high" />);
     expect(screen.getByText('✓')).toBeInTheDocument();
     expect(screen.getByText('High confidence')).toHaveClass('text-green-600');
   });

   it('renders low confidence with amber warning', () => {
     render(<ConfidenceBadge confidence={0.62} tier="low" />);
     expect(screen.getByText('⚠')).toBeInTheDocument();
     expect(screen.getByText('Low confidence')).toHaveClass('text-amber-600');
   });
   ```

5. **Review Modal Tests** (`ReviewModal.test.tsx`)
   ```typescript
   it('calls onApprove when approve button clicked', () => {
     const onApprove = jest.fn();
     render(<ReviewModal bullet={mockBullet} onApprove={onApprove} />);

     fireEvent.click(screen.getByText('Approve'));
     expect(onApprove).toHaveBeenCalledWith(mockBullet.id);
   });

   it('displays source attribution quote', () => {
     render(<ReviewModal bullet={mockBulletWithSource} />);
     expect(screen.getByText(mockBullet.sourceAttribution.exactQuote)).toBeVisible();
   });
   ```

### Integration Tests (Stage H - After Implementation)

**Backend:**

6. **End-to-End Verification Flow** (`test_verification_integration.py`)
   ```python
   @pytest.mark.django_db
   async def test_bullet_generation_with_verification():
       """Test full generation + verification pipeline"""
       # Arrange: Create artifact with known content
       # Act: Generate bullets → Verify → Get results
       # Assert:
       #   - Verification results included in response
       #   - Low-confidence bullets flagged
       #   - High-confidence bullets auto-approved
   ```

7. **Review Workflow API Tests** (`test_review_api_integration.py`)
   ```python
   @pytest.mark.django_db
   def test_approve_flagged_bullet():
       """Test approve endpoint"""
       # Arrange: Create flagged bullet
       # Act: POST to /bullets/{id}/approve
       # Assert: Bullet status updated, requiresReview = False

   @pytest.mark.django_db
   def test_bulk_approve():
       """Test bulk approve endpoint"""
       # Arrange: Create 3 flagged bullets
       # Act: POST to /bullets/bulk-approve with IDs
       # Assert: All bullets approved, response confirms count
   ```

**Frontend:**

8. **Wizard Integration Tests** (`GenerationWizard.integration.test.tsx`)
   ```typescript
   it('inserts review step when content flagged', async () => {
     mockGenerationAPI.returnFlaggedContent();

     render(<GenerationWizard />);
     await completeSteps(['job', 'artifacts', 'generate']);

     // Should show review step
     expect(screen.getByText('Review Flagged Content')).toBeVisible();
   });

   it('skips review step when all content high confidence', async () => {
     mockGenerationAPI.returnHighConfidenceContent();

     render(<GenerationWizard />);
     await completeSteps(['job', 'artifacts', 'generate']);

     // Should skip directly to finalize
     expect(screen.getByText('Finalize Application')).toBeVisible();
     expect(screen.queryByText('Review')).not.toBeInTheDocument();
   });
   ```

### AI Evaluation (LLM Quality)

**Golden Dataset:**
```python
# File: backend/generation/tests/fixtures/verification_goldens.py

VERIFICATION_GOLDENS = [
    {
        'id': 'gold-001',
        'bullet': 'Led team of 5 engineers in developing microservices platform',
        'source_content': 'Managed 5-person engineering team building microservices architecture',
        'expected_verification': {
            'overall_status': 'VERIFIED',
            'confidence': 0.95,
            'hallucination_risk': 'low'
        }
    },
    {
        'id': 'gold-002',
        'bullet': 'Improved system performance by 50%',
        'source_content': 'Optimized database queries, significant performance gains observed',
        'expected_verification': {
            'overall_status': 'INFERRED',
            'confidence': 0.60,
            'hallucination_risk': 'medium',
            'reason': 'Percentage not explicitly stated'
        }
    },
    {
        'id': 'gold-003',
        'bullet': 'Deployed to AWS with 99.9% uptime',
        'source_content': 'Built REST API with PostgreSQL backend',
        'expected_verification': {
            'overall_status': 'UNSUPPORTED',
            'confidence': 0.30,
            'hallucination_risk': 'high',
            'reason': 'AWS deployment and uptime not mentioned in source'
        }
    },
    # ... 47 more examples for 50-item golden set
]
```

**Evaluation Metrics:**
```python
def evaluate_verification_accuracy():
    """
    Run verification service against golden dataset.

    Metrics:
    - Precision: % of flagged items that are actual hallucinations
    - Recall: % of actual hallucinations that are flagged
    - F1 Score: Harmonic mean of precision and recall
    - Accuracy: % of correct classifications

    Thresholds:
    - Precision ≥0.80 (minimize false positives)
    - Recall ≥0.90 (catch most hallucinations)
    - F1 ≥0.85
    - Accuracy ≥0.88
    """
    results = []
    for gold in VERIFICATION_GOLDENS:
        predicted = await verification_service.verify_single_bullet(
            bullet={'text': gold['bullet']},
            artifact_content=gold['source_content'],
            extracted_evidence=mock_evidence
        )
        results.append({
            'expected': gold['expected_verification']['overall_status'],
            'predicted': predicted.status,
            'match': predicted.status == gold['expected_verification']['overall_status']
        })

    precision = calculate_precision(results)
    recall = calculate_recall(results)
    f1 = 2 * (precision * recall) / (precision + recall)

    assert precision >= 0.80, f"Precision {precision} below threshold"
    assert recall >= 0.90, f"Recall {recall} below threshold"
    assert f1 >= 0.85, f"F1 {f1} below threshold"
```

**A/B Testing Plan:**
```python
# Week 1-2: Baseline with conservative thresholds
# Test A (Control): flag_threshold=0.70
# Measure: False positive rate, user acceptance rate

# Week 3-4: Threshold optimization
# Test B: flag_threshold=0.65 (looser)
# Test C: flag_threshold=0.75 (tighter)
# Measure: Quality vs. user experience trade-off

# Success Criteria:
# - Hallucination rate <5%
# - User acceptance ≥80%
# - False positive rate <30%
```

---

## Telemetry & Metrics

### Dashboards

**1. Content Quality Dashboard**
```
Metrics:
- Hallucination rate (spot checks, target: ≤5%)
- Verification pass rate (target: ≥90%)
- Attribution coverage (target: ≥95%)
- Inferred item ratio (target: ≤20%)
- Confidence score distribution (HIGH/MEDIUM/LOW/CRITICAL %)

Filters:
- By artifact type (PDF, GitHub)
- By bullet type (achievement, technical, impact)
- By time range (last 7d, 30d, 90d)

Visualizations:
- Time series: Hallucination rate trend
- Histogram: Confidence score distribution
- Pie chart: Verification status breakdown (VERIFIED/INFERRED/UNSUPPORTED)
```

**2. Review Workflow Dashboard**
```
Metrics:
- % of content flagged for review
- User acceptance rate (approved / total flagged)
- Average review time per item
- Abandon rate at review step
- Bulk action usage rate

Filters:
- By user segment (new vs. returning)
- By confidence tier
- By artifact type

Visualizations:
- Funnel: Generation → Review → Approval
- Bar chart: Approval vs. rejection rate by confidence tier
- Time series: Review step abandon rate
```

**3. Verification Service Health Dashboard**
```
Metrics:
- Verification latency (P50, P95, P99)
- Error rate (target: <5%)
- Circuit breaker state (CLOSED/OPEN/HALF_OPEN)
- LLM API token usage
- Cost per verification

Alerts:
- P95 latency >3s → Performance degradation
- Error rate >5% → Service health issue
- Circuit breaker OPEN → External dependency failure
```

### Alert Thresholds

**Quality Alerts (Critical):**
- Hallucination rate >7% for 1 hour → Immediate investigation
- Verification pass rate <85% for 1 hour → Prompt quality issue
- Attribution coverage <90% for 1 hour → Extraction problem

**User Experience Alerts (High):**
- >20% of content flagged for 1 hour → Threshold too strict
- User acceptance rate <70% for 1 day → False positive issue
- Review step abandon rate >10% for 1 day → UX problem

**Performance Alerts (Medium):**
- Verification P95 latency >3s → Performance degradation
- Total generation P95 >30s → SLO violation
- Verification error rate >5% → Service reliability issue

**Cost Alerts (Low):**
- Daily LLM cost increase >20% → Usage spike investigation
- Cost per generation >$0.10 → Efficiency review

---

## Edge Cases & Risks

### Edge Cases

**1. Ambiguous Source Content**
- **Case:** Source says "led engineering team" but doesn't specify size
- **Handling:** Mark as inferred, flag for review, provide source quote
- **Test:** Golden example with ambiguous team size

**2. Multiple Contradictory Sources**
- **Case:** Resume says "team of 5", LinkedIn says "team of 3"
- **Handling:** Use user_context as ground truth (ADR-041), flag contradiction
- **Test:** Mock artifact with conflicting sources

**3. Verification Service Timeout**
- **Case:** Verification takes >2s for single bullet
- **Handling:** Timeout protection, mark as unverified, continue generation
- **Test:** Mock slow LLM response, assert graceful degradation

**4. All Bullets Flagged**
- **Case:** User has 10 bullets, all have confidence <0.70
- **Handling:** Bulk review interface, suggest re-uploading better artifacts
- **Test:** Generate low-quality content, verify bulk review works

**5. User Rejects All Flagged Bullets**
- **Case:** User rejects all 3 flagged bullets, no remaining bullets
- **Handling:** Prompt to regenerate or manually add bullets
- **Test:** Rejection flow with zero remaining bullets

**6. Mobile Review Experience**
- **Case:** Review modal on small screen
- **Handling:** Responsive bottom sheet, simplified view
- **Test:** Cypress tests on mobile viewports (375px, 768px)

**7. Non-English Content**
- **Case:** Resume in Chinese, verification prompts in English
- **Handling:** Language detection, multilingual prompts (deferred to v2)
- **Test:** Document limitation, add to roadmap

**8. Very Long Source Quotes**
- **Case:** Achievement source quote is 500+ characters
- **Handling:** Truncate display, show full in expandable section
- **Test:** Mock long quote, verify truncation UI

### Risks

**HIGH RISK: False Positive Rate Too High**
- **Impact:** Users frustrated by excessive flagging, abandon workflow
- **Probability:** Medium (threshold calibration uncertain)
- **Mitigation:** A/B testing, user feedback collection, threshold adjustment
- **Monitoring:** Track user acceptance rate daily, alert if <70%
- **Rollback:** Lower threshold from 0.70 to 0.60 via feature flag

**HIGH RISK: LLM API Failures**
- **Impact:** Verification service unavailable, content unverified
- **Probability:** Low (OpenAI reliability ~99.9%)
- **Mitigation:** Circuit breaker, graceful degradation, caching
- **Monitoring:** Error rate dashboard, circuit breaker state alerts
- **Rollback:** Disable verification via feature flag, proceed without

**MEDIUM RISK: Latency SLO Violation**
- **Impact:** Total generation time exceeds 30s, user experience degrades
- **Probability:** Low (parallel verification, caching)
- **Mitigation:** Performance optimization, timeout protection, monitoring
- **Monitoring:** P95 latency dashboard, alert if >28s
- **Rollback:** Disable verification for 50% of users, analyze performance

**MEDIUM RISK: Hallucination Rate Not Improving**
- **Impact:** Quality targets not met, feature doesn't solve problem
- **Probability:** Low (comprehensive approach, proven techniques)
- **Mitigation:** Iterative prompt refinement, golden dataset testing
- **Monitoring:** Spot check 100 samples bi-weekly, measure hallucination rate
- **Rollback:** Re-evaluate approach, consider alternative techniques

**LOW RISK: User Confusion About Confidence Indicators**
- **Impact:** Users don't understand what confidence means, ignore warnings
- **Probability:** Medium (technical concept for non-technical users)
- **Mitigation:** Clear messaging, tooltips, user education
- **Monitoring:** User feedback, support ticket tracking
- **Rollback:** Simplify indicators, hide numeric scores, focus on tier labels

---

## Rollout Plan

### Phase 1: Backend Foundation (Days 1-5)
- Implement source attribution in ExtractedContent
- Enhance extraction prompts with citation requirements
- Create BulletVerificationService skeleton
- Write unit tests for all components
- Deploy to development environment

**Exit Criteria:**
- All unit tests passing
- Extraction returns source attributions
- Verification service can classify claims
- No regressions in existing functionality

### Phase 2: API & Integration (Days 6-8)
- Add review workflow endpoints
- Integrate verification into generation pipeline
- Write integration tests
- Deploy to staging environment

**Exit Criteria:**
- API endpoints functional and tested
- Verification runs after bullet generation
- Integration tests passing
- Performance within acceptable limits (P95 <25s)

### Phase 3: Frontend (Days 9-12)
- Build confidence indicator components
- Implement review modal
- Integrate into generation wizard
- Write frontend tests
- Deploy to staging environment

**Exit Criteria:**
- Review workflow functional in wizard
- Confidence indicators display correctly
- Approve/reject/edit actions work
- Mobile responsive design verified

### Phase 4: Testing & Calibration (Days 13-15)
- Run golden dataset evaluation
- A/B test confidence thresholds
- Collect user feedback
- Adjust thresholds based on data
- Deploy to production (10% rollout)

**Exit Criteria:**
- Golden dataset metrics meet thresholds (F1 ≥0.85)
- User acceptance rate ≥75% (allowing for calibration)
- No critical bugs reported
- Performance stable

### Phase 5: Full Rollout (Days 16-17)
- Gradual rollout: 10% → 25% → 50% → 100%
- Monitor quality metrics
- Collect feedback
- Document learnings

**Exit Criteria:**
- All quality metrics met
- User satisfaction maintained
- System stable at 100% rollout
- Documentation updated

---

## Success Criteria (4 Weeks Post-Launch)

### Quality Metrics (P0 - Must Achieve)
- ✅ Hallucination rate ≤5% (from baseline ~15%)
- ✅ Verification pass rate ≥90%
- ✅ Source attribution coverage ≥95%
- ✅ User acceptance rate ≥80% for flagged content

### User Experience Metrics (P1 - High Priority)
- ✅ <15% of content flagged for review
- ✅ Average review time <90 seconds per item
- ✅ <5% abandon rate at review step
- ✅ User satisfaction score ≥4/5 for feature

### Performance Metrics (P1 - High Priority)
- ✅ P95 generation latency ≤25s (including verification)
- ✅ P95 verification latency ≤2.5s for 3 bullets
- ✅ Review modal load time <1s (P95)
- ✅ API response time <500ms (P95)

### Reliability Metrics (P2 - Medium Priority)
- ✅ Verification service error rate <5%
- ✅ Zero frontend crashes related to feature
- ✅ Graceful degradation functional (tested)
- ✅ Circuit breaker prevents cascade failures

### Business Metrics (P3 - Nice to Have)
- 📊 Cost per generation increase <15% ($0.021 target)
- 📊 User retention unchanged or improved
- 📊 Support tickets related to content quality -50%
- 📊 NPS score maintained or improved

---

## Traceability

**Git Branch:** `feat/ft-030-anti-hallucination-improvements`

**Pull Request:** `[ft-030] Anti-Hallucination Quality Improvements`

**Commit Convention:** `<type>(scope): message (#ft-030)`

**Examples:**
- `feat(llm): add source attribution to extraction (#ft-030)`
- `feat(generation): implement bullet verification service (#ft-030)`
- `feat(api): add review workflow endpoints (#ft-030)`
- `feat(frontend): create review modal components (#ft-030)`
- `test(verification): add unit tests for claim classification (#ft-030)`

**Issue Tracking:** Reference `ft-030` in all related issues, PRs, and documentation.

---

## Implementation Notes

**Critical Path:**
1. Source attribution (blocks verification)
2. Verification service (blocks review workflow)
3. Confidence thresholds (blocks flagging logic)
4. Review workflow (blocks frontend integration)

**Dependencies:**
- All 4 ADRs must be approved before implementation
- Backend changes before frontend (API contract)
- Unit tests before implementation (TDD)

**Feature Flags:**
- `verification_service` - Enable/disable verification layer
- `confidence_based_flagging` - Enable/disable review workflow
- `confidence_indicators` - Show/hide confidence badges

**Monitoring:**
- Set up dashboards before rollout
- Configure alerts for all metrics
- Establish baseline measurements

**Documentation:**
- Update README with new workflow
- Create user guide for review interface
- Document confidence scoring logic
- Add troubleshooting guide

---

**Status:** Ready for CHECKPOINT #3 (Tests Complete - Stage F)

**Next Steps:**
1. Get approval for this FEATURE spec
2. Proceed to Stage F: Write failing unit tests (TDD RED phase)
3. Implement Stage G: Make tests pass (TDD GREEN phase)
4. Complete Stage H: Integration tests + refactoring (TDD REFACTOR phase)
