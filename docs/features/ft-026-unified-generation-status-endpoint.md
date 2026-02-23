# Feature: Unified Generation Status Endpoint

**Feature ID:** ft-026
**Status:** Planning
**Priority:** High
**Size:** Medium
**Created:** 2025-10-31
**Related ADR:** ADR-040
**Related Specs:** spec-api.md v4.5.0, spec-cv-generation.md v2.2.0, spec-frontend.md v2.8.0

## Problem Statement

The artifact and generation apps have inconsistent status checking mechanisms, creating a broken frontend contract and poor user experience:

**Current State:**
- Artifact app provides `/artifacts/{id}/enrichment-status/` for polling
- Generation app returns `job_id` with comment "Client should poll job status endpoint"
- **BUT NO SUCH ENDPOINT EXISTS** - broken promise to frontend
- No way to track per-artifact bullet generation progress
- Frontend must poll full document endpoint (inefficient, no sub-job visibility)

**Impact:**
- Developers confused by inconsistent patterns
- Users see no progress during multi-artifact bullet generation
- Inefficient polling (transfers full CV content just for status checks)
- Debugging difficulty (no visibility into individual job failures)

## Goals

1. **Consistency:** Standardize status polling across all async operations
2. **UX:** Enable "X of Y artifacts processed" progress indicators
3. **Efficiency:** Reduce polling overhead (status-only vs. full document)
4. **Debugging:** Provide clear visibility into sub-job failures
5. **Maintainability:** Single pattern to learn and maintain

## Non-Goals

- Historical job queries (can only check current/latest state)
- Real-time WebSocket updates (HTTP polling sufficient)
- Breaking changes to existing endpoints

## Codebase Discovery Findings

### Existing Patterns

**1. Artifact Enrichment Status** (Reference Implementation)
- **File:** `backend/artifacts/views.py` (Lines 286-368)
- **Endpoint:** `GET /api/v1/artifacts/{artifact_id}/enrichment-status/`
- **Response:** Aggregates ArtifactProcessingJob + ExtractedContent
- **Frontend Hook:** `useEnrichmentStatus` with 10s auto-polling
- **Terminal States:** `completed`, `failed`

**2. Generation Status** (Current Implementation - Incomplete)
- **File:** `backend/generation/views.py` (Line 149)
- **Endpoint:** `GET /api/v1/generations/{generation_id}/status/`
- **Issues:**
  - Returns different response shapes based on status
  - No sub-job aggregation
  - No BulletGenerationJob visibility
- **Missing:** Dedicated status endpoint (only full document endpoint exists)

**3. Bullet Generation Service** (Service Layer - No Endpoint)
- **File:** `backend/generation/services/bullet_generation_service.py` (Lines 666-704)
- **Method:** `get_job_status(job_id)` returns detailed job status
- **Issue:** Service-level only, no REST endpoint exposed

### Job Types Requiring Status Tracking

| Job Type | Model | Status Field | Current Endpoint | Notes |
|----------|-------|--------------|------------------|-------|
| **GeneratedDocument** | `generation.GeneratedDocument` | 7 states | ❌ No dedicated status endpoint | Primary generation tracking |
| **BulletGenerationJob** | `generation.BulletGenerationJob` | 5 states | ❌ None | Per-artifact bullet generation |
| **BulletPoint** | `generation.BulletPoint` | Quality scores | ❌ None | Result model (not job tracker) |
| **ArtifactProcessingJob** | `artifacts.ArtifactProcessingJob` | 4 states | ✅ `/artifacts/{id}/enrichment-status/` | Reference pattern |
| **ExportJob** | `export.ExportJob` | 3 states | ✅ `/export/{id}/status/` | Document export |

### Key Insights from Discovery

1. **Broken Promise:** Backend returns `job_id` at generation/views.py:437-445 but no endpoint exists to poll it
2. **Pattern Exists:** Artifact enrichment-status provides perfect template to follow
3. **Service Ready:** BulletGenerationService already has aggregation logic (just needs endpoint)
4. **Frontend Ready:** useEnrichmentStatus hook can be adapted for generation
5. **Two-Phase Workflow:** GeneratedDocument tracks both bullet generation and assembly phases

## Proposed Solution

### Backend Architecture

**New Endpoint:**
```
GET /api/v1/generations/{generation_id}/generation-status/
```

**Implementation Layers:**

1. **Service Layer:** `GenerationStatusService` (new)
   - Aggregates GeneratedDocument + BulletGenerationJob statuses
   - Calculates phase-level progress
   - Computes processing and quality metrics

2. **View Layer:** `generation_status` (new view in `generation/views.py`)
   - Permission: `IsAuthenticated` + owner check
   - Calls `GenerationStatusService.get_generation_status()`
   - Returns serialized response

3. **Serializer:** `GenerationStatusSerializer` (new)
   - Core status fields (status, progress, error_message)
   - Phase details (bullet_generation, assembly)
   - Sub-job summaries (per-artifact jobs)
   - Aggregated metrics (processing, quality)

**URL Route:**
```python
# backend/generation/urls.py
path('<uuid:generation_id>/generation-status/', views.generation_status, name='generation_status'),
```

### Response Contract

```json
{
  "generation_id": "uuid",
  "status": "processing",
  "progress_percentage": 60,
  "error_message": null,
  "created_at": "2025-10-31T10:00:00Z",
  "completed_at": null,

  "current_phase": "bullet_generation",
  "phase_details": {
    "bullet_generation": {
      "status": "in_progress",
      "artifacts_total": 5,
      "artifacts_processed": 3,
      "bullets_generated": 9,
      "started_at": "2025-10-31T10:00:10Z",
      "completed_at": null
    },
    "assembly": {
      "status": "not_started",
      "started_at": null,
      "completed_at": null
    }
  },

  "bullet_generation_jobs": [
    {
      "job_id": "uuid-1",
      "artifact_id": 42,
      "artifact_title": "E-commerce Platform",
      "status": "completed",
      "bullets_generated": 3,
      "processing_duration_ms": 1500,
      "error_message": null
    },
    {
      "job_id": "uuid-2",
      "artifact_id": 43,
      "artifact_title": "Analytics Dashboard",
      "status": "processing",
      "bullets_generated": 0,
      "processing_duration_ms": null,
      "error_message": null
    }
  ],

  "processing_metrics": {
    "total_duration_ms": 4500,
    "total_cost_usd": 0.05,
    "total_tokens_used": 2500,
    "model_version": "gpt-4o-2024-05-13"
  },

  "quality_metrics": {
    "average_bullet_quality": 0.87,
    "average_keyword_relevance": 0.92,
    "bullets_approved": 9,
    "bullets_rejected": 0,
    "bullets_edited": 2
  }
}
```

### Frontend Architecture

**New Hook:** `useGenerationStatus`

**Location:** `frontend/src/hooks/useGenerationStatus.ts`

**Features:**
- Auto-polling with configurable interval (default 10s)
- React ignore flag pattern (prevents race conditions)
- Terminal state detection (`completed`, `failed`)
- Callbacks: `onComplete`, `onError`
- Manual refetch capability

**New API Method:** `apiClient.getGenerationStatus(generationId)`

**Location:** `frontend/src/services/apiClient.ts`

**Migration Strategy:**
- Existing `useGeneration` hook unchanged (non-breaking)
- New `useGenerationStatus` recommended for future use
- CVGenerationFlow can migrate incrementally

## Implementation Plan

### Phase 1: Backend Foundation (Stage F-G)

**Files to Create:**
- `backend/generation/services/generation_status_service.py` - Service layer
- `backend/generation/serializers.py:GenerationStatusSerializer` - Response serializer

**Files to Modify:**
- `backend/generation/views.py` - Add `generation_status` view
- `backend/generation/urls.py` - Add status route

**Files to Update/Delete:**
- `backend/generation/views.py:437-445` - Remove broken `job_id` return pattern
- `backend/generation/tests/*.py` - Update tests to remove `job_id` assertions

**Tests to Write (TDD - Write First):**
```python
# backend/generation/tests/test_generation_status.py
- test_generation_status_endpoint_returns_comprehensive_response()
- test_generation_status_aggregates_bullet_jobs()
- test_generation_status_calculates_phase_details()
- test_generation_status_handles_missing_generation()
- test_generation_status_requires_authentication()
- test_generation_status_enforces_ownership()
- test_generation_status_terminal_states()
```

### Phase 2: Frontend Integration (Stage F-G)

**Files to Create:**
- `frontend/src/hooks/useGenerationStatus.ts` - Polling hook
- `frontend/src/types/generation.ts` - Type definitions

**Files to Modify:**
- `frontend/src/services/apiClient.ts` - Add `getGenerationStatus()` method

**Tests to Write (TDD - Write First):**
```typescript
// frontend/src/hooks/__tests__/useGenerationStatus.test.ts
- test_hook_fetches_status_on_mount
- test_hook_polls_every_interval
- test_hook_stops_polling_on_completed
- test_hook_stops_polling_on_failed
- test_hook_calls_onComplete_callback
- test_hook_calls_onError_callback
- test_hook_prevents_race_conditions_with_ignore_flag
```

### Phase 3: Migration and Cleanup (Optional)

**Optional Frontend Changes:**
- Migrate CVGenerationFlow to use new hook
- Add per-artifact progress indicators
- Update CVDetailPage to show sub-job statuses

## Success Criteria

**Functional:**
1. ✅ Endpoint returns comprehensive status for all generation operations
2. ✅ Frontend can display "X of Y artifacts processed"
3. ✅ Response structure matches artifact enrichment-status pattern
4. ✅ No breaking changes to existing functionality
5. ✅ All tests pass (unit + integration)

**Performance:**
- Reduced polling data transfer by >90% (status-only vs. full document)
- Status endpoint responds in <200ms (P95)

**UX:**
- Users see per-artifact progress during bullet generation
- Clear error messaging when individual jobs fail

**Code Quality:**
- Test coverage >90% for new code
- Follows llm_services architectural patterns
- Documented in all three specs (API, Generation, Frontend)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance degradation from aggregation queries | Low | Medium | Use `select_related()` and `prefetch_related()` for efficient queries |
| Frontend race conditions during polling | Medium | High | Use React ignore flag pattern (proven in useEnrichmentStatus) |
| Breaking existing frontend code | Low | High | Additive changes only, existing endpoints unchanged |
| Test coverage gaps | Medium | Medium | TDD workflow (write tests first) |

## Dependencies

**Blockers:**
- None (all required models and services exist)

**Related Work:**
- ADR-040: Decision documentation (completed)
- spec-api.md v4.5.0: API contract (completed)
- spec-cv-generation.md v2.2.0: Service interface (completed)
- spec-frontend.md v2.8.0: Hook specification (completed)

## Rollout Plan

**Stage 1: Backend Implementation**
1. Write failing tests for generation-status endpoint
2. Implement GenerationStatusService
3. Implement generation_status view
4. Add URL route
5. Run tests (should pass now)

**Stage 2: Frontend Implementation**
6. Write failing tests for useGenerationStatus hook
7. Implement getGenerationStatus API method
8. Implement useGenerationStatus hook
9. Run tests (should pass now)

**Stage 3: Cleanup**
10. Remove broken `job_id` pattern from bullet endpoint responses
11. Update/delete old tests expecting `job_id`
12. Run full test suite to verify no regressions

**Stage 4: Documentation**
13. Update API documentation with examples
14. Add usage examples to README
15. Document migration path for existing code

## Testing Strategy

**Backend Tests:**
- Unit tests for GenerationStatusService (aggregation logic)
- Integration tests for generation_status view (full request/response)
- Permission tests (authentication, ownership)
- Edge case tests (no jobs, failed jobs, partial completion)

**Frontend Tests:**
- Unit tests for useGenerationStatus hook (polling logic)
- Integration tests for apiClient.getGenerationStatus()
- Race condition tests (multiple concurrent polls)
- Callback tests (onComplete, onError)

**Manual Testing:**
- Create generation with multiple artifacts
- Watch status poll during processing
- Verify per-artifact progress updates
- Test terminal states (completed, failed)
- Verify polling stops at terminal states

## Alternative Solutions Considered

**Alternative 1: Job-Scoped Endpoint**
- `GET /api/v1/generations/bullet-jobs/{job_id}/status/`
- **Rejected:** Inconsistent with generation-scoped pattern (ADR-038)

**Alternative 2: WebSocket Real-Time Updates**
- **Rejected:** Over-engineering for current scale, adds complexity

**Alternative 3: Continue Without Status Endpoint**
- **Rejected:** Violates user expectations, poor UX

## References

- **Codebase Discovery:** Comprehensive analysis of existing status patterns
- **Artifact Reference:** `backend/artifacts/views.py:artifact_enrichment_status`
- **Frontend Reference:** `frontend/src/hooks/useEnrichmentStatus.ts`
- **ADR-040:** Decision rationale for chosen approach
- **spec-api.md v4.5.0:** Complete API contract
- **spec-cv-generation.md v2.2.0:** Service layer interface
- **spec-frontend.md v2.8.0:** Frontend hook and API client

## Acceptance Tests

```python
# Scenario 1: Poll generation status during bullet generation
GIVEN a generation with 5 artifacts
WHEN bullet generation is in progress (3 of 5 completed)
THEN status endpoint returns:
  - status: "processing"
  - current_phase: "bullet_generation"
  - phase_details.bullet_generation.artifacts_processed: 3
  - phase_details.bullet_generation.artifacts_total: 5
  - bullet_generation_jobs: array with 5 items
  - 3 jobs with status "completed"
  - 2 jobs with status "pending" or "processing"

# Scenario 2: Poll generation status during assembly
GIVEN a generation with bullets approved
WHEN CV assembly is in progress
THEN status endpoint returns:
  - status: "assembling"
  - current_phase: "assembly"
  - phase_details.assembly.status: "in_progress"
  - quality_metrics with approved/rejected/edited counts

# Scenario 3: Terminal state (completed)
GIVEN a completed generation
WHEN status endpoint is polled
THEN status endpoint returns:
  - status: "completed"
  - current_phase: "completed"
  - processing_metrics.total_cost_usd: <actual cost>
  - quality_metrics: <final scores>

# Scenario 4: Terminal state (failed)
GIVEN a failed generation
WHEN status endpoint is polled
THEN status endpoint returns:
  - status: "failed"
  - error_message: <failure reason>
  - bullet_generation_jobs: array showing which jobs failed

# Scenario 5: Frontend polling behavior
GIVEN a React component using useGenerationStatus
WHEN generation is in progress
THEN:
  - Hook polls every 10 seconds
  - status state updates on each poll
  - isPolling returns true
WHEN generation completes
THEN:
  - Hook stops polling
  - onComplete callback fires
  - isPolling returns false
```

## Appendix: Discovery Data

**Total Job Types Found:** 5 (GeneratedDocument, BulletGenerationJob, ArtifactProcessingJob, ExportJob, BulletPoint)

**Active Async Jobs:** 3 (GeneratedDocument, BulletGenerationJob, ArtifactProcessingJob)

**Existing Status Endpoints:** 2 (artifact enrichment, export status)

**Key Gaps:**
1. No bullet generation job status endpoint
2. No unified status response across job types
3. Frontend polling inefficiencies (full document vs status-only)
4. Missing sub-job aggregation in generation status

**Best Reference Implementation:** `artifact_enrichment_status` endpoint + `useEnrichmentStatus` hook
