# ADR-041: Source Attribution Schema for Extracted Content

**File:** docs/adrs/adr-041-source-attribution-schema.md
**Status:** Draft
**Date:** 2025-11-04
**Decision Makers:** Engineering, ML Team
**Related:** PRD v1.4.0, spec-llm.md v4.0.0, ft-030-anti-hallucination-improvements.md

## Context

Current evidence extraction system (EvidenceContentExtractor) extracts technologies, achievements, and summaries from PDF and GitHub sources, but lacks source attribution. This results in:

**Problem 1: Untraceable Claims**
- Generated bullet points contain claims that cannot be verified against source documents
- No way to trace a claim like "Led team of 5 engineers" back to its origin
- Users cannot verify accuracy of generated content
- Baseline hallucination rate: ~15% (from investigation in ft-030)

**Problem 2: Inability to Detect Hallucinations**
- No distinction between explicitly stated facts vs. reasonable inferences
- LLM may "fill in gaps" or "improve" metrics without source backing
- Example: Source says "optimized API" → LLM generates "improved API performance by 40%"
- No automated way to fact-check generated content

**Problem 3: Low Confidence Detection**
- Current confidence scoring based only on content presence, not source quality
- Cannot identify when extraction is uncertain or based on interpretation
- No mechanism to flag potentially inaccurate extractions for review

**Requirements from PRD v1.4.0:**
- Hallucination rate ≤5% (from baseline ~15%)
- Source attribution accuracy ≥95%
- All claims traceable to source documents
- Confidence scoring that reflects source quality

## Decision

Implement a comprehensive **Source Attribution Schema** for all extracted content:

### 1. SourceAttribution Dataclass

```python
@dataclass
class SourceAttribution:
    """
    Source attribution for a single extracted claim.
    """
    source_type: str                  # 'pdf', 'github', 'web'
    source_location: str              # Page number, file path, or URL
    exact_quote: Optional[str]        # Verbatim text from source (required for achievements)
    section_heading: Optional[str]    # Section where found (e.g., "Work Experience")
    confidence: float                 # 0.0-1.0 confidence in this attribution
    attribution_type: str             # 'direct' or 'inferred'
    hallucination_risk: str           # 'low', 'medium', 'high'
```

### 2. Enhanced ExtractedContent Schema

```python
@dataclass
class ExtractedContent:
    # Existing fields
    source_type: str
    source_url: Optional[str]
    success: bool
    data: Dict[str, Any]
    confidence: float
    processing_cost: float

    # NEW: Source attribution fields
    source_attributions: List[SourceAttribution]  # One per extracted item
    attribution_coverage: float                    # % of items with attribution (≥95%)
    inferred_item_ratio: float                     # % of inferred items (≤20%)
    verification_metadata: Dict[str, Any]          # For verification service
```

### 3. Enhanced Extraction Output Format

```json
{
  "technologies": [
    {
      "name": "PostgreSQL",
      "source_attribution": {
        "source_type": "pdf",
        "source_location": "page 2, paragraph 3",
        "exact_quote": "Designed PostgreSQL database schema for e-commerce platform",
        "section_heading": "Work Experience",
        "confidence": 1.0,
        "attribution_type": "direct",
        "hallucination_risk": "low"
      }
    },
    {
      "name": "REST APIs",
      "source_attribution": {
        "source_type": "pdf",
        "source_location": "page 2, inferred from 'API endpoints'",
        "exact_quote": "Built API endpoints for product catalog",
        "section_heading": "Work Experience",
        "confidence": 0.7,
        "attribution_type": "inferred",
        "hallucination_risk": "medium"
      }
    }
  ],
  "achievements": [
    {
      "text": "Improved API response time by 40%",
      "metrics": {
        "latency_improvement": "40%",
        "baseline": "500ms",
        "target": "300ms"
      },
      "source_attribution": {
        "source_type": "pdf",
        "source_location": "page 2, Work Experience section",
        "exact_quote": "Optimized database queries, reducing API latency from 500ms to 300ms (40% improvement)",
        "section_heading": "Senior Backend Engineer",
        "confidence": 0.95,
        "attribution_type": "direct",
        "hallucination_risk": "low"
      }
    }
  ],
  "attribution_coverage": 0.95,
  "inferred_item_ratio": 0.15
}
```

### 4. Updated Extraction Prompts

Modify LLM prompts to require source attribution (see Prompt Set v2.0 in spec-llm.md v4.0.0):

- **CRITICAL RULE**: "Extract ONLY information explicitly stated in the document"
- **REQUIRED**: Source quote for every achievement
- **REQUIRED**: Page/section location for every item
- **REQUIRED**: Confidence score per item
- **REQUIRED**: Classification as 'direct' or 'inferred'

## Consequences

### Positive

**Traceability (+++):**
- Every claim can be traced back to source document
- Users can verify accuracy of generated content
- Enables automated fact-checking via BulletVerificationService
- Supports hallucination detection and prevention

**Quality Improvement (++):**
- Enhanced confidence scoring factors in source quality
- Ability to flag uncertain extractions for review
- Distinction between direct facts vs. inferences
- Expected 70% reduction in hallucination rate (15% → <5%)

**Debugging & Monitoring (+):**
- Easy to identify which sources produce low-quality extractions
- Can track attribution coverage and inferred item ratios
- Helps refine extraction prompts based on attribution quality

**User Trust (++):**
- Users can see evidence backing each claim
- Transparency about confidence levels
- Clear indicators when claims are inferences vs. direct quotes

### Negative

**Increased Complexity (-):**
- More complex data structures to manage
- Additional fields in extraction outputs
- Requires updates to all services consuming ExtractedContent

**Latency Impact (-):**
- Slightly longer LLM responses (attribution data adds ~20% tokens)
- Estimated +0.5-1s per extraction
- Still within 30s SLO for total generation

**Cost Increase (-):**
- ~20% more tokens per extraction for attribution data
- Estimated +$0.003 per artifact extraction
- Acceptable for quality improvement

**Migration Required (-):**
- Existing ExtractedContent data lacks attribution
- Need to handle legacy data gracefully
- Nullable fields for backward compatibility

## Alternatives

### Alternative 1: Post-hoc Attribution (Rejected)

**Idea**: Extract content normally, then add attribution in separate step.

**Rejected because**:
- Two LLM calls instead of one (higher cost, latency)
- Attribution may not align with extracted items
- No benefit to prompt quality improvements from upfront attribution requirement

### Alternative 2: Lightweight Attribution (Page Number Only) (Rejected)

**Idea**: Only require page numbers, skip exact quotes and detailed metadata.

**Rejected because**:
- Cannot verify specific claims without quotes
- Insufficient for fact-checking service
- Page-level attribution too coarse for multi-claim pages

### Alternative 3: Optional Attribution (Rejected)

**Idea**: Make attribution optional, only for high-confidence items.

**Rejected because**:
- Defeats purpose of preventing hallucinations
- Cannot calculate attribution coverage consistently
- Low-confidence items are where attribution matters most

## Rollback Plan

**Phase 1: Graceful Degradation**
- Make all new attribution fields optional in data models
- Handle missing attribution data gracefully in consuming services
- Allow ExtractedContent without source_attributions

**Phase 2: Feature Flag**
- Add `feature.source_attribution_enabled` flag
- When disabled, extraction uses old prompts without attribution requirements
- Verification service disabled when attribution unavailable

**Phase 3: Data Migration**
- Existing ExtractedContent without attribution marked as `legacy`
- New extractions always include attribution
- No need to backfill legacy data (re-extract on next enrichment)

**Rollback Trigger**: If attribution adds >3s latency or hallucination rate doesn't improve after 2 weeks of A/B testing.

## Implementation Notes

### Database Schema

No database migrations required - attribution data stored in JSON fields:

```sql
-- ExtractedContent already stored as JSON in enhanced_evidence table
-- New attribution fields fit within existing JSON structure
-- No ALTER TABLE statements needed
```

### API Changes

**Backward Compatible**: Existing API consumers don't break if they ignore new fields.

**New Fields in Responses**:
- `source_attributions`: Array of attribution objects
- `attribution_coverage`: Float (0.0-1.0)
- `inferred_item_ratio`: Float (0.0-1.0)

### Performance Testing

Before rollout, measure:
- Extraction latency impact (target: <+1s)
- Token usage increase (target: <25%)
- Attribution coverage achieved (target: ≥95%)
- Inferred item ratio (target: ≤20%)

### Success Metrics

After 2 weeks of production use:
- Attribution coverage ≥95%
- Inferred item ratio ≤20%
- Hallucination rate ≤5% (measured via verification service)
- User acceptance rate ≥80% for flagged items
- No user complaints about increased latency

## Links

**Related Documents:**
- **PRD**: `docs/prds/prd.md` v1.4.0 (anti-hallucination requirements)
- **TECH-SPEC**: `docs/specs/spec-llm.md` v4.0.0 (source attribution schema)
- **FEATURE**: `docs/features/ft-030-anti-hallucination-improvements.md` (planned)
- **RELATED ADRs**:
  - `adr-042-verification-architecture.md` (uses source attribution for fact-checking)
  - `adr-043-confidence-thresholds.md` (enhanced confidence scoring)
  - `adr-044-review-workflow-ux.md` (displays attribution to users)

**Prior Art:**
- None directly relevant, but inspired by:
  - Bing AI's citation system
  - Google Search's source attribution
  - Scientific paper citation standards
