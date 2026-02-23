# ADR-038: Generation-Scoped Bullet Endpoints

**Status:** Accepted
**Date:** 2025-10-30
**Deciders:** Development Team
**Tags:** #api-design #rest #domain-model #breaking-change

## Context

The codebase currently has **two conflicting sets of bullet point endpoints** that violate REST principles and create confusion:

### 1. Generation-Scoped Bullets (CORRECT)
```
GET    /api/v1/generations/{generation_id}/bullets/
PATCH  /api/v1/generations/{generation_id}/bullets/{bullet_id}/
POST   /api/v1/generations/{generation_id}/bullets/approve/
POST   /api/v1/generations/{generation_id}/bullets/regenerate/
```

### 2. Artifact-Scoped Bullets (INCORRECT)
```
POST   /api/v1/generations/artifacts/{artifact_id}/generate-bullets/
GET    /api/v1/generations/artifacts/{artifact_id}/bullets/preview/
POST   /api/v1/generations/artifacts/{artifact_id}/bullets/approve/
```

### Problem Analysis

**Domain Model Truth** (from `generation/models.py:180-207`):
```python
class BulletPoint(models.Model):
    artifact = models.ForeignKey('artifacts.Artifact', ...)
    cv_generation = models.ForeignKey(                    # ← Bullets belong to GENERATION!
        'GeneratedDocument',
        related_name='bullet_points',
        help_text='CV generation this bullet belongs to'
    )
```

**Bullets belong to a GENERATION, not to an artifact!**

### Issues with Current Structure

1. **Violates Domain Model:**
   - URLs suggest bullets belong to artifacts: `/artifacts/{id}/generate-bullets/`
   - Database shows bullets belong to generations: `BulletPoint.cv_generation`
   - Creates semantic mismatch between API and domain model

2. **Confusing Namespace:**
   - `/api/v1/generations/artifacts/...` suggests artifacts nested under generations
   - Reality: Artifacts and generations are independent resources
   - Violates REST principle: resources should reflect domain relationships

3. **Duplicated Endpoints:**
   - Two sets of bullet endpoints doing similar things
   - `preview_artifact_bullets()` vs `get_generation_bullets()` - both fetch bullets
   - `approve_artifact_bullets()` vs `approve_generation_bullets()` - both approve bullets
   - Creates confusion about which endpoint to use

4. **Parameter Inconsistency:**
   - Artifact endpoints require `cv_generation_id` in request body
   - This proves bullets are scoped to generation, not artifact!
   - URL structure contradicts request payload structure

5. **Poor Code Organization:**
   - Artifact bullet endpoints defined in `generation/urls.py` (line 23-25)
   - Artifact bullet views implemented in `generation/views.py` (line 715-914)
   - Should be in artifacts app OR clearly generation-scoped

### Workflow Reality

The actual bullet generation workflow:
1. User creates **Generation** (GeneratedDocument UUID: `550e8400...`)
2. Generation uses **multiple artifacts** (e.g., artifacts #1, #5, #12)
3. For **each artifact** in **this generation**, generate 3 bullets
4. User reviews **all bullets for this generation** together
5. Assemble CV using **approved bullets from this generation**

→ Bullets are scoped to generation, filtered by artifact!

## Decision

**Consolidate all bullet operations under generation scope**, with artifact_id as a filter/parameter.

### New Unified Structure

```
GET    /api/v1/generations/{generation_id}/bullets/
       Query: ?artifact_id=42 (optional filter)
       → Get all bullets for generation (or filter by artifact)

POST   /api/v1/generations/{generation_id}/bullets/
       Body: { "artifact_id": 42, "job_context": {...} }
       → Generate bullets for an artifact in this generation

PATCH  /api/v1/generations/{generation_id}/bullets/{bullet_id}/
       Body: { "text": "..." }
       → Edit specific bullet (ALREADY EXISTS ✅)

POST   /api/v1/generations/{generation_id}/bullets/approve/
       Body: { "bullet_ids": [1,2,3], "action": "approve" }
       → Approve/reject/edit bullets (ALREADY EXISTS ✅)

POST   /api/v1/generations/{generation_id}/bullets/regenerate/
       Body: { "artifact_id": 42, "refinement_prompt": "..." }
       → Regenerate bullets (ALREADY EXISTS ✅)
```

### Rationale

1. **Matches Domain Model:**
   - URLs reflect database relationships: bullets belong to generations
   - Artifact is a filter/parameter, not the primary resource
   - Semantic consistency between API and domain model

2. **RESTful Design:**
   - Resources properly nested: `/generations/{id}/bullets/`
   - Sub-resources under correct parent resource
   - No confusing cross-resource namespaces

3. **Reduces Duplication:**
   - Single set of bullet endpoints (not two)
   - Clear ownership: all bullet operations under generation scope
   - Easier to maintain and extend

4. **Clearer API:**
   - Intuitive structure: "Get bullets for this generation"
   - Optional filtering: "...filtered by this artifact"
   - Consistent with other generation sub-resources

5. **Parameter Consistency:**
   - Primary identifier in URL path: `generation_id`
   - Filters/specifiers in query or body: `artifact_id`
   - No more contradictory parameter locations

### Breaking Changes Accepted

- **Removed endpoints:**
  - `POST /api/v1/generations/artifacts/{artifact_id}/generate-bullets/`
  - `GET /api/v1/generations/artifacts/{artifact_id}/bullets/preview/`
  - `POST /api/v1/generations/artifacts/{artifact_id}/bullets/approve/`

- **New/Modified endpoints:**
  - `POST /api/v1/generations/{generation_id}/bullets/` (new: generate bullets)
  - `GET /api/v1/generations/{generation_id}/bullets/` (modified: add artifact filter)

- **Parameter changes:**
  - `artifact_id` moved from URL path to request body/query params
  - `cv_generation_id` removed from body (now in URL path)

## Consequences

### Positive

1. **Semantic Accuracy:**
   - API structure matches domain model
   - Clear ownership: bullets belong to generations
   - Easier to understand for new developers

2. **REST Compliance:**
   - Resources properly nested
   - No confusing cross-resource namespaces
   - Follows standard REST conventions

3. **Reduced Code Duplication:**
   - Single set of bullet endpoints
   - Removed redundant `preview_artifact_bullets()`
   - Removed redundant `approve_artifact_bullets()`

4. **Clearer API Surface:**
   - One way to do each operation
   - Intuitive resource hierarchy
   - Consistent with other generation endpoints

5. **Easier Maintenance:**
   - Clear code ownership (all in generation app)
   - Single source of truth for bullet operations
   - Easier to extend with new features

### Negative

1. **Breaking Changes:**
   - Frontend must update 3 API client methods
   - Backend tests require updates (11 test cases)
   - Requires coordinated deployment

2. **Migration Effort:**
   - Backend: URL patterns, view functions, serializers
   - Frontend: API client, components
   - Testing: Update and verify all tests

3. **Parameter Location Changes:**
   - Developers must update `artifact_id` from URL to body/query
   - Potential for runtime errors if not updated correctly

### Migration Strategy

**Pre-Production Breaking Change Deployment:**

1. **Backend Changes:**
   - Update URL patterns in `generation/urls.py`
   - Consolidate view functions
   - Update serializers for new parameter locations
   - Update all tests

2. **Frontend Changes:**
   - Update API client methods
   - Update components calling old methods
   - Verify TypeScript compilation

3. **Coordinated Deployment:**
   - Deploy backend and frontend together
   - No backward compatibility needed (pre-production)
   - Single atomic release

4. **Testing:**
   - Run full backend test suite
   - Run frontend TypeScript checks
   - Manual testing of bullet generation workflow
   - E2E testing of complete CV generation

## Implementation Details

### Backend Changes

**File: `backend/generation/urls.py`**
```python
# REMOVE (3 endpoints):
path('artifacts/<int:artifact_id>/generate-bullets/', ...),
path('artifacts/<int:artifact_id>/bullets/preview/', ...),
path('artifacts/<int:artifact_id>/bullets/approve/', ...),

# MODIFY (support GET + POST):
path('<uuid:generation_id>/bullets/', views.generation_bullets, name='generation_bullets'),
```

**File: `backend/generation/views.py`**
```python
# Consolidate into single view:
@api_view(['GET', 'POST'])
def generation_bullets(request, generation_id):
    if request.method == 'GET':
        # Get bullets for generation
        # Support ?artifact_id filter
    elif request.method == 'POST':
        # Generate bullets for artifact in generation
        # artifact_id from request body

# REMOVE:
# - generate_bullets_for_artifact()
# - preview_artifact_bullets()
# - approve_artifact_bullets() (already handled by approve_generation_bullets)
```

**File: `backend/generation/serializers.py`**
```python
class BulletGenerationRequestSerializer(serializers.Serializer):
    artifact_id = serializers.IntegerField()  # NEW: From body
    job_context = JobContextSerializer()
    regenerate = serializers.BooleanField(default=False)
    # REMOVED: cv_generation_id (now in URL)
```

### Frontend Changes

**File: `frontend/src/services/apiClient.ts`**
```typescript
// BEFORE:
async generateBulletsForArtifact(artifactId: number, request: {...}): Promise<...> {
  return this.client.post(`/v1/generations/artifacts/${artifactId}/generate-bullets/`, request)
}

// AFTER:
async generateGenerationBullets(generationId: string, artifactId: number, request: {...}): Promise<...> {
  return this.client.post(`/v1/generations/${generationId}/bullets/`, {
    artifact_id: artifactId,
    ...request
  })
}

// BEFORE:
async previewArtifactBullets(artifactId: number, params?: {...}): Promise<...> {
  return this.client.get(`/v1/generations/artifacts/${artifactId}/bullets/preview/?...`)
}

// AFTER:
async getGenerationBullets(generationId: string, artifactId?: number): Promise<...> {
  const url = `/v1/generations/${generationId}/bullets/`
  const params = artifactId ? `?artifact_id=${artifactId}` : ''
  return this.client.get(url + params)
}

// REMOVE:
// - approveArtifactBullets() (use approveGenerationBullets instead)
```

### Testing Updates

**File: `backend/generation/tests/test_api.py`**

11 test cases require URL updates:
```python
# BEFORE:
url = f'/api/v1/generations/artifacts/{artifact_id}/generate-bullets/'

# AFTER:
url = f'/api/v1/generations/{generation_id}/bullets/'
data = {'artifact_id': artifact_id, ...}
```

## Compliance

- **Workflow:** Docs-first (ADR created before implementation)
- **Change-Control:** Breaking API contract changes documented
- **TDD:** Tests updated to reflect new endpoints
- **Pattern:** Follows REST resource nesting principles

## References

- **Related:** ADR-037 (Standardize Generation Terminology)
- **Domain Model:** `backend/generation/models.py:180-207` (BulletPoint model)
- **Current Implementation:** `backend/generation/urls.py:23-25` (artifact-scoped endpoints)
- **REST Standards:** https://restfulapi.net/resource-naming/

## Metadata

- **ID:** ADR-038
- **Created:** 2025-10-30
- **Updated:** 2025-10-30
- **Version:** 1.0.0
