# ADR: Adaptive Token Budget Allocation for PDF Processing

**File:** docs/adrs/adr-026-adaptive-token-budget-allocation.md
**Status:** Draft
**Date:** 2025-10-07
**Deciders:** ML/Backend Team
**Related:** ft-016-adaptive-pdf-processing, spec-llm.md v3.2.0, adr-025-hybrid-pdf-classification-strategy

---

## Context

### Problem Statement

Current PDF processing uses a **fixed 10,000-character limit** for all documents, resulting in severe quality and cost inefficiencies:

**Underallocation for Large Documents:**
- Academic theses (200 pages, 2MB): Only 1% of content extracted → Poor summaries
- Research papers (15 pages, 500KB): Missing methodology, results sections → Incomplete extraction
- Project reports (30 pages, 1MB): Surface-level summaries → No technical depth

**Overallocation for Small Documents:**
- Certificates (1 page, 50KB): Entire document fits in 2,000 chars, but allocated 10,000 → 80% token waste
- Resumes (2 pages, 100KB): Full content fits in 20,000 chars, truncated to 10,000 → Acceptable but could be optimized

**Quantitative Evidence:**
- Thesis example (evidence_31, 2MB file):
  - Current processing: 10,000 chars → 1-sentence summary
  - Needed: 300,000 chars → Comprehensive multi-chapter summary
  - Quality gap: 30x improvement needed

**Cost Impact:**
- 50% of uploads are small documents (certificates, 1-2 page resumes)
- These waste ~50% of allocated tokens
- Large documents (5% of uploads) receive insufficient tokens despite user need

### Business Impact

**User Dissatisfaction:**
- Thesis owners: "AI completely missed my research contributions"
- Portfolio owners: "Summary doesn't reflect the scope of my work"
- Certificate uploads: "Why does a 1-page document take 30 seconds?"

**Competitive Gap:**
- Competitors (Rezi, Kickresume) process large documents more comprehensively
- Our system underserves users with extensive documentation
- Wasteful token spending on trivial documents = higher costs, slower processing

### Technical Constraints

1. **LLM Context Windows:**
   - GPT-5: 128K token context (sufficient for adaptive allocation)
   - Need to stay well below limits for reliable processing

2. **Processing Time:**
   - Users expect <60s for small documents, <10 min for theses
   - Token count correlates with processing time (~1s per 500 tokens)

3. **Cost Considerations:**
   - GPT-5 pricing: TBD (spec-llm.md notes uncertainty)
   - Current monitoring threshold: $0.75/artifact (may need adjustment)
   - Must balance quality vs. cost

4. **Existing Classification System:**
   - adr-025-hybrid-pdf-classification-strategy provides 5 categories
   - Each category has different processing needs

---

## Decision

Implement **document-type-specific token budgets** with adaptive allocation based on classification:

### Token Budget Strategy

| Document Type | Max Characters | Est. Tokens | Rationale |
|---------------|---------------|-------------|-----------|
| **Certificate** | 10,000 | ~2,500 | Full content, minimal waste |
| **Resume** | 50,000 | ~12,500 | Baseline (current quality maintained) |
| **Research Paper** | 100,000 | ~25,000 | Capture abstract + methodology + results |
| **Project Report** | 150,000 | ~37,500 | Cover all major sections comprehensively |
| **Academic Thesis** | 300,000 | ~75,000 | Multi-chapter extraction with map-reduce |

### Processing Strategy Per Document Type

**Certificates (10K chars, -50% tokens):**
```python
{
    'max_chunks': 10,
    'max_chars': 10_000,
    'sampling': 'full',              # Process all content
    'summary_tokens': 500,           # Brief extraction
    'chunk_selection': 'sequential',
    'map_reduce': False
}
```

**Resumes (50K chars, baseline):**
```python
{
    'max_chunks': 50,
    'max_chars': 50_000,
    'sampling': 'full',
    'summary_tokens': 1_000,
    'chunk_selection': 'sequential',
    'map_reduce': False
}
```

**Research Papers (100K chars, +100% tokens for quality):**
```python
{
    'max_chunks': 100,
    'max_chars': 100_000,
    'sampling': 'section_aware',     # Prioritize abstract, methodology, results
    'summary_tokens': 1_500,
    'chunk_selection': 'section_priority',
    'map_reduce': False
}
```

**Project Reports (150K chars, +200% tokens):**
```python
{
    'max_chunks': 150,
    'max_chars': 150_000,
    'sampling': 'adaptive',          # Heading-aware intelligent sampling
    'summary_tokens': 2_000,
    'chunk_selection': 'heading_aware',
    'map_reduce': False
}
```

**Academic Theses (300K chars, +2900% tokens, map-reduce enabled):**
```python
{
    'max_chunks': 300,
    'max_chars': 300_000,
    'sampling': 'map_reduce',        # Process chapters independently
    'summary_tokens': 3_000,
    'chunk_selection': 'chapter_aware',
    'map_reduce': True,
    'map_chunk_size': 50_000,        # 50K chars per chapter
    'reduce_strategy': 'hierarchical'
}
```

### Map-Reduce Strategy for Large Documents

For academic theses, implement **two-phase processing**:

**Phase 1: MAP (Parallel Chapter Processing)**
```python
# Process each chapter/section independently
for section in thesis_sections:
    section_text = extract_text(section, max_chars=50_000)
    section_summary = llm.extract_content(
        text=section_text,
        max_tokens=3_000,
        prompt="Extract achievements, technologies, metrics from this thesis chapter"
    )
    section_summaries.append(section_summary)
```

**Phase 2: REDUCE (Hierarchical Aggregation)**
```python
# Aggregate section summaries into comprehensive overview
final_summary = llm.reduce_summaries(
    summaries=section_summaries,
    max_tokens=3_000,
    prompt="Synthesize these chapter summaries into comprehensive thesis overview"
)
```

**Benefits of Map-Reduce:**
- Preserves chapter context boundaries (no mid-chapter truncation)
- Parallel processing potential (future optimization)
- Better handling of 200+ page documents
- Comprehensive summaries covering full thesis scope

---

## Alternatives Considered

### Alternative 1: Fixed Budget for All Documents

**Approach:** Keep current 10K char limit
- **Pros:** Simple, predictable cost
- **Cons:** Poor quality for large docs, wasteful for small docs
- **Rejected:** Status quo is insufficient

### Alternative 2: User-Configurable Budgets

**Approach:** Let users select "quick" vs. "comprehensive" processing
- **Pros:** User control, flexibility
- **Cons:** Adds complexity to upload flow, users may not understand trade-offs
- **Rejected:** Poor UX, automatic intelligence preferred

### Alternative 3: Dynamic Budget Based on Content Complexity

**Approach:** Analyze first N pages, decide budget based on density
- **Pros:** Optimally tailored to each document
- **Cons:** Requires two-pass processing, complexity, unpredictable costs
- **Rejected:** Over-engineered for MVP

### Alternative 4: Uniform Large Budget (e.g., 500K chars for all)

**Approach:** Allocate maximum budget to all documents
- **Pros:** Best quality for all documents
- **Cons:** Extreme cost (10x increase), slow processing for small docs
- **Rejected:** Economically infeasible

### Alternative 5: Tiered Pricing (Free/Premium Processing)

**Approach:** Free tier gets 10K chars, premium tier gets 300K
- **Pros:** Monetization opportunity
- **Cons:** Creates feature inequality, complex billing
- **Rejected:** Not aligned with product strategy (automatic intelligence for all)

---

## Consequences

### Positive

**Quality Improvements:**
- Theses: 1-sentence summaries → Comprehensive multi-chapter overviews (+3000% detail)
- Papers: Surface summaries → Full abstract + methodology + results (+200% coverage)
- Reports: Generic summaries → Technical depth with architecture details (+100% detail)

**Cost Efficiency:**
- Certificates: 10K → 10K (no change, but better aligned)
- Resumes: 10K → 50K (+400% tokens, justified by full coverage)
- Net impact: -50% waste on small docs, +300% investment in large docs
- **Expected net cost change: ±0% to +10%** (50% of docs save 50%, 5% of docs spend 30x more)

**User Experience:**
- Small docs process faster (<30s vs. 60s) due to reduced overhead
- Large docs provide comprehensive summaries justifying 10 min processing time
- Users see quality appropriate to document type

### Negative

**Increased Complexity:**
- Must maintain 5 different processing configurations
- Map-reduce adds code complexity for theses
- Testing requires golden datasets for all document types

**Processing Time Variance:**
- Certificates: <30s (faster)
- Resumes: ~60s (same)
- Papers: ~120s (slower but acceptable)
- Reports: ~180s
- Theses: <600s (10 min, significant but justified)

**Cost Uncertainty:**
- GPT-5 pricing TBD (spec-llm.md v3.2.0 notes this)
- Current $0.75/artifact threshold may need adjustment
- Large document processing could exceed threshold

### Mitigation Strategies

**For Complexity:**
- Configuration-driven strategies (DOCUMENT_STRATEGIES dict)
- Comprehensive testing with golden datasets
- Gradual rollout with monitoring

**For Processing Time:**
- Show progress indicators for large documents
- Set user expectations upfront ("Processing thesis: ~10 min")
- Async processing with email notifications for theses

**For Cost Management:**
- Monitor cost per document type
- Alert if thesis processing exceeds $2.00
- Configurable budget caps per category

---

## Implementation Notes

### Service Integration

**Enhanced EvidenceContentExtractor:**
```python
class EvidenceContentExtractor(BaseLLMService):
    """Enhanced with adaptive processing."""

    async def extract_pdf_content(self, pdf_chunks, user_id, source_url):
        # Classify document type
        classification = await self.pdf_classifier.classify_document(file_path)
        category = classification['category']
        strategy = classification['processing_strategy']

        # Apply adaptive token budget
        if strategy['sampling'] == 'full':
            selected_chunks = pdf_chunks[:strategy['max_chunks']]
        elif strategy['sampling'] == 'section_aware':
            selected_chunks = self._select_section_aware_chunks(pdf_chunks, strategy)
        elif strategy['sampling'] == 'map_reduce':
            return await self._map_reduce_extraction(pdf_chunks, strategy, user_id)

        # Combine chunks with adaptive limit
        full_text = self._combine_chunks(selected_chunks, strategy['max_chars'])

        # Extract with category-specific token budget
        llm_response = await self._call_llm_for_extraction(
            prompt=self._build_adaptive_prompt(full_text, category),
            max_tokens=strategy['summary_tokens']
        )
```

### Metrics to Track

**Token Usage by Document Type:**
```python
pdf_processing_tokens = Histogram(
    'pdf_processing_tokens_used',
    'Tokens used per PDF document',
    ['document_category']  # certificate, resume, paper, report, thesis
)
```

**Processing Duration by Category:**
```python
pdf_processing_duration = Histogram(
    'pdf_processing_duration_seconds',
    'Time spent processing PDF',
    ['document_category', 'sampling_strategy']
)
```

**Cost per Document Type:**
```python
pdf_processing_cost = Histogram(
    'pdf_processing_cost_usd',
    'Cost per PDF processing',
    ['document_category']
)
```

### Rollout Strategy

**Phase 1: Baseline Validation (Week 1)**
- Deploy with feature flag OFF
- Process 100 sample PDFs (20 per category) with new budgets
- Measure: token usage, processing time, cost per category
- Validate: quality improvement vs. baseline

**Phase 2: Canary (Week 2)**
- Enable for 10% of new PDF uploads
- Monitor: cost per artifact, processing time p95, user satisfaction
- Alert thresholds: cost >$2.00/thesis, time >15 min

**Phase 3: Full Deployment (Week 3)**
- Enable for 100% of new uploads
- Begin batch re-enrichment of existing large documents (theses, reports)

### Success Criteria

**Quality Metrics:**
- Thesis summary quality: 2.0/5 → 4.5/5 (human evaluation)
- Achievement extraction: 1 per thesis → 5+ per thesis
- User satisfaction: >80% approve re-enriched summaries

**Performance Metrics:**
- Certificate processing: <30s (50% faster)
- Thesis processing: <10 min (acceptable for 200+ pages)
- Cost per artifact: Net ±10% variance from baseline

---

## Related Decisions

**Dependencies:**
- adr-025-hybrid-pdf-classification-strategy (provides document categories)
- ft-016-adaptive-pdf-processing (parent feature)

**Impacts:**
- Future pricing decisions will require budget adjustments
- Map-reduce pattern may extend to other document types (large reports)

---

## Status Tracking

- [ ] **Draft** - Initial proposal
- [ ] **Accepted** - Team approved
- [ ] **Implemented** - Code deployed
- [ ] **Superseded** - Replaced by future ADR

---

## References

- **Code Location:** `llm_services/services/core/evidence_content_extractor.py` (enhanced)
- **Configuration:** `DOCUMENT_STRATEGIES` dict in spec-llm.md v3.2.0
- **Pattern Reference:** Map-reduce from distributed systems patterns
- **SPEC:** spec-llm.md v3.2.0 (Processing Strategies section)
