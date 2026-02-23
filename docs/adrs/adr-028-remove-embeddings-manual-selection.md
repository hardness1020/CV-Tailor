# ADR-028: Remove Embeddings and Implement Manual Artifact Selection

**Status:** Accepted
**Date:** 2025-10-16
**Decision Makers:** User, Claude Code
**Technical Story:** Remove embedding/semantic similarity infrastructure in favor of manual artifact selection with keyword-based suggestions

---

## Context and Problem Statement

The CV Tailor application currently uses pgvector-based semantic similarity search to automatically rank and select artifacts for CV generation. This involves:
- OpenAI/Anthropic embedding APIs ($0.0001-0.0004 per 1K tokens)
- pgvector PostgreSQL extension for vector storage and similarity search
- Complex service architecture (EmbeddingService, ArtifactRankingService with semantic strategy)
- Vector database storage (~1.5KB per artifact for embeddings)

**Key Question:** Is the complexity and cost of semantic embedding justified for artifact selection, or would manual user selection with keyword-based suggestions provide better value?

### Current State Analysis

**Embedding Usage:**
1. **Job Description Embedding:** Job desc → OpenAI embedding API → cached in `JobDescriptionEmbedding` table
2. **Artifact Embedding:** Artifact content → OpenAI embedding API → stored in `Artifact.unified_embedding` (1536-dim vector)
3. **Semantic Ranking:** Cosine similarity between job embedding and artifact embeddings
4. **Hybrid Strategy (default):** 70% semantic similarity + 30% keyword overlap

**Issues Identified:**
1. **Low Active Usage:**
   - `ArtifactChunk` model not actively created in current ft-013 enrichment flow
   - Chunk-based similarity is legacy/fallback code (lines 301-338 in artifact_ranking_service.py)
   - No user-facing UI for semantic search beyond automatic ranking

2. **Complexity vs. Value:**
   - Adds 394 lines in EmbeddingService alone
   - Requires pgvector extension (installation/maintenance overhead)
   - 3 database tables + 4 vector columns for a single feature
   - API costs for embedding generation

3. **User Control:**
   - No UI for users to manually select artifacts
   - Users cannot override automatic selection
   - Trust in AI ranking without transparency

4. **Technical Debt:**
   - Multiple models (EnhancedEvidence, ArtifactChunk) no longer align with current architecture
   - Misleading parameter names in embed_artifact_chunks() (line 273-275 comments)
   - Legacy relationship chains for chunk-based similarity

---

## Decision

**We will remove all embedding/semantic similarity infrastructure** and implement **manual artifact selection with keyword-based ranking suggestions**.

### What Will Be Removed

1. **Services:**
   - `EmbeddingService` (394 lines) - ALL embedding generation for jobs and artifacts
   - Semantic ranking methods in `ArtifactRankingService`:
     - `_rank_by_semantic_similarity()`
     - `_get_chunk_based_similarity()`
     - `find_similar_artifacts()`

   **KEEP (Enrichment services, NOT embeddings):**
   - `ArtifactEnrichmentService` - multi-source preprocessing (ft-005)
   - `EvidenceContentExtractor` - LLM-based content extraction
   - `DocumentLoaderService` - document loading
   - `GitHubRepositoryAgent` - GitHub analysis (ft-013)

2. **Database:**
   - `llm_services_jobdescriptionembedding` table (job embedding cache)
   - `llm_services_artifactchunk` table (chunk embeddings for semantic search)
   - `artifacts_artifact.unified_embedding` column (artifact vector embeddings)
   - pgvector extension (vector similarity operations)

   **KEEP (Enrichment-related, NOT embeddings):**
   - `llm_services_enhancedevidence` table - stores enriched content from evidence sources (ft-005)
   - `llm_services_extractedcontent` table - per-source extraction results (ft-005)
   - `llm_services_githubrepositoryanalysis` table - GitHub agent analysis (ft-013)

3. **API Endpoints (REMOVED):**
   - `GET /v1/llm/job-embeddings/` - job embedding cache retrieval
   - Embedding-related parameters from ranking endpoints

   **KEEP (Enrichment endpoints):**
   - `GET /v1/llm/enhanced-artifacts/` - enriched evidence content (ft-005)
   - `POST /v1/artifacts/{id}/enrich/` - trigger enrichment

4. **Frontend:**
   - Embedding-related API client methods
   - Embedding-related TypeScript types

### What Will Be Added

1. **Backend:**
   - `POST /v1/artifacts/suggest-for-job/` endpoint (keyword-ranked suggestions)
   - Enhanced keyword ranking algorithm (fuzzy matching, recency weighting)
   - `artifact_ids` parameter to CV generation endpoint

2. **Frontend:**
   - `ArtifactSelector` component (multi-select with drag-to-reorder)
   - Artifact selection step in CV generation workflow
   - Relevance score badges (keyword match %)

### What Will Be Simplified

1. **ArtifactRankingService:**
   - Remove `strategy` parameter (always keyword)
   - Remove `job_embedding` parameter
   - Keep only `_rank_by_keyword_overlap()` and enhance it

2. **CVGenerationService:**
   - Accept optional `artifact_ids` parameter
   - Maintain backward compatibility (keyword ranking if no IDs)

### Job Description Processing Changes

**BEFORE (with embeddings):**
```
Job Description → OpenAI Embedding API ($0.0001/1K tokens)
                        ↓
        Store in JobDescriptionEmbedding table
                        ↓
        Cosine similarity vs artifact embeddings
                        ↓
                Semantic ranking
```

**AFTER (keyword-only):**
```
Job Description → Simple keyword extraction (free, <1ms)
                        ↓
        Match keywords vs artifact technologies
                        ↓
        Keyword overlap ranking (exact/partial/fuzzy)
```

**Key Changes:**
- NO embedding API calls for job descriptions
- NO JobDescriptionEmbedding cache table
- Simple text parsing for keyword extraction
- Instant ranking (<200ms for 100 artifacts)

---

## Decision Drivers

### Drivers FOR Removal

1. **Simplicity:** Reduce codebase by ~1500 lines, remove infrastructure dependency
2. **Cost:** Eliminate embedding API costs (~$0.01-0.05 per CV generation)
3. **User Control:** Users explicitly choose artifacts (transparency, trust)
4. **Maintenance:** Less complexity = fewer bugs, easier onboarding
5. **Low ROI:** Semantic search not actively used, chunk embeddings not created
6. **Developer Velocity:** Faster iteration without embedding pipeline concerns

### Drivers AGAINST Removal

1. **Feature Loss:** Semantic understanding of job-artifact match quality
2. **User Effort:** Users must manually select artifacts (extra step)
3. **Accuracy Risk:** Keyword matching may miss semantic relationships (e.g., "React" vs "Frontend Framework")
4. **Re-enablement Cost:** If needed later, requires re-implementation

---

## Considered Alternatives

### Alternative 1: Keep Embeddings, Add Manual Override

**Description:** Keep semantic search for automatic selection, but add UI for manual override.

**Pros:**
- Best of both worlds (automation + control)
- Semantic search as fallback for new users

**Cons:**
- Still maintains complexity and cost
- Dual paths increase testing surface
- Most users may never use automatic selection

**Decision:** ❌ **Rejected** - Doesn't address core complexity/cost issues

### Alternative 2: Replace pgvector with Simpler Vector DB (Redis, Faiss)

**Description:** Keep embeddings but use Redis Vector Search or Faiss instead of pgvector.

**Pros:**
- Simpler infrastructure (Redis may already be in stack)
- Potentially faster vector search

**Cons:**
- Still requires embedding API costs
- Still adds complexity (different infrastructure, same concept)
- Doesn't address "is semantic search needed?" question

**Decision:** ❌ **Rejected** - Addresses symptom (infrastructure), not root cause (unnecessary feature)

### Alternative 3: Keyword-Only Ranking (No Manual Selection)

**Description:** Remove embeddings but keep automatic selection using only keyword ranking.

**Pros:**
- Simple, fast, no API costs
- No extra user effort

**Cons:**
- Removes user control (same as current state)
- No transparency into why artifacts were selected

**Decision:** ❌ **Rejected** - Misses opportunity to empower users

### Alternative 4: Hybrid Manual + Smart Suggestions (CHOSEN)

**Description:** Remove embeddings, implement manual selection with keyword-based suggestions.

**Pros:**
- User control + helpful suggestions
- Simple keyword algorithm (fast, cost-free)
- Transparent relevance scores
- Progressive disclosure (show why artifact matches)

**Cons:**
- Extra user step (artifact selection)
- Keyword matching less sophisticated than semantic

**Decision:** ✅ **ACCEPTED**

---

## Consequences

### Positive Consequences

1. **Reduced Complexity:**
   - ~1500 lines of code removed
   - No pgvector extension to maintain
   - Simpler onboarding for new developers

2. **Cost Savings:**
   - $0 embedding API costs (was ~$0.01-0.05 per CV)
   - Reduced database storage (~1.5KB per artifact saved)

3. **Faster Performance:**
   - Keyword ranking: ~150ms (vs ~300ms for hybrid)
   - No vector distance calculations
   - Simpler SQL queries

4. **User Empowerment:**
   - Explicit artifact selection (user feels in control)
   - Transparent relevance scores
   - Ability to reorder artifacts by importance

5. **Better Architecture:**
   - Single responsibility (ArtifactRankingService → keyword only)
   - No embedding models (JobDescriptionEmbedding, ArtifactChunk)
   - Cleaner separation of concerns (enrichment vs ranking)

### Negative Consequences

1. **Feature Loss:**
   - No semantic understanding of job-artifact relationships
   - Cannot match "React" to "Frontend Framework" automatically
   - May miss nuanced skill equivalencies

2. **User Effort:**
   - Users must review and select artifacts manually
   - Extra step in CV generation workflow
   - Potential friction for users with many artifacts (50+)

3. **Re-enablement Cost:**
   - If semantic search needed later, requires:
     - Re-implementation of EmbeddingService
     - Re-installation of pgvector
     - Data migration (re-generate embeddings)
     - Estimated effort: 40-60 hours

4. **Data Loss:**
   - All existing job embeddings discarded
   - All artifact embeddings discarded
   - Cannot rollback migration (irreversible data loss)

### Neutral Consequences

1. **API Changes:**
   - Breaking: Embedding endpoints removed (low impact - admin only)
   - Additive: New suggest-for-job endpoint
   - Backward compatible: CV generation endpoint (artifact_ids optional)

2. **Migration Effort:**
   - Database migration: ~2-5 min downtime
   - Code changes: ~10-13 hours total
   - Testing: ~3-5 hours

---

## Risks and Mitigations

### Risk 1: Keyword Matching Insufficient

**Risk:** Users complain that keyword suggestions miss relevant artifacts.

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**
1. Enhance keyword algorithm with fuzzy matching (typos, abbreviations)
2. Add recency weighting (recent artifacts rank higher)
3. Add manual search/filter in ArtifactSelector component
4. Monitor user feedback for 30 days post-launch

**Escape Hatch:** If 25%+ users report poor suggestions, consider re-implementing semantic search

### Risk 2: User Friction from Manual Selection

**Risk:** Users abandon CV generation due to extra artifact selection step.

**Likelihood:** Low
**Impact:** High

**Mitigation:**
1. Provide "Use all suggested" quick action button
2. Save selection preferences per user (remember last selection)
3. Add "Skip selection, use top 5" option
4. Monitor drop-off rates at artifact selection step

**Escape Hatch:** If drop-off > 15%, make artifact selection optional (auto-select top 5 by default)

### Risk 3: Re-enablement Cost Higher Than Estimated

**Risk:** If semantic search needed later, cost to re-implement exceeds 60 hours.

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
1. Document embedding architecture in this ADR
2. Keep EmbeddingService code in git history (tagged)
3. Save migration rollback scripts (for reference)

---

## Implementation Plan

See **SPEC-artifact-selection v1.0.0** and **ft-007-manual-artifact-selection.md** for detailed implementation plan.

### Key Stages

1. **Stage B:** Codebase discovery ✅
2. **Stage C:** Technical specification ✅
3. **Stage D:** Architecture decision record ✅ (this document)
4. **Stage E:** Feature specification
5. **Stage F:** Write failing tests (TDD RED)
6. **Stage G:** Implement code (TDD GREEN)
7. **Stage H:** Refactor and polish

### Timeline

- **Implementation:** 10-13 hours
- **Testing:** 3-5 hours
- **Deployment:** 1 hour
- **Monitoring:** 30 days post-launch

---

## Monitoring and Evaluation

### Success Metrics (30-day evaluation)

| Metric | Target | Measured By |
|--------|--------|-------------|
| CV generation completion rate | ≥ 85% | Analytics (funnel) |
| Artifact selection drop-off rate | < 15% | Analytics (step navigation) |
| User-reported suggestion quality | ≥ 4.0/5.0 | User survey |
| Keyword ranking latency (p95) | < 200ms | Performance monitoring |
| Developer onboarding time | < 2 hours | Team feedback |

### Rollback Criteria

Rollback to previous version if ANY of the following occur within 30 days:

1. CV generation completion rate drops below 70%
2. User-reported suggestion quality < 3.0/5.0
3. Critical bugs in artifact selection (> 3 P0 issues)

---

## Related Documents

- **SPEC:** `docs/specs/spec-artifact-selection.md` (v1.0.0)
- **Feature:** `docs/features/ft-007-manual-artifact-selection.md`
- **Previous ADRs:**
  - ADR-20251001: Service Layer Extraction (ft-006)
  - SPEC-20250930: LLM Service Architecture Refactoring

---

## Decision Outcome

**Status:** ✅ **ACCEPTED**
**Date:** 2025-10-16
**Approvers:** User (product owner), Claude Code (implementer)

**Rationale:** The benefits of simplicity, cost reduction, and user control outweigh the loss of semantic understanding. Keyword-based suggestions with manual selection provide sufficient value while drastically reducing complexity. The decision is reversible (with effort) if proven insufficient.

**Next Steps:**
1. Create feature specification (ft-007)
2. Write failing tests (TDD approach)
3. Implement backend changes
4. Implement frontend changes
5. Deploy to staging
6. Monitor metrics for 30 days

---

## Notes

This ADR follows the decision-first docs workflow mandated by `rules/00-workflow.md`. Non-trivial architectural changes (removing infrastructure, changing contracts) require ADR documentation before implementation.

**Change Impact:**
- **Topology:** Removes pgvector extension (infrastructure change)
- **Contracts:** Removes embedding API endpoints, adds suggest-for-job endpoint
- **Framework Roles:** Simplifies service layer architecture

Therefore, this change triggers a SPEC version increment (artifact-selection v1.0.0) and requires ADR documentation (this document).
