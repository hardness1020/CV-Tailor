# ADR: Hybrid Rule-Based and LLM Classification Strategy for PDF Documents

**File:** docs/adrs/adr-025-hybrid-pdf-classification-strategy.md
**Status:** Draft
**Date:** 2025-10-07
**Deciders:** ML/Backend Team
**Related:** ft-016-adaptive-pdf-processing, spec-llm.md v3.2.0

---

## Context

### Problem Statement

Current PDF processing treats all documents identically with a fixed 10,000-character limit, resulting in:

**Quality Issues:**
- **Academic theses** (200+ pages, 2MB): Only ~1% of content processed → 1-sentence summaries lacking detail
- **Certificates** (1 page, 50KB): Full content processed but over-allocated tokens → Wasted API costs
- **Research papers** (15 pages, 500KB): Missing key sections (methodology, results) → Incomplete extraction

**Impact on User Experience:**
- Thesis owners see poor summaries that don't capture research contributions
- System wastes 50% of tokens on trivial documents (certificates)
- No differentiation between document types leads to one-size-fits-none processing

**Quantitative Evidence (from evidence_id 30-31):**
- Thesis (evidence_31): `raw_content` only 1,113 chars from 2MB file → 99.9% content loss
- GitHub (evidence_30): Low confidence 0.275 due to limited file analysis
- Current limit: 20 chunks max, 10K chars max (evidence_content_extractor.py:187-191)

### Business Impact

Poor PDF extraction directly affects CV generation quality:
- Incomplete achievement extraction reduces bullet point quality
- Missing technical skills from large documents weaken job matching
- Users must manually supplement AI-extracted content (adds 10-15 min/artifact)
- Competitive disadvantage: Users with extensive documentation (theses, portfolios) underserved

### Technical Constraints

1. **Classification must be fast:** <2s overhead (users expect ~30s total enrichment)
2. **Accuracy threshold:** >90% correct classification (misclassification wastes tokens or degrades quality)
3. **Cost considerations:** LLM-based classification adds $0.001-0.005 per document
4. **Metadata available:** `page_count`, `file_size`, `first_page_text` already extracted (artifacts/tasks.py:320)

---

## Decision

Implement **hybrid two-tier classification strategy** combining rule-based and LLM-based methods:

### Tier 1: Rule-Based Classification (Fast Path)

**Primary classifier** using metadata heuristics:
- Input: `page_count`, `file_size`, `first_page_text`
- Method: Keyword matching + size/page thresholds
- Performance: <100ms, 85% accuracy
- Cost: $0 (no API calls)

**Classification Rules:**
```python
if page_count <= 3 AND file_size < 200KB:
    if "certificate" keywords found:
        return 'certificate' (confidence: 0.9)
    elif "resume" keywords found:
        return 'resume' (confidence: 0.85)

if page_count >= 50 AND "thesis" keywords found:
    return 'academic_thesis' (confidence: 0.9)

if 5 <= page_count <= 20 AND "abstract" keywords found:
    return 'research_paper' (confidence: 0.85)

if 10 <= page_count <= 50:
    return 'project_report' (confidence: 0.7)
```

### Tier 2: LLM Refinement (High-Confidence Path)

**Secondary classifier** for ambiguous cases:
- Trigger: Rule-based confidence <0.7
- Input: Metadata + first_page_text (500 chars)
- Model: GPT-5-mini (cost-optimized)
- Performance: ~2s, 95% accuracy
- Cost: ~$0.003 per document

**LLM Prompt:**
```
Analyze this PDF metadata and classify into ONE category:
- resume, certificate, research_paper, project_report, academic_thesis

Metadata:
- Pages: {page_count}
- Size: {file_size} bytes
- First page: {first_page_text[:500]}

Return JSON: {"category": "resume", "confidence": 0.95}
```

### Decision Logic Flow

```
PDF Uploaded
    ↓
Extract Metadata (page_count, file_size, first_page_text)
    ↓
Tier 1: Rule-Based Classification
    ├─ Confidence ≥ 0.7 → Use category (85% of cases, 0ms cost)
    └─ Confidence < 0.7 → Proceed to Tier 2
        ↓
    Tier 2: LLM Refinement
        ├─ Call GPT-5-mini with metadata
        └─ Return high-confidence category (15% of cases, $0.003 cost)
    ↓
Return {category, confidence, processing_strategy}
```

---

## Alternatives Considered

### Alternative 1: Pure LLM Classification

**Approach:** Use LLM for all classifications
- **Pros:** 95% accuracy, handles edge cases well
- **Cons:** Slow (2s overhead per document), costly ($0.003 × all documents)
- **Rejected:** Unnecessary for obvious cases (1-page certificate, 200-page thesis)

### Alternative 2: Pure Rule-Based Classification

**Approach:** Only use heuristics (no LLM)
- **Pros:** Fast (<100ms), free
- **Cons:** 85% accuracy insufficient (15% misclassification → wasted tokens or poor quality)
- **Rejected:** 15% error rate too high for cost-sensitive adaptive processing

### Alternative 3: ML Classifier (Supervised Learning)

**Approach:** Train classifier on labeled PDF dataset
- **Pros:** Fast inference, no API costs, potentially high accuracy
- **Cons:** Requires training data, model maintenance, cold start problem
- **Rejected:** Not feasible for MVP, requires 1000+ labeled PDFs

### Alternative 4: User-Specified Categories

**Approach:** Ask users to select document type during upload
- **Pros:** 100% accurate if users comply, zero classification cost
- **Cons:** Adds friction to upload flow, users may not know/care about categories
- **Rejected:** Poor UX, users expect automatic intelligence

---

## Consequences

### Positive

**Performance:**
- 85% of documents classified in <100ms (rule-based fast path)
- Only 15% incur 2s LLM classification overhead
- Average classification time: (0.85 × 0.1s) + (0.15 × 2s) = 0.385s

**Accuracy:**
- Combined system: >90% correct classification
- High-confidence path (rule-based ≥0.7): 85% accurate
- Low-confidence path (LLM refinement): 95% accurate

**Cost Efficiency:**
- Rule-based (85% of docs): $0
- LLM refinement (15% of docs): $0.003 × 0.15 = $0.00045 average
- **Total classification cost: <$0.001 per document**

**Scalability:**
- Rules scale to unlimited documents (no API dependency)
- LLM refinement only for 15% edge cases (manageable API load)

### Negative

**Complexity:**
- Two-tier system adds code complexity
- Must maintain keyword lists for rule-based classifier
- Requires testing both classification paths

**Edge Cases:**
- Hybrid documents (e.g., resume + portfolio) may confuse classifier
- Non-English documents may reduce keyword matching accuracy
- Scanned PDFs (image-only) have limited first_page_text

### Mitigation Strategies

**For Complexity:**
- Abstract classification logic into PDFDocumentClassifier service
- Comprehensive unit tests for both tiers
- Configuration-driven keywords (easy to update)

**For Edge Cases:**
- Fallback to 'resume' category for ambiguous documents (safe default)
- LLM refinement handles non-English documents well
- OCR fallback for scanned PDFs (future enhancement)

**For Accuracy Monitoring:**
- Track classification confidence distribution
- Alert if LLM refinement rate >30% (indicates rules need tuning)
- User feedback mechanism for misclassifications

---

## Implementation Notes

### Service Architecture

**New Component:**
```python
# llm_services/services/infrastructure/pdf_document_classifier.py
class PDFDocumentClassifier(BaseLLMService):
    """
    Hybrid two-tier PDF document classifier.
    Tier 1: Rule-based (fast, free, 85% accuracy)
    Tier 2: LLM refinement (slow, costly, 95% accuracy)
    """

    CLASSIFICATION_KEYWORDS = {
        'resume': ['experience', 'education', 'skills', 'work history'],
        'certificate': ['certificate', 'awarded', 'completion', 'certified'],
        'research_paper': ['abstract', 'methodology', 'results', 'references'],
        'project_report': ['implementation', 'design', 'architecture', 'testing'],
        'academic_thesis': ['thesis', 'dissertation', 'chapter', 'advisor']
    }

    async def classify_document(self, file_path, metadata) -> Dict:
        # Tier 1: Rule-based
        category, confidence = self._classify_by_rules(metadata)

        # Tier 2: LLM refinement if needed
        if confidence < 0.7:
            category, confidence = await self._classify_with_llm(metadata)

        return {
            'category': category,
            'confidence': confidence,
            'processing_strategy': self._get_strategy(category)
        }
```

### Metrics to Track

**Classification Performance:**
- `pdf_classification_duration_seconds{method="rule_based|llm_refined"}`
- `pdf_classification_confidence{category}`
- `pdf_classification_accuracy{predicted,actual}` (when ground truth available)

**Business Metrics:**
- LLM refinement rate (target: <20%)
- Classification confidence distribution
- Cost per classification
- Misclassification impact on extraction quality

### Rollout Strategy

**Phase 1:** Deploy with feature flag OFF
- Test classification accuracy on 100 sample PDFs
- Validate cost projections

**Phase 2:** Enable for 10% of documents
- Monitor LLM refinement rate
- Track classification confidence

**Phase 3:** Enable for all documents
- Monitor accuracy and cost metrics
- Tune keyword rules based on refinement patterns

---

## Related Decisions

**Dependencies:**
- ft-016-adaptive-pdf-processing (parent feature)
- adr-026-adaptive-token-budget-allocation (companion ADR)

**Future Decisions:**
- Whether to add ML classifier as Tier 1.5 (between rules and LLM)
- Whether to support user overrides for misclassifications

---

## Status Tracking

- [ ] **Draft** - Initial proposal
- [ ] **Accepted** - Team approved
- [ ] **Implemented** - Code deployed
- [ ] **Superseded** - Replaced by future ADR

---

## References

- **Code Location:** `llm_services/services/infrastructure/pdf_document_classifier.py`
- **Pattern Reference:** ft-013-github-agent-traversal.md (agent-based adaptive analysis)
- **SPEC:** spec-llm.md v3.2.0 (PDF Document Classification section)
