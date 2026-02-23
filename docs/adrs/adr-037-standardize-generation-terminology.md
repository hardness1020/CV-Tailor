# ADR-037: Standardize Generation Terminology

**Status:** Accepted
**Date:** 2025-10-30
**Deciders:** Development Team
**Tags:** #refactoring #naming #consistency #breaking-change

## Context

The codebase exhibits significant naming inconsistencies for CV-related functionality:

1. **Three competing terminology patterns:**
   - "CV" prefix: `generate_cv()`, `CVGenerationService`, `CVGenerationRequestSerializer`
   - "Generation" prefix: `GenerationDetailView`, `generation_status()`, model relations
   - "GeneratedDocument": Model name, some serializers

2. **URL confusion:**
   - Backend: `/v1/generate/` AND `/v1/cv/` (duplicate patterns)
   - Frontend: `/cvs` (different from both backend patterns)

3. **Inconsistency with artifacts pattern:**
   - Artifacts app demonstrates excellent consistency: `Artifact` model, `/v1/artifacts/` URLs, `artifact_*` function prefix
   - Generation app has no consistent pattern

4. **Semantic mismatch:**
   - The "CVs page" actually displays **job applications** containing multiple generated documents (CV, cover letter)
   - "CV" terminology is too narrow (excludes cover letters)

### Analysis Findings

**Artifacts Pattern (Reference Standard - CONSISTENT):**
- Model: `Artifact` (singular)
- URLs: `/v1/artifacts/` (plural)
- Functions: `artifact_*` prefix (100% consistent)
- Frontend: `/artifacts`
- Related names: `related_name='artifacts'`

**Generation Pattern (INCONSISTENT):**
- Model: `GeneratedDocument`
- URLs: `/v1/generate/` OR `/v1/cv/` (two patterns)
- Functions: `cv_*` OR `generation_*` OR `generate_*` (three patterns)
- Frontend: `/cvs`
- Serializers: `CV*` OR `GeneratedDocument*` (two patterns)

## Decision

**Standardize on "Generation" terminology** across the full stack, following the artifacts naming pattern.

### Rationale for "Generation" over alternatives:

1. **"Generation" (SELECTED):**
   - ✅ Covers both CVs and cover letters (semantic accuracy)
   - ✅ Matches current model naming pattern (`GeneratedDocument`)
   - ✅ Used in some existing code (`generation_status`, `GenerationDetailView`)
   - ✅ Domain-neutral (can extend to other document types)

2. **"JobApplication" (REJECTED):**
   - ❌ More verbose
   - ❌ Requires renaming everything (higher migration cost)
   - ❌ Less aligned with current code

3. **"CV" (REJECTED):**
   - ❌ Excludes cover letters (semantic mismatch)
   - ❌ Too specific (limits future document types)

### Breaking Changes Accepted

- **API Endpoints:** `/v1/cv/*` and `/v1/generate/*` removed, replaced with `/v1/generations/*`
- **Frontend URLs:** `/cvs` removed, replaced with `/generations`
- **Impact:** All API consumers must update (development environment only, no production users yet)

### Model Name Decision

**Keep `GeneratedDocument` model name** (no database migration):
- ✅ Avoids complex database migration
- ✅ Still semantically accurate
- ✅ Lower risk of breaking relationships
- ⚠️ Minor inconsistency with "Generation" terminology acceptable

## Consequences

### Positive

1. **Consistency with artifacts pattern:**
   - Single terminology throughout codebase
   - Easier onboarding for new developers
   - Reduced cognitive load when navigating code

2. **Semantic accuracy:**
   - "Generation" correctly describes both CVs and cover letters
   - Extensible to future document types

3. **Cleaner API:**
   - Single URL pattern: `/v1/generations/*`
   - Predictable naming conventions

4. **Maintainability:**
   - Easier to search/replace code
   - Reduced naming confusion in reviews

### Negative

1. **Breaking changes:**
   - All API endpoints changed
   - Frontend URLs changed
   - Requires updating all consumers

2. **Migration effort:**
   - ~17 todos across backend and frontend
   - All tests must be updated
   - Documentation must be updated

3. **Minor model name inconsistency:**
   - Model is `GeneratedDocument` but everything else uses "Generation"
   - Acceptable trade-off to avoid database migration

### Migration Strategy

1. **No backward compatibility:**
   - Clean break (user preference: "Breaking changes OK")
   - No API versioning or aliases
   - All changes in single deployment

2. **Full-stack refactoring:**
   - Backend: URLs, views, serializers, services, tests
   - Frontend: Routes, pages, components, API client, types, tests

3. **Testing:**
   - Update all existing tests
   - Run full test suite before deployment
   - Manual smoke testing after deployment

## Compliance

- **Workflow:** Docs-first (ADR created before implementation)
- **Change-Control:** Breaking API contract changes documented
- **TDD:** Tests will be updated before code changes (tests fail → implementation → tests pass)

## References

- Analysis document: Plan mode research (2025-10-30)
- Related: Artifacts app naming pattern (reference standard)
- Pattern: `docs/architecture/patterns.md` (service layer architecture)

## Metadata

- **ID:** ADR-037
- **Created:** 2025-10-30
- **Updated:** 2025-10-30
- **Version:** 1.0.0
