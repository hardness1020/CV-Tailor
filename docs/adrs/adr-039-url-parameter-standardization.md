# ADR-039: URL Parameter Standardization

**Status:** Accepted
**Date:** 2025-10-30
**Deciders:** Development Team
**Tags:** #api-design #rest #consistency #conventions

## Context

The API had several URL inconsistencies that violated REST principles and created confusion for frontend developers:

### 1. Inconsistent Parameter Naming

**Before:**
```python
# Artifact endpoints - mixed naming
path('<int:pk>/', views.ArtifactDetailView.as_view())           # Uses 'pk'
path('<int:artifact_id>/upload/', views.upload_artifact_files)  # Uses 'artifact_id'

# Export endpoints - mixed naming
path('<uuid:pk>/detail/', views.ExportJobDetailView.as_view())  # Uses 'pk'
path('<uuid:export_id>/status/', views.export_status)           # Uses 'export_id'

# Generation endpoints - consistent
path('<uuid:generation_id>/', views.GenerationDetailView.as_view())  # Uses 'generation_id'
```

**Issues:**
- `pk` is Django internal naming, not semantic
- Inconsistent naming makes API harder to learn
- No clear pattern to predict parameter names

### 2. Non-RESTful Suffixes

**Before:**
```python
# Export detail endpoint with /detail/ suffix
path('<uuid:pk>/detail/', views.ExportJobDetailView.as_view())

# Other detail endpoints WITHOUT suffix (inconsistent)
path('<int:pk>/', views.ArtifactDetailView.as_view())
path('<uuid:generation_id>/', views.GenerationDetailView.as_view())
```

**Issues:**
- `/detail/` suffix is redundant (detail is implied by GET on resource URL)
- Inconsistent with other detail endpoints
- Not RESTful (resource URLs should be clean: `/exports/{id}/`)

### 3. Missing Trailing Slashes

**Before (frontend API client):**
```typescript
// Missing trailing slashes caused 301 redirects → 404s
async getExportStatus(exportId: string) {
  return await this.client.get(`/v1/export/${exportId}/status`)  // ❌ Missing slash
}

async downloadExport(exportId: string) {
  return await this.client.get(`/v1/export/${exportId}/download`)  // ❌ Missing slash
}
```

**Issues:**
- Django's `APPEND_SLASH=True` causes 301 redirects
- POST requests fail on redirect (lose request body)
- Inconsistent with other endpoints that have trailing slashes

### 4. Implicit View Configuration

**Before:**
```python
class ArtifactDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    # ❌ No explicit lookup configuration
    # Django defaults: lookup_field='pk', lookup_url_kwarg='pk'
```

**Issues:**
- URL parameter name must match default `lookup_url_kwarg='pk'`
- Cannot use semantic names like `artifact_id` without explicit configuration
- Implicit behavior is harder to understand

## Decision

We standardize all API URLs to follow these conventions:

### 1. Semantic Parameter Naming Convention

**Use resource-specific parameter names, not generic `pk`:**

```python
# Artifact endpoints
path('<int:artifact_id>/', views.ArtifactDetailView.as_view())
path('<int:artifact_id>/upload/', views.upload_artifact_files)

# Generation endpoints
path('<uuid:generation_id>/', views.GenerationDetailView.as_view())
path('<uuid:generation_id>/bullets/', views.generation_bullets)

# Export endpoints
path('<uuid:export_id>/', views.ExportJobDetailView.as_view())
path('<uuid:export_id>/status/', views.export_status)
```

**Naming Pattern:** `<type>_id` where `type` is the singular resource name

### 2. Remove Non-RESTful Suffixes

**Use clean resource URLs:**

```python
# ✅ CORRECT: Clean resource URL
path('<uuid:export_id>/', views.ExportJobDetailView.as_view())

# ❌ WRONG: Redundant /detail/ suffix
path('<uuid:export_id>/detail/', views.ExportJobDetailView.as_view())
```

**Rationale:**
- RESTful URLs: `GET /resource/{id}/` retrieves detail by convention
- Suffixes like `/detail/` are redundant
- Keeps URLs clean and predictable

### 3. Always Use Trailing Slashes

**All API endpoints must end with trailing slash:**

```typescript
// ✅ CORRECT
async getExportStatus(exportId: string) {
  return await this.client.get(`/v1/export/${exportId}/status/`)  // Trailing slash
}

// ❌ WRONG
async getExportStatus(exportId: string) {
  return await this.client.get(`/v1/export/${exportId}/status`)   // No trailing slash
}
```

**Rationale:**
- Django's `APPEND_SLASH=True` is standard configuration
- Missing slash causes 301 redirect
- POST requests lose body on redirect
- Consistent trailing slashes avoid redirects entirely

### 4. Explicit View Lookup Configuration

**Always specify `lookup_field` and `lookup_url_kwarg` explicitly:**

```python
class ArtifactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific artifact."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'              # Model field to lookup by
    lookup_url_kwarg = 'artifact_id' # URL parameter name (ADR-039)

    def get_queryset(self):
        return Artifact.objects.filter(user=self.request.user)
```

**Rationale:**
- Makes URL-to-field mapping explicit and visible
- Allows semantic URL parameter names
- Easier to understand and maintain
- Self-documenting code

## Consequences

### ✅ Positive

1. **Consistent API Design:**
   - Predictable URL patterns across all resources
   - Easy to learn and remember
   - Follows REST conventions

2. **Self-Documenting URLs:**
   - `artifact_id` clearly indicates an artifact identifier
   - No need to guess parameter names
   - IDE autocomplete shows semantic names

3. **No Redirect Issues:**
   - Trailing slashes prevent 301 redirects
   - POST requests work reliably
   - Better performance (no extra HTTP round-trip)

4. **Explicit Configuration:**
   - View classes self-document their URL mapping
   - Easier to understand code flow
   - Reduces implicit Django magic

### ⚠️ Breaking Changes

**Backend URLs Changed:**

```python
# Before → After
path('<int:pk>/', ...)           → path('<int:artifact_id>/', ...)
path('<uuid:pk>/detail/', ...)   → path('<uuid:export_id>/', ...)
```

**Frontend URLs Changed:**

```typescript
// Before → After
`/v1/export/${id}/status`        → `/v1/export/${id}/status/`
`/v1/export/${id}/download`      → `/v1/export/${id}/download/`
`/v1/generations/${id}/detail/`  → `/v1/generations/${id}/`
```

**Migration Strategy:**

1. ✅ **Tests Updated:** All URL reverse() calls use new parameter names
2. ✅ **Frontend Updated:** API client methods use new URLs with trailing slashes
3. ✅ **Views Configured:** All detail views have explicit lookup configuration
4. ⚠️ **Coordinated Deployment:** Backend and frontend must be deployed together

### 📋 Checklist for New Endpoints

When creating new API endpoints, ensure:

- [ ] URL parameters use semantic names (`<type>_id>`, not `<pk>`)
- [ ] No redundant suffixes (no `/detail/`, `/info/`, etc.)
- [ ] All URLs end with trailing slash
- [ ] Detail views have explicit `lookup_field` and `lookup_url_kwarg`
- [ ] Frontend API client includes trailing slashes
- [ ] Tests use `reverse()` with correct parameter names

## References

- **Related ADRs:**
  - [ADR-038: Generation-Scoped Bullet Endpoints](./adr-038-generation-scoped-bullet-endpoints.md) - Resource scoping decisions

- **Django Documentation:**
  - [URL Dispatcher](https://docs.djangoproject.com/en/4.2/topics/http/urls/)
  - [Generic Views](https://docs.djangoproject.com/en/4.2/ref/class-based-views/generic-display/)
  - [APPEND_SLASH Setting](https://docs.djangoproject.com/en/4.2/ref/settings/#append-slash)

- **REST API Best Practices:**
  - [RESTful API Design](https://restfulapi.net/resource-naming/)
  - Semantic URLs over generic identifiers
  - Clean resource URLs without redundant suffixes

## Implementation

**Files Modified:**

**Backend:**
- `backend/artifacts/urls.py` - Changed `<int:pk>` to `<int:artifact_id>`
- `backend/artifacts/views.py` - Added explicit lookup configuration to ArtifactDetailView
- `backend/artifacts/tests/test_api.py` - Updated URL reverse kwargs (3 occurrences)
- `backend/artifacts/tests/test_editing.py` - Updated URL reverse kwargs (4 occurrences)
- `backend/export/urls.py` - Changed `<uuid:pk>/detail/` to `<uuid:export_id>/`
- `backend/export/views.py` - Added explicit lookup configuration to ExportJobDetailView

**Frontend:**
- `frontend/src/services/apiClient.ts` - Added trailing slashes to export status/download URLs
- `frontend/src/services/apiClient.ts` - Removed `/detail/` from generation delete URL

**Test Coverage:**
- ✅ Artifact endpoint tests updated and passing
- ✅ TypeScript compilation passes with no errors
- ⏳ Backend test suite pending (next step)

**Deployment Notes:**
- Backend and frontend changes are coordinated
- Breaking changes require simultaneous deployment
- URL changes are backward-incompatible (old URLs will 404)
