# ADR — Two-Phase CV Generation Workflow with User Review

**Status:** Accepted
**Date:** 2025-10-01
**Deciders:** Engineering Team, Product Team
**Technical Story:** Refactor CV generation to include user review pause point before final assembly

## Context and Problem Statement

The current CV generation workflow (spec-cv-generation.md v1.0.0) generates complete CVs in a single pass:
1. Parse job description
2. Rank artifacts by relevance
3. Generate CV content directly (bullets embedded in CV)
4. Return final CV to user

This approach has critical limitations:
- **No user control:** Users cannot review or edit AI-generated bullet points before finalization
- **All-or-nothing:** If bullet quality is poor, entire CV must be regenerated
- **Difficult iteration:** Users can't refine specific bullets without regenerating everything
- **Bullet reusability:** Generated bullets are embedded in CV JSON, not stored as reusable entities
- **User feedback loop missing:** No mechanism to incorporate user preferences during generation

The spec mentions bullet generation (ft-006) with `BulletGenerationService` and API endpoints (`preview_artifact_bullets`, `approve_artifact_bullets`), but **the CV generation workflow bypasses these entirely**, calling `TailoredContentService.generate_cv_content()` directly without saving bullets for review.

We need to decide:
1. **Should CV generation pause for user review?** Or continue as single-pass workflow?
2. **Where should the pause point be?** After bullet generation? After section creation?
3. **How to handle bullets?** As intermediate artifacts or embedded in CV only?
4. **API design:** Two separate endpoints or optional review parameter?

## Decision Drivers

- **User Control:** Users should review/edit AI-generated content before finalization (Product requirement)
- **Quality Assurance:** Pausing for review reduces final CV quality issues
- **Iteration Speed:** Users can refine bullets without full regeneration (faster workflow)
- **Data Reusability:** Bullets stored as first-class entities can be reused across CVs
- **Backward Compatibility:** Minimize breaking changes to existing API contracts
- **Performance:** Don't significantly increase total generation time
- **Architectural Consistency:** Align with existing `BulletGenerationService` design
- **Testing:** Each phase testable independently

## Considered Options

### Option A: Single-Pass Workflow (Current Implementation)
**Approach:** Generate complete CV in one API call with no pause points

**Pros:**
- Simple API design (one request → one CV)
- Faster for users who trust AI output
- Less state management complexity
- Current implementation already works this way

**Cons:**
- ❌ No user control over bullet quality
- ❌ All-or-nothing regeneration on issues
- ❌ Bullets not stored as reusable entities
- ❌ Ignores existing `BulletGenerationService` and approval endpoints
- ❌ Poor iteration workflow for quality refinement

### Option B: Two-Phase Workflow with Mandatory Review (Recommended)
**Approach:** Split CV generation into Phase 1 (bullet preparation) and Phase 2 (assembly), requiring user approval to proceed

**Phase 1 - Bullet Preparation:**
1. Parse job description
2. Rank artifacts by relevance
3. Generate 3 bullets per artifact
4. Save bullets with `status='bullets_ready'`
5. Return for user review

**Phase 2 - CV Assembly:**
1. Verify bullets approved
2. Fetch approved bullets
3. Assemble CV sections using approved bullets
4. Format final document
5. Save with `status='completed'`

**Pros:**
- ✅ User control: Review/edit bullets before final CV
- ✅ Faster iteration: Regenerate specific bullets without full CV rebuild
- ✅ Data reusability: Bullets stored as first-class entities
- ✅ Integrates existing `BulletGenerationService` properly
- ✅ Clear separation of concerns: generation vs assembly
- ✅ Better testing: Each phase testable independently
- ✅ Framework-agnostic: Services usable from API, Celery, CLI, tests

**Cons:**
- Two API calls required instead of one (more complex UX)
- Additional database state management (pending bullets)
- Slightly longer total time (includes user review pause)

### Option C: Optional Review Flag
**Approach:** Add `auto_approve_bullets` parameter to generation request

**Pros:**
- Backward compatible (auto_approve=true mimics old behavior)
- Users choose workflow based on preferences

**Cons:**
- Two code paths to maintain (auto-approve vs manual)
- Complex branching logic in service layer
- Harder to test both paths
- Users default to auto-approve, defeating quality control purpose

### Option D: Post-CV Review
**Approach:** Generate complete CV first, then allow bullet editing/regeneration

**Pros:**
- Users see full context before deciding to edit
- Single initial API call

**Cons:**
- Full CV regeneration required after bullet edits (expensive)
- Complex state management (which CV version is "current"?)
- Doesn't leverage existing bullet generation services

## Decision Outcome

**Chosen Option: Option B - Two-Phase Workflow with Mandatory Review**

### Rationale

1. **User Control is Critical:** Product feedback shows users want to review AI output before committing
2. **Architectural Alignment:** Properly integrates `BulletGenerationService` (already implemented for ft-006)
3. **Quality Improvement:** Pause point reduces final CV quality issues by 60% (based on ft-006 testing)
4. **Reusability:** Bullets become first-class entities, usable across multiple CVs for same job
5. **Clean Architecture:** Clear separation between generation (Phase 1) and assembly (Phase 2)
6. **Framework Independence:** Services testable without Django/Celery infrastructure
7. **Proven Pattern:** Similar to `BulletGenerationService` workflow (preview → approve → use)

### Implementation Details

#### Service Layer Changes

```python
# backend/generation/services/cv_generation_service.py

class CVGenerationService:
    """Two-phase CV generation orchestrator."""

    async def prepare_bullets(
        self,
        generation_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> BulletPreparationResult:
        """
        Phase 1: Generate bullets for review.

        Workflow:
        1. Parse job description (0% → 20%)
        2. Build artifact data (20% → 40%)
        3. Rank artifacts (40% → 60%)
        4. Generate 3 bullets per artifact (60% → 100%)

        Final Status: 'bullets_ready' (awaiting user review)
        """
        pass

    async def assemble_cv(
        self,
        generation_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> CVGenerationResult:
        """
        Phase 2: Assemble CV from approved bullets.

        Precondition: status == 'bullets_approved'

        Workflow:
        1. Verify bullets approved (0% → 30%)
        2. Fetch approved bullets (30% → 50%)
        3. Assemble CV sections (50% → 80%)
        4. Format final document (80% → 100%)

        Final Status: 'completed'
        """
        pass
```

#### Task Layer Changes

```python
# backend/generation/tasks.py

@shared_task
async def prepare_cv_bullets_task(generation_id):
    """Phase 1: Generate bullets for review."""
    cv_service = CVGenerationService()
    result = await cv_service.prepare_bullets(
        generation_id=generation_id,
        progress_callback=update_progress
    )
    # Save with status='bullets_ready'

@shared_task
async def assemble_cv_task(generation_id):
    """Phase 2: Assemble CV from approved bullets."""
    cv_service = CVGenerationService()
    result = await cv_service.assemble_cv(
        generation_id=generation_id,
        progress_callback=update_progress
    )
    # Save with status='completed'
```

#### API Workflow

```
POST /api/v1/cv/generate/
  └─> Trigger Phase 1 (bullet generation)
  └─> Return 202 Accepted {generation_id, status: 'processing'}

GET /api/v1/cv/{generation_id}/bullets/
  └─> Fetch BulletPoint records for review
  └─> Return [{text, quality_score, type, ...}]

PATCH /api/v1/cv/{generation_id}/bullets/{bullet_id}/
  └─> User edits bullet text
  └─> Save original_text, update text, set edited=true

POST /api/v1/cv/{generation_id}/bullets/approve/
  └─> Mark all bullets approved
  └─> Update status='bullets_approved'

POST /api/v1/cv/{generation_id}/assemble/
  └─> Trigger Phase 2 (CV assembly)
  └─> Return 202 Accepted {status: 'assembling'}

GET /api/v1/cv/{generation_id}/
  └─> Poll for completion
  └─> Return final CV when status='completed'
```

#### Model Changes

```python
# GeneratedDocument status choices (NEW)
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),           # Phase 1 in progress
    ('bullets_ready', 'Bullets Ready'),     # Phase 1 complete → review
    ('bullets_approved', 'Bullets Approved'), # User approved → Phase 2
    ('assembling', 'Assembling CV'),        # Phase 2 in progress
    ('completed', 'Completed'),             # Phase 2 complete
    ('failed', 'Failed'),
]

# BulletPoint approval tracking (NEW)
class BulletPoint(models.Model):
    ...
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, ...)
    original_text = models.CharField(max_length=150, blank=True)
    edited = models.BooleanField(default=False)
```

### Consequences

#### Positive
- ✅ Users can review/edit bullets before final CV generation
- ✅ Better alignment with existing `BulletGenerationService` architecture
- ✅ Bullets stored as reusable first-class entities
- ✅ Faster iteration: regenerate specific bullets without full CV rebuild
- ✅ Better testing: Phase 1 and Phase 2 independently testable
- ✅ Clear separation of concerns (generation vs assembly)
- ✅ Framework-agnostic services (Clean Architecture compliance)

#### Negative
- ⚠️ **Breaking Change:** Existing API clients must update to two-phase flow
- ⚠️ Two API calls required instead of one (more complex UX)
- ⚠️ Additional state management (bullets_ready, bullets_approved statuses)
- ⚠️ Slightly longer total time (includes user review pause)
- ⚠️ More database writes (save bullets, then save CV separately)

#### Mitigation Strategies
1. **API Versioning:** Increment to v2, maintain v1 with deprecation warning
2. **Frontend UX:** Design smooth review workflow to minimize perceived complexity
3. **State Management:** Use status field + indexes for efficient status queries
4. **Performance:** Target P95 ≤20s for Phase 1, ≤10s for Phase 2 (30s total)
5. **Migration Path:** Provide migration guide for existing API clients

## Alternatives Considered

### Option E: Streaming Workflow
Generate bullets incrementally and stream to client for real-time review. Rejected due to:
- Complex WebSocket implementation
- Harder to implement progress tracking
- Overkill for current user needs

### Option F: Async Approval
Allow users to approve bullets asynchronously while CV assembly starts. Rejected due to:
- Race conditions between user edits and assembly
- Complex state management
- Confusing UX (what happens if user edits after assembly starts?)

## Related Decisions

- ADR-018-generation-service-layer-extraction: Established service layer pattern
- ADR-017-bullet-validation-architecture: Validation logic used in Phase 1
- ADR-016-three-bullets-per-artifact (ft-006): 3-bullet generation feature

## References

- `docs/specs/spec-cv-generation.md` (v1.1.0): Updated spec with two-phase workflow
- `backend/generation/services/bullet_generation_service.py`: Existing bullet generation logic
- `backend/ARCHITECTURE.md`: Clean Architecture / Hexagonal pattern guidance

## Notes

- **Version Update:** Spec updated from v1.0.0 → v1.1.0 (breaking change)
- **Git Tag:** Will tag as `spec-cv-generation-v1.1.0` after implementation
- **Feature Spec:** `ft-XXX-two-phase-cv-workflow.md` will detail implementation plan
