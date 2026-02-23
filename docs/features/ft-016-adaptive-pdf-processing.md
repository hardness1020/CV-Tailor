# Feature — 016 Adaptive PDF Processing

**File:** docs/features/ft-016-adaptive-pdf-processing.md
**Owner:** ML/Backend Team
**ID:** ft-016
**TECH-SPECs:** `spec-llm.md` (v3.2.0), `spec-artifact-upload-enrichment-flow.md` (v1.3.0)
**PRD:** `docs/prds/prd.md`
**Related Features:** ft-005-multi-source-artifact-preprocessing.md
**Discovery:** Codebase discovery completed (Stage B)
**Status:** Planning
**Type:** Medium (Multi-component enhancement, new database fields, no new services)

---

## Summary

Implement adaptive PDF document processing that classifies documents into 5 categories (resume, certificate, research paper, project report, academic thesis) and applies type-specific extraction strategies. This enhancement addresses the current limitation where all PDFs receive identical processing (10K character limit), which produces poor summaries for large documents like theses while wasting tokens on small documents like certificates.

**Key Impact:**
- Summary quality for theses: Poor (1-sentence) → Comprehensive (multi-chapter)
- Token efficiency for certificates: -50% cost savings
- Classification accuracy: >90% for all document types
- Processing time for theses: +200% (justified by 30x better quality)

**Deployment:** Backward-compatible enhancement with database migration

---

## Existing Implementation Analysis

**From Stage B Discovery:**

### Current Limitations

**Current Implementation:** `llm_services/services/core/evidence_content_extractor.py:166-310`

**Fixed Processing Limits** (lines 185-191):
```python
# Current implementation
for chunk in pdf_chunks[:20]:  # Only first 20 chunks
    full_text += chunk.get('content', '') + "\n\n"

if len(full_text) > 10000:  # Hard limit: 10K chars
    full_text = full_text[:10000] + "..."
```

**Quality Impact:**
- **Academic theses** (2MB, 200 pages): Only 1% of content processed → Poor summaries
- **Certificates** (50KB, 1 page): Full content processed but over-allocated tokens → Wasted cost
- **Research papers** (500KB, 15 pages): Missing key sections (methodology, results) → Incomplete extraction
- **No document type awareness**: All documents treated identically

### Reusable Components Identified

| Component | Location | Reuse Strategy |
|-----------|----------|----------------|
| **EvidenceContentExtractor** | `llm_services/services/core/evidence_content_extractor.py` | Enhance `extract_pdf_content()` method |
| **DocumentLoaderService** | `llm_services/services/core/document_loader_service.py` | Use `extract_pdf_basic_metadata()` (line 578) |
| **BaseLLMService** | `llm_services/services/base/base_service.py` | Inherit for new PDFDocumentClassifier |
| **APIClientManager** | `llm_services/services/base/client_manager.py` | Use for LLM-based classification |
| **PerformanceTracker** | `llm_services/services/reliability/performance_tracker.py` | Track classification + extraction metrics |
| **extract_pdf_metadata()** | `artifacts/tasks.py:320` | Already provides page_count, file_size |

### Patterns to Follow

**Service Layer Pattern** (from `llm_services/` architecture):
```
base/            # BaseLLMService
  ↓
infrastructure/  # NEW: PDFDocumentClassifier
  ↓
core/            # ENHANCED: EvidenceContentExtractor.extract_pdf_content()
```

**Agent-Based Adaptive Processing** (from ft-013):
- Classify first (reconnaissance)
- Select strategy based on classification
- Adaptive resource allocation (token budgets)
- Confidence scoring throughout

### Code to Modify

**File:** `llm_services/services/core/evidence_content_extractor.py`

**Method:** `extract_pdf_content()` (lines 166-310)
- **Action:** Enhance with classification + adaptive strategies
- **Backward Compatibility:** Keep existing signature unchanged
- **Risk:** Low (enhancement only, no breaking changes)

**New File:** `llm_services/services/infrastructure/pdf_document_classifier.py`
- **Action:** Create new classifier service
- **Layer:** Infrastructure (supporting component)
- **Pattern:** Follows BaseLLMService pattern

### Dependencies

**Hard Dependencies:**
- `DocumentLoaderService.extract_pdf_basic_metadata()` - PDF metadata extraction
- `APIClientManager` - LLM calls for classification (GPT-5-mini)
- `BaseLLMService` - Base class with circuit breaker + tracking
- `PerformanceTracker` - Cost tracking, latency monitoring

**Database Dependencies:**
- `EnhancedEvidence` model - Add `document_category`, `classification_confidence` fields
- Migration required: ALTER TABLE (backward compatible)

**No Dependencies On:**
- `TailoredContentService` (CV generation, not extraction)
- `ArtifactRankingService` (job matching, not document classification)
- `BulletGenerationService` (generation app, separate from llm_services)

---

## Acceptance Criteria

### Functional Requirements

- [ ] **PDF Classification:** System classifies PDFs into 5 categories with >90% accuracy
  - Resume/CV (1-5 pages)
  - Certificate (1-3 pages)
  - Research Paper (5-20 pages)
  - Project Report (10-50 pages)
  - Academic Thesis (50+ pages)

- [ ] **Adaptive Processing:** Each document type receives appropriate token budget
  - Resumes: 50K chars max (current baseline)
  - Certificates: 10K chars max (-50% tokens)
  - Research Papers: 100K chars max (+100% for quality)
  - Project Reports: 150K chars max
  - Academic Theses: 300K chars max (+2900% for comprehensive extraction)

- [ ] **Map-Reduce Summarization:** Large documents (theses) processed in sections
  - Phase 1 (Map): Extract content from each chapter independently
  - Phase 2 (Reduce): Aggregate chapter summaries into comprehensive overview
  - Section-aware chunking preserves context boundaries

- [ ] **Summary Quality:** Significant improvement for large documents
  - Theses: From 1-sentence to comprehensive multi-paragraph summaries
  - Papers: Include abstract, methodology, results, conclusion
  - Reports: Cover all major sections (intro, implementation, results)

- [ ] **Backward Compatibility:** Existing PDFs re-classified without data loss
  - Migration assigns default category ('resume') to existing records
  - Re-enrichment triggered for existing documents (user-initiated)

### Non-Functional Requirements

- [ ] **Processing Time:** Adaptive limits appropriate for document size
  - Certificates: <30s (faster than current)
  - Resumes: <60s (same as current)
  - Papers: <120s (acceptable for quality gain)
  - Reports: <180s
  - Theses: <600s (10 min for 200+ pages is reasonable)

- [ ] **Classification Accuracy:** >90% correct category assignment
  - Rule-based classifier: >85% accuracy (fast path)
  - LLM refinement: >95% accuracy (high confidence)
  - Confidence scoring: Report classification confidence to users

- [ ] **Cost Efficiency:** Net neutral or positive cost impact
  - Small documents (50% of uploads): 50% cost reduction
  - Large documents (5% of uploads): Increased cost justified by quality
  - Overall: Break-even or slight cost reduction

- [ ] **Database Performance:** New fields indexed, queries optimized
  - `document_category` indexed for filtering
  - Backward compatible (nullable fields)
  - Migration completes in <5 min for existing data

---

## Design Changes

### API Endpoints

**No New Endpoints** - Enhancement to existing enrichment flow

**Modified Response:**
```python
GET /api/v1/artifacts/{id}/enhanced-evidence/

# Enhanced response includes:
{
    "id": "uuid",
    "title": "published_thesis.pdf",
    "content_type": "document",
    "document_category": "academic_thesis",  # NEW
    "classification_confidence": 0.95,       # NEW
    "processed_content": {
        "technologies": [...],
        "achievements": [...],
        "summary": "Comprehensive multi-paragraph summary..."  # ENHANCED
    },
    "processing_confidence": 1.0
}
```

### Database Schema Changes

```sql
-- Add document classification fields to enhanced_evidence
ALTER TABLE enhanced_evidence
ADD COLUMN document_category VARCHAR(50) DEFAULT NULL,
ADD COLUMN classification_confidence FLOAT DEFAULT NULL;

-- Create index for category-based queries
CREATE INDEX idx_enhanced_evidence_category
ON enhanced_evidence(document_category);

-- Backward compatibility: Update existing records
UPDATE enhanced_evidence
SET document_category = 'resume'
WHERE document_category IS NULL AND content_type = 'document';
```

**Impact:**
- **Backward Compatible:** Nullable fields, existing queries unchanged
- **Performance:** Indexed for fast category filtering
- **Data Migration:** Existing records default to 'resume' category

### Service Architecture Changes

**New Component:**
```
llm_services/services/infrastructure/
└── pdf_document_classifier.py        # NEW: PDF type classifier
    ├── PDFDocumentClassifier
    ├── classify_document()            # Main classification method
    ├── _classify_by_rules()           # Fast rule-based classification
    ├── _classify_with_llm()           # LLM refinement for low confidence
    └── _get_processing_strategy()     # Return adaptive config
```

**Enhanced Component:**
```
llm_services/services/core/
└── evidence_content_extractor.py     # ENHANCED
    ├── __init__()                     # Add self.pdf_classifier
    ├── extract_pdf_content()          # ENHANCED with adaptive processing
    ├── _map_reduce_extraction()       # NEW: For large documents
    ├── _select_section_aware_chunks() # NEW: Section-based sampling
    └── _adaptive_chunk_selection()    # NEW: Smart chunk selection
```

### Processing Flow

```
PDF Upload → Extract Metadata (page_count, file_size)
    ↓
PDFDocumentClassifier.classify_document()
    ├── Rule-based classification (fast, 85% accuracy)
    └── LLM refinement if confidence < 0.7 (95% accuracy)
    ↓
Get Processing Strategy for Category
    ├── certificate: 10K chars, full sampling
    ├── resume: 50K chars, full sampling
    ├── paper: 100K chars, section-aware sampling
    ├── report: 150K chars, heading-aware sampling
    └── thesis: 300K chars, map-reduce
    ↓
EvidenceContentExtractor.extract_pdf_content()
    ├── Adaptive chunk selection based on strategy
    ├── Map-reduce for theses (chapter-by-chapter)
    ├── Section-aware for papers (abstract, results, conclusion)
    └── Full content for small documents
    ↓
Store Enhanced Evidence with document_category
```

---

## Test & Eval Plan

### Unit Tests

**Test File:** `backend/llm_services/tests/unit/services/infrastructure/test_pdf_document_classifier.py`

Test Cases:
- [ ] **Rule-based classification accuracy** (page_count + file_size + keywords)
  - 1-page certificate → 'certificate' (confidence >0.8)
  - 2-page resume → 'resume' (confidence >0.8)
  - 15-page paper → 'research_paper' (confidence >0.8)
  - 30-page report → 'project_report' (confidence >0.7)
  - 200-page thesis → 'academic_thesis' (confidence >0.9)

- [ ] **LLM refinement triggers** for low confidence cases
  - Confidence <0.7 → LLM classification called
  - Mock LLM response → correct category returned

- [ ] **Strategy selection** matches category
  - Each category returns correct DOCUMENT_STRATEGIES config

**Test File:** `backend/llm_services/tests/unit/services/core/test_evidence_content_extractor_adaptive.py`

Test Cases:
- [ ] **Adaptive chunk selection** based on document type
  - Certificate: Selects all chunks (≤10)
  - Thesis: Selects 300 chunks with chapter boundaries

- [ ] **Map-reduce extraction** for large documents
  - Thesis with 10 chapters → 10 map operations + 1 reduce
  - Section summaries correctly aggregated

- [ ] **Backward compatibility** with existing code
  - Can still process PDFs without classification
  - Falls back to default strategy if classification fails

### Integration Tests

**Test File:** `backend/llm_services/tests/integration/test_adaptive_pdf_pipeline.py`

End-to-End Scenarios:
- [ ] **Certificate processing** (1-page completion certificate)
  - Classification: 'certificate' with >0.8 confidence
  - Tokens used: <5,000 (50% reduction)
  - Summary: Brief, complete extraction

- [ ] **Resume processing** (2-page professional CV)
  - Classification: 'resume' with >0.8 confidence
  - Tokens used: ~10,000 (baseline)
  - Summary: Professional experience extracted

- [ ] **Thesis processing** (200-page dissertation)
  - Classification: 'academic_thesis' with >0.9 confidence
  - Tokens used: ~300,000 (30x increase justified)
  - Summary: Comprehensive multi-chapter summary with achievements

- [ ] **Migration testing** (existing records)
  - Existing enhanced_evidence records have default category
  - Re-enrichment assigns correct categories
  - No data loss during migration

### Golden Test Cases

```python
GOLDEN_TEST_CASES = [
    {
        'name': 'one_page_certificate',
        'file': 'test_fixtures/aws_certification.pdf',
        'expected_category': 'certificate',
        'expected_confidence': 0.9,
        'expected_tokens': 5000,
        'expected_summary_length': 100,  # words
    },
    {
        'name': 'two_page_resume',
        'file': 'test_fixtures/software_engineer_resume.pdf',
        'expected_category': 'resume',
        'expected_confidence': 0.85,
        'expected_tokens': 10000,
        'expected_summary_length': 200,
    },
    {
        'name': 'research_paper',
        'file': 'test_fixtures/ml_research_paper.pdf',
        'expected_category': 'research_paper',
        'expected_confidence': 0.85,
        'expected_tokens': 25000,
        'expected_summary_length': 300,
        'expected_sections': ['abstract', 'methodology', 'results'],
    },
    {
        'name': 'phd_thesis',
        'file': 'test_fixtures/published_thesis.pdf',  # Real 200-page thesis
        'expected_category': 'academic_thesis',
        'expected_confidence': 0.9,
        'expected_tokens': 300000,
        'expected_summary_length': 500,
        'expected_achievements_count': 5,
    }
]
```

### Evaluation Metrics

**Classification Accuracy:**
- Measured against manually labeled test set (100 PDFs, 20 per category)
- Target: >90% accuracy across all categories
- Metric: Category precision, recall, F1 score

**Summary Quality:**
- Human evaluation on 5-point scale (20 samples)
- Target: Average score >4.0 for all document types
- Metric: Fluency, completeness, relevance

**Cost Efficiency:**
- Track token usage per document type
- Target: Net neutral or positive cost impact
- Metric: Average cost per document type vs. baseline

---

## Telemetry & Metrics

### Dashboards

**PDF Classification Metrics:**
```python
# Prometheus metrics
pdf_classification_duration = Histogram(
    'pdf_classification_duration_seconds',
    'Time spent classifying PDF documents',
    ['classification_method']  # 'rule_based' or 'llm_refined'
)

pdf_classification_accuracy = Counter(
    'pdf_classification_total',
    'Total PDF classifications',
    ['predicted_category', 'actual_category']  # For accuracy tracking
)

pdf_classification_confidence = Histogram(
    'pdf_classification_confidence',
    'Confidence scores for PDF classification',
    ['category']
)
```

**Adaptive Processing Metrics:**
```python
pdf_processing_tokens = Histogram(
    'pdf_processing_tokens_used',
    'Tokens used per PDF document',
    ['document_category']
)

pdf_processing_duration = Histogram(
    'pdf_processing_duration_seconds',
    'Time spent processing PDF by category',
    ['document_category', 'sampling_strategy']
)

pdf_processing_success_rate = Counter(
    'pdf_processing_total',
    'Total PDF processing attempts',
    ['document_category', 'status']  # 'success' or 'failure'
)
```

### Alerts

- **Classification accuracy** <85% (P2 alert) → Investigate rule tuning
- **Thesis processing time** >15 min (P2 alert) → Check map-reduce efficiency
- **Cost per thesis** >$2.00 (P2 alert) → Review token allocation
- **LLM refinement rate** >50% (P2 alert) → Improve rule-based classifier

---

## Edge Cases & Risks

### Classification Challenges

**Risk:** Ambiguous documents (e.g., technical report vs. research paper)
**Mitigation:** LLM refinement for confidence <0.7, user override option

**Risk:** Scanned PDFs (image-only, no text extraction)
**Mitigation:** OCR fallback, graceful degradation to 'certificate' category

**Risk:** Multi-language documents (non-English)
**Mitigation:** Keyword detection supports multiple languages, LLM handles classification

### Processing Failures

**Risk:** Map-reduce timeout for extremely large theses (500+ pages)
**Mitigation:** Configurable timeout limits, chunking strategy adjusts dynamically

**Risk:** Section detection fails (no clear chapter boundaries)
**Mitigation:** Fallback to sequential chunking with larger character limits

**Risk:** LLM API rate limits during batch re-enrichment
**Mitigation:** Queue-based processing with exponential backoff

### Data Migration Issues

**Risk:** Existing enhanced_evidence records require re-classification
**Mitigation:** Background task for re-classification, user-initiated re-enrichment

**Risk:** Migration fails mid-execution
**Mitigation:** Transaction-based migration, rollback capability

---

## Rollout Plan

### Phase 1: Infrastructure Deployment (Week 1)

**Objectives:**
- Deploy database migration (add document_category fields)
- Deploy PDFDocumentClassifier service
- Feature flag: `feature.adaptive_pdf_processing` (default: OFF)

**Rollout:**
1. Run database migration in staging
2. Deploy PDFDocumentClassifier to staging
3. Test classification accuracy with golden dataset
4. Deploy to production with feature flag OFF

### Phase 2: Canary Testing (Week 2)

**Objectives:**
- Enable adaptive processing for 10% of new PDF uploads
- Monitor classification accuracy and processing metrics
- Validate cost impact

**Rollout:**
1. Enable feature flag for 10% of users
2. Monitor dashboards for 48 hours
3. If metrics meet targets, increase to 50%
4. Continue monitoring for 48 hours

### Phase 3: Full Deployment (Week 3)

**Objectives:**
- Enable adaptive processing for 100% of new uploads
- Begin batch re-classification of existing records

**Rollout:**
1. Enable feature flag for all users
2. Trigger background re-classification task
3. Monitor completion rate and quality metrics
4. Address any issues discovered

### Phase 4: Migration Completion (Week 4)

**Objectives:**
- Complete re-classification of all existing PDFs
- Remove legacy processing code
- Update documentation

**Feature Flags:**
- `feature.adaptive_pdf_processing` - Enable adaptive processing (default: ON after Phase 3)
- `feature.pdf_reclassification` - Enable batch re-classification (default: OFF)
- `feature.map_reduce_extraction` - Enable map-reduce for theses (default: ON)

### Rollback Plan

**Instant Rollback:**
- Disable `feature.adaptive_pdf_processing` → Reverts to fixed 10K limit

**Partial Rollback:**
- Disable `feature.map_reduce_extraction` → Disables map-reduce, keeps classification

**Full Rollback:**
- Database: `ALTER TABLE enhanced_evidence DROP COLUMN document_category` (data preserved)
- Code: Remove PDFDocumentClassifier, revert EvidenceContentExtractor changes

---

## Success Metrics

**Classification Quality:**
- Accuracy: >90% (measured against manual labels)
- Confidence: Average >0.8 across all categories
- LLM refinement rate: <30% (rule-based handles most cases)

**Extraction Quality:**
- Thesis summary quality: 2.0 → 4.5 (5-point scale)
- User satisfaction: >80% approve re-enriched summaries
- Achievement extraction: >5 achievements per thesis (vs. 1 currently)

**Performance:**
- Certificate processing: <30s (50% faster)
- Thesis processing: <10 min (acceptable for 200+ pages)
- Cost per artifact: Net neutral or -10% reduction

**Adoption:**
- Re-classification completion: 100% of existing PDFs within 30 days
- User-initiated re-enrichment: >50% of thesis owners re-enrich
- Feature flag stability: No rollbacks required

---

## References

- **SPEC:** `docs/specs/spec-llm.md` (v3.2.0)
- **Related Feature:** `docs/features/ft-005-multi-source-artifact-preprocessing.md`
- **Discovery:** Codebase discovery completed in Stage B
- **Pattern Reference:** `docs/features/ft-013-github-agent-traversal.md` (agent-based adaptive processing)
