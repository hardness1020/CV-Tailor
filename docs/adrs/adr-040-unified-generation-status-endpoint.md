# ADR-040: Unified Generation Status Endpoint Pattern

**Status:** Accepted
**Date:** 2025-10-31
**Decision Makers:** Backend Team, Frontend Team
**Related:** ADR-038 (Generation-Scoped Endpoints), ft-030 (Generation Status Standardization)

## Context and Problem Statement

The artifact and generation apps have inconsistent approaches to status checking for async operations:

**Artifact App** provides a dedicated enrichment-status endpoint:
```
GET /api/v1/artifacts/{artifact_id}/enrichment-status/
```

**Generation App** returns `job_id` in bullet generation responses but has **NO corresponding status endpoint** to poll that job:
```python
# backend/generation/views.py (Lines 437-445)
return Response({
    'job_id': str(job.id) if job else None,  # ← Job ID returned
    'status': 'processing',  # ← Comment says "Client should poll job status endpoint"
    # BUT NO SUCH ENDPOINT EXISTS!
    ...
}, status=status.HTTP_202_ACCEPTED)
```

This creates several problems:

1. **Broken Contract:** Backend promises polling capability but provides no endpoint
2. **Inconsistent Patterns:** Different status checking approaches confuse developers
3. **No Sub-Job Visibility:** Frontend cannot track per-artifact bullet generation progress
4. **Inefficient Polling:** Existing polling fetches full CV document instead of lightweight status
5. **Poor UX:** No "X of Y artifacts processed" indicators during generation

## Decision Drivers

* **Consistency:** Follow established artifact enrichment-status pattern
* **UX Requirements:** Enable per-artifact progress indicators
* **Efficiency:** Reduce polling data transfer (status-only vs. full document)
* **Debugging:** Provide visibility into individual job failures
* **Maintainability:** Single standardized pattern for all async operations

## Considered Options

### Option A: Resource-Scoped Status (CHOSEN)

**Endpoint:**
```
GET /api/v1/generations/{generation_id}/generation-status/
```

**Response Structure:**
```json
{
  "generation_id": "uuid",
  "status": "processing",
  "progress_percentage": 60,
  "current_phase": "bullet_generation",
  "phase_details": {
    "bullet_generation": {
      "status": "in_progress",
      "artifacts_total": 5,
      "artifacts_processed": 3,
      "bullets_generated": 9
    }
  },
  "bullet_generation_jobs": [
    {
      "job_id": "uuid",
      "artifact_id": 42,
      "artifact_title": "E-commerce Platform",
      "status": "completed",
      "bullets_generated": 3
    }
  ],
  "processing_metrics": { "total_cost_usd": 0.05 },
  "quality_metrics": { "average_bullet_quality": 0.87 }
}
```

**Pros:**
- ✅ Consistent with artifact enrichment-status pattern
- ✅ No need to track individual `job_id` on frontend
- ✅ Simpler client implementation (one endpoint, one ID)
- ✅ Matches ADR-038 generation-scoped philosophy
- ✅ Aggregates all related job statuses in one response
- ✅ Lightweight (status-only, not full CV content)

**Cons:**
- ⚠️ Can only check latest state (no historical job queries)
- ⚠️ Cannot check status of specific old jobs

### Option B: Job-Scoped Status (Rejected)

**Endpoint:**
```
GET /api/v1/generations/bullet-jobs/{job_id}/status/
```

**Pros:**
- Can check any specific job's status
- Better for debugging historical jobs
- Matches the `job_id` return pattern

**Cons:**
- ❌ Introduces new top-level resource namespace
- ❌ Less consistent with generation-scoped pattern
- ❌ More complex frontend state management
- ❌ Requires tracking multiple `job_id` values
- ❌ No aggregated view of all jobs

### Option C: Hybrid Approach (Rejected - Over-Engineering)

Both endpoints:
```
GET /api/v1/generations/{generation_id}/generation-status/  (convenience)
GET /api/v1/generations/bullet-jobs/{job_id}/status/       (granular)
```

**Pros:**
- Maximum flexibility

**Cons:**
- ❌ Duplicate logic and maintenance burden
- ❌ Risk of inconsistencies between endpoints
- ❌ Violates YAGNI principle
- ❌ No clear use case for job-level endpoint

## Decision Outcome

**Chosen option: Option A (Resource-Scoped Status)**

Implement unified generation status endpoint at `/api/v1/generations/{generation_id}/generation-status/` that:

1. Aggregates GeneratedDocument status + all related BulletGenerationJob statuses
2. Provides phase-level tracking (bullet generation, bullet review, assembly)
3. Returns comprehensive metrics (processing cost, quality scores)
4. Matches artifact enrichment-status pattern for consistency
5. Enables "X of Y artifacts processed" progress indicators

## Consequences

### Positive

* **Consistency:** All async operations follow same status polling pattern
* **Better UX:** Per-artifact progress visibility during generation
* **Efficiency:** Reduced polling overhead (status-only vs. full document)
* **Debugging:** Clear visibility into which artifacts/jobs succeeded/failed
* **Maintainability:** Single pattern to learn and maintain

### Negative

* **No Historical Queries:** Cannot check status of old jobs (acceptable tradeoff)
* **Minor Implementation Effort:** Need to aggregate data from multiple models

### Neutral

* **Frontend Changes:** New `useGenerationStatus` hook (non-breaking, additive)
* **Backend Changes:** New view and serializer (non-breaking, additive)

## Implementation Details

### Backend Changes

**New Files:**
- `backend/generation/views.py:generation_status` - Status aggregation view
- `backend/generation/serializers.py:GenerationStatusSerializer` - Response serializer
- `backend/generation/services/generation_status_service.py` - Business logic

**Modified Files:**
- `backend/generation/urls.py` - Add generation-status route
- `backend/generation/views.py` - Remove broken `job_id` return pattern

### Frontend Changes

**New Files:**
- `frontend/src/hooks/useGenerationStatus.ts` - Auto-polling hook
- `frontend/src/types/generation.ts` - GenerationStatus type definitions

**Modified Files:**
- `frontend/src/services/apiClient.ts` - Add `getGenerationStatus()` method
- `frontend/src/components/CVGenerationFlow.tsx` - Migrate to new polling pattern (optional)

### URL Routing

```python
# backend/generation/urls.py
urlpatterns = [
    # ...existing routes...
    path('<uuid:generation_id>/generation-status/', views.generation_status, name='generation_status'),
]
```

### Response Contract

**Status Field Mapping:**
- `status`: Overall GeneratedDocument status
- `current_phase`: Derived from status (bullet_generation | bullet_review | assembly | completed)
- `phase_details.bullet_generation.status`: Aggregated from BulletGenerationJob statuses
- `phase_details.assembly.status`: Derived from GeneratedDocument status

**Terminal States:**
- `completed`: All operations finished successfully
- `failed`: At least one critical failure occurred

**Polling Behavior:**
- Frontend polls every 10 seconds (configurable)
- Stops polling when status reaches `completed` or `failed`
- Uses React ignore flag pattern to prevent race conditions

## Alternatives Considered and Rejected

### Alternative 1: Continue Without Status Endpoint

**Rejected Reason:** Violates user expectations (backend promises polling but provides no endpoint)

### Alternative 2: Poll Full Document Endpoint

**Current Behavior:** Some code polls `GET /generations/{id}/` for status

**Rejected Reason:**
- Inefficient (transfers full CV content just for status check)
- No sub-job visibility
- Poor UX (no per-artifact progress)

### Alternative 3: WebSocket Real-Time Updates

**Rejected Reason:**
- Over-engineering for current scale
- HTTP polling sufficient for 10s update interval
- Adds infrastructure complexity (WebSocket server)

## Related Decisions

- **ADR-038:** Generation-Scoped Bullet Endpoints - Establishes generation-scoped pattern
- **ADR-039:** URL Parameter Standardization - Ensures consistent parameter naming
- **ADR-037:** CV → Generation Terminology - Standardizes naming conventions

## References

- **Codebase Discovery:** Research on existing status patterns across apps
- **Artifact Pattern:** `backend/artifacts/views.py:artifact_enrichment_status` (Lines 286-368)
- **Frontend Hook:** `frontend/src/hooks/useEnrichmentStatus.ts` (Reference implementation)
- **spec-api.md v4.5.0:** API contract for new endpoint
- **spec-cv-generation.md v2.2.0:** Backend service interface
- **spec-frontend.md v2.8.0:** Frontend hook and API client

## Validation

**Acceptance Criteria:**
1. ✅ Endpoint returns comprehensive status for all generation operations
2. ✅ Frontend can display "X of Y artifacts processed"
3. ✅ Response matches artifact enrichment-status structure
4. ✅ No breaking changes to existing functionality
5. ✅ Tests cover all status combinations and edge cases

**Success Metrics:**
- Reduced polling data transfer by >90% (status-only vs. full document)
- Frontend can render per-artifact progress indicators
- Consistent pattern across all async operations
- Zero regressions in existing generation flows
