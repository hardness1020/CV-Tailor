# ft-007 Stage G Implementation Progress

**Date**: 2025-10-17
**Status**: In Progress (Stage G - TDD GREEN phase)
**Target**: Implement code to make all 57 failing tests pass

## Completed ✅

### Backend Services

**1. ArtifactRankingService** (`backend/llm_services/services/core/artifact_ranking_service.py`)
- ✅ Removed all semantic similarity methods (_rank_by_semantic_similarity, find_similar_artifacts, _get_chunk_based_similarity, _calculate_cosine_similarity, _similarity_search_sync, _combine_rankings)
- ✅ Removed EmbeddingService dependency
- ✅ Enhanced _rank_by_keyword_overlap with:
  - matched_keywords list (returns list of matched job keywords)
  - fuzzy_matches count (partial substring matching)
  - recency weighting (_calculate_recency_boost method with 0.0-0.1 boost for artifacts within 1 year)
  - Case-insensitive matching (already existed)
- ✅ Simplified to 193 lines (down from 378 lines)

**2. Suggest-for-Job Endpoint** (`backend/artifacts/views.py`)
- ✅ Created suggest_artifacts_for_job view function (lines 563-653)
- ✅ Accepts job_description (required, min 10 chars) and limit (optional, 1-50, default 10)
- ✅ Extracts keywords from job description (simple word splitting)
- ✅ Calls ArtifactRankingService with keyword strategy
- ✅ Returns ranked artifacts with total_artifacts and returned_count
- ✅ Includes authentication and user isolation
- ✅ Added URL routing: `path('suggest-for-job/', views.suggest_artifacts_for_job, name='artifact-suggest-for-job')`

**3. CVGenerationRequestSerializer** (`backend/generation/serializers.py`)
- ✅ Added artifact_ids field (optional, list of integers, max 50, no duplicates)
- ✅ Added validation method (validate_artifact_ids) for empty list, max count, and duplicates

**4. CVGenerationService** (`backend/generation/services/cv_generation_service.py`)
- ✅ Added artifact_ids parameter to generate_cv_for_job() method
- ✅ Added artifact_ids parameter to prepare_bullets() method
- ✅ Created _fetch_selected_artifacts() method with:
  - Ownership validation (ensures all artifacts belong to user)
  - Order preservation (returns artifacts in specified order)
  - Comprehensive error handling (ValueError for missing/unauthorized artifacts)
- ✅ Modified workflow to use manual selection when artifact_ids provided:
  - Skips automatic ranking when artifact_ids present
  - Uses keyword-only ranking for automatic selection (backward compatible)
  - Preserves artifact order in final document
- ✅ Updated both generate_cv_for_job() and prepare_bullets() methods

**5. Generate CV View & Tasks** (`backend/generation/views.py` & `backend/generation/tasks.py`)
- ✅ Modified generate_cv() view to extract artifact_ids from request.data
- ✅ Stored artifact_ids in generation.generation_preferences for task retrieval
- ✅ Updated prepare_cv_bullets_task() to extract and pass artifact_ids
- ✅ Updated generate_cv_task() (deprecated) for backward compatibility
- ✅ Full view → task → service pipeline complete

### Tests Created (Stage F)

**Backend Tests**: 46 tests created
- 6 tests in test_artifact_ranking_service.py (keyword ranking enhancements)
- 8 tests in test_api.py (suggest-for-job endpoint)
- 11 tests in test_cv_generation_with_artifacts.py (CV generation with artifact_ids)
- 9 tests in test_remove_embedding_migration.py (migration safety)

**Frontend Tests**: 23 tests created
- 14 tests in ArtifactSelector.test.tsx
- 9 tests in CVGenerationWorkflow.test.tsx

**Deprecated Tests Removed**: 5 tests
- test_calculate_cosine_similarity()
- test_combine_rankings()
- test_service_initialization()
- test_cosine_similarity_edge_cases()
- TestArtifactRankingIntegration class (entire class)

## Remaining Work ❌

### Backend Implementation

**6. Database Migration** (New file: `backend/generation/migrations/XXXX_remove_embedding_infrastructure.py`)
- ❌ DROP TABLE llm_services_enhancedevidence CASCADE
- ❌ DROP TABLE llm_services_artifactchunk CASCADE
- ❌ DROP TABLE llm_services_jobdescriptionembedding CASCADE
- ❌ DROP COLUMN artifacts_artifact.unified_embedding
- ❌ DROP EXTENSION vector (pgvector)
- ❌ Use RunSQL.noop for reverse_sql (non-reversible migration)
- ❌ Test migration with test_remove_embedding_migration.py

**7. Delete EmbeddingService**
- ❌ Delete file: `backend/llm_services/services/core/embedding_service.py` (394 lines)
- ❌ Remove imports from __init__.py and other files that reference EmbeddingService
- ❌ Update llm_services/services/__init__.py to remove EmbeddingService export

### Frontend Implementation

**8. ArtifactSelector Component** (New file: `frontend/src/components/ArtifactSelector.tsx`)
- ❌ Fetch suggestions from suggest-for-job endpoint on mount
- ❌ Display artifacts in list/grid view with:
  - Artifact title, description, technologies
  - Relevance score badge (e.g., "85% match")
  - Matched keywords chips (highlighted)
  - Checkbox for selection
- ❌ Auto-select top 5 artifacts on load
- ❌ Support manual selection/deselection
- ❌ Show selection count (e.g., "5 artifacts selected")
- ❌ Implement search/filter functionality (title, technologies)
- ❌ Implement sorting (relevance, date, title)
- ❌ Implement drag-to-reorder (@dnd-kit/core)
- ❌ Handle loading state (LoadingOverlay)
- ❌ Handle error state (error message + retry)
- ❌ Handle empty state (no artifacts found)
- ❌ Call onSelectionChange(artifactIds) when selection changes

**9. CVGenerationWorkflow Component** (Modify: `frontend/src/pages/CVGenerationWorkflow.tsx`)
- ❌ Add new Step 2: Artifact Selection (between job description and review)
- ❌ Integrate ArtifactSelector component
- ❌ Update step indicator to show 3 steps: "Job Description → Artifacts → Review"
- ❌ Persist artifact selection when navigating back/forward
- ❌ Add "Use Top 5" button to skip manual selection (calls generateCV with undefined artifact_ids)
- ❌ Validate at least 1 artifact selected before proceeding
- ❌ Pass selected artifact_ids to generateCV() call
- ❌ Update multi-step state management

**10. API Client** (Modify: `frontend/src/services/apiClient.ts`)
- ❌ Add suggestArtifactsForJob(jobDescription, limit?) method
- ❌ Modify generateCV(jobDescription, artifactIds?) to accept optional artifact_ids parameter
- ❌ Add TypeScript types:
  ```typescript
  interface ArtifactSuggestion {
    id: number;
    title: string;
    description: string;
    technologies: string[];
    enriched_technologies: string[];
    relevance_score: number;
    exact_matches: number;
    partial_matches: number;
    fuzzy_matches: number;
    matched_keywords: string[];
    start_date: string;
    end_date: string;
    artifact_type: string;
  }

  interface SuggestArtifactsResponse {
    artifacts: ArtifactSuggestion[];
    total_artifacts: number;
    returned_count: number;
  }
  ```

## Test Execution Plan

### Phase 1: Backend Tests (Run after backend implementation)
```bash
# Test artifact ranking service
docker-compose exec backend uv run python manage.py test llm_services.tests.unit.services.core.test_artifact_ranking_service --keepdb

# Test suggest-for-job endpoint
docker-compose exec backend uv run python manage.py test artifacts.tests.test_api.ArtifactSuggestForJobAPITests --keepdb

# Test CV generation with artifacts
docker-compose exec backend uv run python manage.py test generation.tests.test_cv_generation_with_artifacts --keepdb

# Test migration
docker-compose exec backend uv run python manage.py test generation.tests.test_remove_embedding_migration --keepdb
```

### Phase 2: Frontend Tests (Run after frontend implementation)
```bash
# Test ArtifactSelector component
docker-compose exec frontend npm test -- ArtifactSelector.test.tsx

# Test CVGenerationWorkflow component
docker-compose exec frontend npm test -- CVGenerationWorkflow.test.tsx
```

## Implementation Priority

**Critical Path (Minimum Viable)**:
1. CVGenerationService modifications (artifact_ids support)
2. Generate CV view modifications (pass artifact_ids)
3. Frontend API client updates
4. ArtifactSelector component (basic version)
5. CVGenerationWorkflow integration

**Post-MVP Enhancements**:
6. Database migration (can run later, doesn't block feature)
7. Delete EmbeddingService (cleanup, doesn't block feature)
8. Advanced UI features (drag-to-reorder, advanced filtering)

## Notes

- **Backward Compatibility**: artifact_ids is optional. If not provided, use automatic keyword ranking (existing behavior).
- **Ownership Validation**: Critical security requirement - must validate all artifact_ids belong to request.user.
- **Order Preservation**: When artifact_ids provided, preserve the order specified by user (don't re-sort).
- **Migration Safety**: Migration is non-reversible due to data loss. Document this clearly.
- **Keyword Extraction**: Current implementation uses simple word splitting. Can be improved with NLP in Stage H.

## Stage H Preview (Refactor & Polish)

After all tests pass in Stage G, Stage H will focus on:
- Remove dead code and unused imports
- Improve keyword extraction algorithm (use spaCy or similar)
- UI/UX polish (loading states, tooltips, error handling, animations)
- Performance optimization (debounce search, virtualize long lists)
- Documentation updates (API docs, component docs)
- Run full test suite and verify coverage ≥ 89%
