# Feature — 009 two-phase-cv-workflow

**File:** docs/features/ft-009-two-phase-cv-workflow.md
**Owner:** Backend Team, Frontend Team
**TECH-SPECs:** `spec-cv-generation.md` (v1.1.0)
**Related ADRs:** [ADR-019-two-phase-cv-generation-workflow](../adrs/adr-019-two-phase-cv-generation-workflow.md)
**PRD Reference:** `prd.md` Section 2.2 (CV Generation with User Control)

## Existing Implementation Analysis

**Current Workflow (v1.0.0):**
```
POST /api/v1/cv/generate/
  → generate_cv_task()
    → CVGenerationService.generate_cv_for_job()
      → TailoredContentService.generate_cv_content()  # Direct LLM call
  → Returns complete CV (status='completed')
```

**Problem:** Users cannot review/edit AI-generated bullets before final CV assembly.

**Files to Modify:**
- `backend/generation/services/cv_generation_service.py` (293 lines) - **PRIMARY CHANGES**
- `backend/generation/tasks.py` (266 lines) - Split tasks
- `backend/generation/views.py` (674 lines) - Add endpoints
- `backend/generation/models.py` (586 lines) - Add fields
- `backend/generation/serializers.py` (493 lines) - New serializers
- `backend/generation/urls.py` - New routes

**Reusable Components:**
- ✅ `generation/services/bullet_generation_service.py` (612 lines) - **CENTRAL TO PHASE 1**
  - `generate_bullets()` - Already generates exactly 3 bullets per artifact
  - `regenerate_bullet()` - Single bullet refinement
  - Auto-retry on validation failure (up to 3 attempts)
- ✅ `generation/services/bullet_validation_service.py` (644 lines)
  - Multi-criteria quality validation
  - Semantic similarity detection
  - ATS keyword relevance scoring
- ✅ `llm_services/services/core/tailored_content_service.py`
  - `assemble_final_document()` - **WILL USE IN PHASE 2**
  - Already exists, just needs bullet input instead of generating bullets
- ✅ `llm_services/services/core/artifact_ranking_service.py`
  - `rank_artifacts_by_relevance()` - Semantic similarity search
  - Already used in current cv_generation_service.py (line 190)

**Patterns to Follow:**
- **Service Layer Pattern:** Framework-agnostic services (ADR-018-generation-service-layer-extraction)
- **Progress Callback:** Used in CVGenerationService.generate_cv_for_job() (lines 83-87, 125-126)
- **Async Task Delegation:** tasks.py delegates to services (lines 25-100)
- **Clean Architecture:** App layer (generation/services) → Infrastructure layer (llm_services)

**Code Already Implemented:**
- ✅ BulletPoint model (models.py:166-250) - Has most fields, missing approval tracking
- ✅ BulletGenerationJob model (models.py:252-300) - Job tracking exists
- ✅ BulletGenerationService - Complete orchestration logic
- ✅ BulletValidationService - Multi-criteria validation
- ✅ 4 bullet API endpoints (views.py:291-613):
  - `generate_bullets_for_artifact()` (line 291)
  - `preview_artifact_bullets()` (line 373)
  - `approve_artifact_bullets()` (line 437)
  - `validate_bullets()` (line 613)

**Gaps (What Needs to Be Built):**
1. **GeneratedDocument** missing status values:
   - Need: 'pending', 'bullets_ready', 'bullets_approved', 'assembling'
   - Current: Only 'processing', 'completed', 'failed' (models.py:51-55)
2. **BulletPoint** missing approval tracking:
   - Need: approved_at, approved_by, original_text, edited
   - Current: Has structure/quality fields but no approval tracking (models.py:166-250)
3. **CVGenerationService** single-pass design:
   - Need: Split generate_cv_for_job() → prepare_bullets() + assemble_cv()
   - Current: Single method that generates complete CV (cv_generation_service.py:83-249)
4. **Tasks** single task:
   - Need: prepare_cv_bullets_task() + assemble_cv_task()
   - Current: Single generate_cv_task() (tasks.py:25-100)
5. **API Endpoints** missing:
   - Need: GET /cv/{id}/bullets/, POST /cv/{id}/bullets/approve/, POST /cv/{id}/assemble/
   - Current: Only POST /cv/generate/ and GET /cv/{id}/ (views.py)

**Dependencies:**
- `generation.services.BulletGenerationService` - **WILL CALL IN PHASE 1**
- `generation.services.BulletValidationService` - Used by BulletGenerationService
- `llm_services.services.core.TailoredContentService` - For Phase 2 assembly
- `llm_services.services.core.ArtifactRankingService` - For artifact selection
- `generation.models.GeneratedDocument` - **WILL EXTEND**
- `generation.models.BulletPoint` - **WILL EXTEND**

## Architecture Conformance

**Layer Assignment:**
- **Service Layer:** `generation/services/cv_generation_service.py`
  - `prepare_bullets()` - Phase 1 orchestration
  - `assemble_cv()` - Phase 2 orchestration
- **Task Layer:** `generation/tasks.py`
  - `prepare_cv_bullets_task()` - Worker for Phase 1
  - `assemble_cv_task()` - Worker for Phase 2
- **API Layer:** `generation/views.py`
  - `generate_cv()` - Trigger Phase 1 (update existing)
  - `get_generation_bullets()` - List bullets for review (new)
  - `approve_generation_bullets()` - Approve all bullets (new)
  - `update_bullet()` - Edit single bullet (new)
  - `assemble_cv_from_bullets()` - Trigger Phase 2 (new)
- **Data Layer:** `generation/models.py`
  - GeneratedDocument - Add status values and metadata fields
  - BulletPoint - Add approval tracking fields

**Pattern Compliance:**
- ✅ Framework-agnostic services (testable without Django/Celery)
- ✅ Progress callback pattern for async job tracking
- ✅ Clean separation: worker concerns (tasks.py) vs business logic (services/)
- ✅ Dependency direction: app layer (generation) → infrastructure (llm_services)
- ✅ Circuit breaker pattern for LLM calls (via BulletGenerationService)
- ✅ Retry logic with exponential backoff (via task_executor)

**Test Coverage:**
- Current: 89.6% in generation/ app (95/106 tests passing)
- Target: Maintain ≥85% coverage after changes
- New tests needed:
  - Unit tests for prepare_bullets() and assemble_cv()
  - Integration tests for two-phase workflow
  - API endpoint tests for new routes
  - Migration tests for model changes

## Acceptance Criteria

### Phase 1 - Bullet Preparation
- [ ] POST /api/v1/cv/generate/ triggers bullet generation (not full CV)
- [ ] Generation creates GeneratedDocument with status='processing'
- [ ] Service calls BulletGenerationService for each ranked artifact
- [ ] BulletPoint records saved with approved_at=null
- [ ] Final status='bullets_ready' when all bullets generated
- [ ] Progress callback updates: 0% → 20% → 40% → 60% → 100%
- [ ] P95 latency ≤ 20 seconds for 6-8 artifacts

### Phase 2 - User Review
- [ ] GET /api/v1/cv/{id}/bullets/ returns all bullet points
- [ ] PATCH /api/v1/cv/{id}/bullets/{bullet_id}/ allows editing bullet text
- [ ] Editing preserves original_text and sets edited=true
- [ ] POST /api/v1/cv/{id}/bullets/approve/ marks all bullets approved
- [ ] Approval sets approved_at, approved_by, updates status='bullets_approved'

### Phase 3 - CV Assembly
- [ ] POST /api/v1/cv/{id}/assemble/ triggers CV assembly
- [ ] Assembly blocked if status != 'bullets_approved'
- [ ] Service fetches approved bullets from database
- [ ] Calls TailoredContentService.assemble_final_document() with bullets
- [ ] Final CV saved with status='completed'
- [ ] P95 latency ≤ 10 seconds for assembly

### Data Integrity
- [ ] GeneratedDocument.status transitions validated
- [ ] BulletPoint.approved_at requires approved_by
- [ ] original_text preserved when user edits
- [ ] Migration runs without data loss
- [ ] All foreign keys properly indexed

### Backward Compatibility
- [ ] Existing GeneratedDocument records migrated with default status
- [ ] Existing BulletPoint records nullable approval fields
- [ ] API v1 deprecated with clear migration guide
- [ ] Frontend receives breaking change notification

## Design Changes

### Model Changes

**GeneratedDocument (models.py:43-97):**
```python
class GeneratedDocument(models.Model):
    # ... existing fields ...

    STATUS_CHOICES = [
        ('pending', 'Pending'),                # NEW - Initial state
        ('processing', 'Processing'),          # Existing - Phase 1 in progress
        ('bullets_ready', 'Bullets Ready'),    # NEW - Phase 1 complete
        ('bullets_approved', 'Bullets Approved'),  # NEW - User approved
        ('assembling', 'Assembling CV'),       # NEW - Phase 2 in progress
        ('completed', 'Completed'),            # Existing - Phase 2 complete
        ('failed', 'Failed'),                  # Existing - Error state
    ]

    # NEW FIELDS
    bullets_generated_at = models.DateTimeField(null=True, blank=True)
    bullets_count = models.IntegerField(default=0)
    assembled_at = models.DateTimeField(null=True, blank=True)

    # UPDATED (make nullable for Phase 1)
    content = models.JSONField(null=True, blank=True)  # Was default=dict
    metadata = models.JSONField(null=True, blank=True)  # Was default=dict
```

**BulletPoint (models.py:166-250):**
```python
class BulletPoint(models.Model):
    # ... existing fields ...

    # NEW APPROVAL TRACKING FIELDS
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_bullets'
    )
    original_text = models.CharField(
        max_length=150,
        blank=True,
        help_text='LLM-generated text before user edits'
    )
    edited = models.BooleanField(
        default=False,
        help_text='True if user modified text'
    )

    # NEW TIMESTAMPS
    updated_at = models.DateTimeField(auto_now=True)
```

### Service Changes

**CVGenerationService (services/cv_generation_service.py):**
```python
class CVGenerationService:
    """Two-phase CV generation orchestrator."""

    async def prepare_bullets(
        self,
        generation_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> BulletPreparationResult:
        """
        Phase 1: Generate bullets for review.

        Stages:
        1. Parse job description (0% → 20%)
        2. Build artifact data (20% → 40%)
        3. Rank artifacts (40% → 60%)
        4. Generate bullets (60% → 100%)
           - For each artifact: BulletGenerationService.generate_bullets()

        Returns:
            BulletPreparationResult(
                success=True,
                bullets_generated=24,  # 8 artifacts × 3 bullets
                artifacts_used=[1, 5, 12, ...],
                status='bullets_ready'
            )
        """
        # Implementation reuses existing logic from generate_cv_for_job()
        # Stages 1-4, then calls BulletGenerationService instead of generate_cv_content()

    async def assemble_cv(
        self,
        generation_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> CVGenerationResult:
        """
        Phase 2: Assemble CV from approved bullets.

        Preconditions:
        - GeneratedDocument.status == 'bullets_approved'
        - All BulletPoint records have approved_at set

        Stages:
        1. Verify approval status (0% → 30%)
        2. Fetch approved bullets (30% → 50%)
        3. Assemble sections (50% → 80%)
           - Calls TailoredContentService.assemble_final_document(bullets)
        4. Format document (80% → 100%)

        Returns:
            CVGenerationResult(
                success=True,
                content={...final CV...},
                status='completed'
            )
        """
```

### API Changes

**New Endpoints (views.py):**
```python
# Update existing endpoint
@api_view(['POST'])
def generate_cv(request):
    """
    Phase 1: Generate bullets for review.

    CHANGED: Now triggers bullet generation instead of full CV.
    """
    # ... create GeneratedDocument ...
    prepare_cv_bullets_task.delay(generation_id)  # Changed task name
    return Response({
        'generation_id': generation_id,
        'status': 'processing',
        'message': 'Bullet generation in progress'  # Updated message
    }, status=202)

# NEW endpoints
@api_view(['GET'])
def get_generation_bullets(request, generation_id):
    """Get all bullets for a generation (for review)."""
    bullets = BulletPoint.objects.filter(cv_generation_id=generation_id)
    serializer = BulletPointSerializer(bullets, many=True)
    return Response(serializer.data)

@api_view(['PATCH'])
def update_bullet(request, generation_id, bullet_id):
    """Edit a bullet's text before approval."""
    bullet = BulletPoint.objects.get(id=bullet_id, cv_generation_id=generation_id)
    if not bullet.original_text:
        bullet.original_text = bullet.text  # Preserve LLM-generated text
    bullet.text = request.data['text']
    bullet.edited = True
    bullet.save()
    return Response(BulletPointSerializer(bullet).data)

@api_view(['POST'])
def approve_generation_bullets(request, generation_id):
    """Approve all bullets for a generation."""
    generation = GeneratedDocument.objects.get(id=generation_id)
    bullets = BulletPoint.objects.filter(cv_generation_id=generation_id)

    bullets.update(
        approved_at=timezone.now(),
        approved_by=request.user
    )

    generation.status = 'bullets_approved'
    generation.save()

    return Response({'status': 'bullets_approved'})

@api_view(['POST'])
def assemble_cv_from_bullets(request, generation_id):
    """Phase 2: Assemble CV from approved bullets."""
    generation = GeneratedDocument.objects.get(id=generation_id)

    if generation.status != 'bullets_approved':
        return Response(
            {'error': 'Bullets must be approved before assembly'},
            status=400
        )

    assemble_cv_task.delay(generation_id)
    return Response({
        'generation_id': generation_id,
        'status': 'assembling'
    }, status=202)
```

**URL Routing (urls.py):**
```python
urlpatterns = [
    # ... existing routes ...

    # Phase 1 (updated)
    path('cv/generate/', views.generate_cv, name='generate-cv'),

    # Review endpoints (new)
    path('cv/<uuid:generation_id>/bullets/', views.get_generation_bullets),
    path('cv/<uuid:generation_id>/bullets/<int:bullet_id>/', views.update_bullet),
    path('cv/<uuid:generation_id>/bullets/approve/', views.approve_generation_bullets),

    # Phase 2 (new)
    path('cv/<uuid:generation_id>/assemble/', views.assemble_cv_from_bullets),
]
```

### Task Changes

**tasks.py:**
```python
# Rename and update existing task
@shared_task
async def prepare_cv_bullets_task(generation_id):
    """
    Phase 1: Generate bullets for review.

    CHANGED: Previously generate_cv_task (generated complete CV).
    Now only generates bullets, stops at 'bullets_ready' status.
    """
    cv_service = CVGenerationService()

    async def update_progress(percentage: int):
        generation.progress_percentage = percentage
        await sync_to_async(generation.save)()

    result = await cv_service.prepare_bullets(
        generation_id=generation_id,
        progress_callback=update_progress
    )

    if result.success:
        generation.status = 'bullets_ready'
        generation.bullets_generated_at = timezone.now()
        generation.bullets_count = result.bullets_generated
        generation.artifacts_used = result.artifacts_used
    else:
        generation.status = 'failed'
        generation.error_message = result.error_message

    await sync_to_async(generation.save)()

# NEW task
@shared_task
async def assemble_cv_task(generation_id):
    """
    Phase 2: Assemble CV from approved bullets.

    Precondition: status == 'bullets_approved'
    """
    cv_service = CVGenerationService()

    async def update_progress(percentage: int):
        generation.progress_percentage = percentage
        await sync_to_async(generation.save)()

    result = await cv_service.assemble_cv(
        generation_id=generation_id,
        progress_callback=update_progress
    )

    if result.success:
        generation.content = result.content
        generation.metadata = result.metadata
        generation.status = 'completed'
        generation.assembled_at = timezone.now()
        generation.completed_at = timezone.now()
    else:
        generation.status = 'failed'
        generation.error_message = result.error_message

    await sync_to_async(generation.save)()
```

## Migration Strategy

### Database Migrations

**Migration 1: Add GeneratedDocument status values**
```python
# generation/migrations/00XX_add_two_phase_workflow_status.py
operations = [
    migrations.AlterField(
        model_name='generateddocument',
        name='status',
        field=models.CharField(
            max_length=20,
            choices=[
                ('pending', 'Pending'),
                ('processing', 'Processing'),
                ('bullets_ready', 'Bullets Ready'),
                ('bullets_approved', 'Bullets Approved'),
                ('assembling', 'Assembling CV'),
                ('completed', 'Completed'),
                ('failed', 'Failed'),
            ],
            default='pending'  # Changed from 'processing'
        ),
    ),
    # Set existing records to 'pending' or 'completed' based on current status
    migrations.RunPython(migrate_existing_status),
]
```

**Migration 2: Add BulletPoint approval fields**
```python
# generation/migrations/00XX_add_bullet_approval_tracking.py
operations = [
    migrations.AddField(
        model_name='bulletpoint',
        name='approved_at',
        field=models.DateTimeField(null=True, blank=True),
    ),
    migrations.AddField(
        model_name='bulletpoint',
        name='approved_by',
        field=models.ForeignKey(
            'auth.User',
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name='approved_bullets'
        ),
    ),
    migrations.AddField(
        model_name='bulletpoint',
        name='original_text',
        field=models.CharField(max_length=150, blank=True),
    ),
    migrations.AddField(
        model_name='bulletpoint',
        name='edited',
        field=models.BooleanField(default=False),
    ),
    migrations.AddField(
        model_name='bulletpoint',
        name='updated_at',
        field=models.DateTimeField(auto_now=True),
    ),
]
```

### Data Migration

**Existing GeneratedDocument records:**
- If status='completed' → Keep as 'completed'
- If status='processing' → Set to 'pending' (needs regeneration)
- If status='failed' → Keep as 'failed'

**Existing BulletPoint records:**
- All approval fields default to null/false (correct for unapproved bullets)
- No data loss

## Testing Strategy

### Unit Tests

**services/test_cv_generation_service.py:**
```python
class TestPrepareБullets:
    async def test_prepare_bullets_success()
    async def test_prepare_bullets_ranking_artifacts()
    async def test_prepare_bullets_calls_bullet_service()
    async def test_prepare_bullets_progress_callback()
    async def test_prepare_bullets_failure_handling()

class TestAssembleCV:
    async def test_assemble_cv_success()
    async def test_assemble_cv_requires_approved_status()
    async def test_assemble_cv_fetches_approved_bullets()
    async def test_assemble_cv_calls_assemble_final_document()
    async def test_assemble_cv_progress_callback()
```

**tests/test_tasks.py:**
```python
class TestPrepareCVBulletsTask:
    async def test_task_creates_bullets()
    async def test_task_updates_status_bullets_ready()
    async def test_task_handles_failure()

class TestAssembleCVTask:
    async def test_task_requires_bullets_approved()
    async def test_task_assembles_cv()
    async def test_task_updates_status_completed()
```

### Integration Tests

**tests/test_two_phase_workflow.py:**
```python
class TestTwoPhaseWorkflow:
    async def test_end_to_end_workflow()
    async def test_bullet_editing_workflow()
    async def test_regenerate_single_bullet()
    async def test_assembly_blocks_without_approval()
```

### API Tests

**tests/test_views.py:**
```python
class TestCVGenerationAPI:
    def test_generate_triggers_bullet_generation()
    def test_get_bullets_returns_all_bullets()
    def test_update_bullet_preserves_original()
    def test_approve_bullets_sets_status()
    def test_assemble_requires_approval()
```

## Rollout Plan

### Phase A: Documentation ✅
- [x] Update spec-cv-generation.md v1.1.0
- [x] Create ADR-019-two-phase-cv-generation-workflow.md
- [ ] Create ft-009 feature spec (this document)

### Phase B: Backend Models (Week 1, Days 1-2)
- [ ] Write migration tests
- [ ] Create migrations for GeneratedDocument status
- [ ] Create migrations for BulletPoint approval fields
- [ ] Run migrations in development
- [ ] Verify data integrity

### Phase C: Service Layer (Week 1, Days 3-5)
- [ ] Write tests for prepare_bullets() (TDD RED)
- [ ] Implement prepare_bullets() method (TDD GREEN)
- [ ] Write tests for assemble_cv() (TDD RED)
- [ ] Implement assemble_cv() method (TDD GREEN)
- [ ] Refactor for code quality (TDD REFACTOR)
- [ ] Remove old generate_cv_for_job() method

### Phase D: Task Layer (Week 2, Days 1-2)
- [ ] Write tests for prepare_cv_bullets_task
- [ ] Refactor generate_cv_task → prepare_cv_bullets_task
- [ ] Write tests for assemble_cv_task
- [ ] Implement assemble_cv_task
- [ ] Update task routing

### Phase E: API Layer (Week 2, Days 3-5)
- [ ] Write API tests for new endpoints
- [ ] Update generate_cv() view
- [ ] Implement get_generation_bullets()
- [ ] Implement update_bullet()
- [ ] Implement approve_generation_bullets()
- [ ] Implement assemble_cv_from_bullets()
- [ ] Add URL routing
- [ ] Create/update serializers

### Phase F: Integration & Testing (Week 3)
- [ ] Run full test suite
- [ ] Fix integration issues
- [ ] Performance testing (P95 targets)
- [ ] Load testing
- [ ] Security review

### Phase G: Frontend Updates (Week 4)
- [ ] Update CV generation flow
- [ ] Build bullet review UI
- [ ] Build bullet editing UI
- [ ] Build approval workflow
- [ ] Add progress indicators

### Phase H: Deployment (Week 5)
- [ ] Create operation note
- [ ] Deploy to staging
- [ ] Smoke tests
- [ ] Deploy to production with feature flag
- [ ] Monitor metrics
- [ ] Gradual rollout (10% → 50% → 100%)

## Performance Targets

- **Phase 1 (Bullet Generation):** P95 ≤ 20 seconds for 6-8 artifacts
- **Phase 2 (CV Assembly):** P95 ≤ 10 seconds
- **Total Time (with user review):** P95 ≤ 30 seconds active processing + user review time
- **Success Rate:** ≥ 95% for both phases
- **Bullet Quality:** ≥ 8/10 user rating

## Risk Mitigation

**Risk 1: Breaking Change**
- Mitigation: API versioning, v1 deprecation with 30-day notice
- Fallback: Maintain v1 endpoint with auto-approve flag

**Risk 2: User Abandons Review**
- Mitigation: Auto-approve after 7 days with notification
- Tracking: Monitor review completion rate

**Risk 3: Performance Regression**
- Mitigation: A/B testing against old workflow
- Rollback: Feature flag to disable two-phase flow

**Risk 4: Database Migrations Fail**
- Mitigation: Test migrations on production snapshot
- Rollback: Keep old status choices, add new ones (backward compatible)

## Success Metrics

- **User Engagement:** ≥ 70% of users review bullets before approval
- **Edit Rate:** ≥ 30% of users edit at least one bullet
- **Quality Improvement:** ≥ 15% increase in final CV user ratings
- **Performance:** P95 ≤ 30s total (both phases)
- **Success Rate:** ≥ 95% for both phases independently
- **Time to Review:** Median ≤ 5 minutes from bullets_ready → bullets_approved

## Related Documents

- `docs/specs/spec-cv-generation.md` (v1.1.0) - Updated specification
- `docs/adrs/adr-019-two-phase-cv-generation-workflow.md` - Decision rationale
- `docs/adrs/adr-018-generation-service-layer-extraction.md` - Service layer pattern
- `docs/adrs/adr-017-bullet-validation-architecture.md` - Validation logic
- `docs/features/ft-006-three-bullets-per-artifact.md` - Bullet generation feature
- `backend/ARCHITECTURE.md` - Clean Architecture guidance

## Notes

- **Breaking Change:** API v1 deprecated, v2 required for two-phase flow
- **Estimated Effort:** 5 weeks (1 backend + 1 frontend + 1 testing + 1 deployment + 1 buffer)
- **Team Size:** 2 backend engineers, 1 frontend engineer, 1 QA engineer
- **Priority:** High (core product differentiation feature)
- **User Impact:** All CV generation users (100% of active users)
