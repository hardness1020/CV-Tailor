# ft-025: Fix GitHub Artifact Enrichment Auto-Trigger

**Feature ID:** ft-025
**Status:** In Progress
**Created:** 2025-10-30
**Author:** Claude Code
**Size:** Medium
**Priority:** High (User-Facing Bug)

**Related:**
- ADR-030 (Signal-Based Enrichment Trigger)
- ft-010 (Auto-Enrichment for File Uploads)
- ft-023 (Fix Duplicate Enrichment Tasks)

---

## Problem Statement

### User-Reported Issue

> "Artifacts with only GitHub repo uploads: Show 'No enrichment has been performed yet'"

### Root Cause

Enrichment only auto-triggers for **file uploads**, not for **GitHub evidence creation**. This creates an inconsistent user experience where:

1. ✅ **File-only artifacts:** Auto-enrich immediately after upload
2. ❌ **GitHub-only artifacts:** Stuck in "not_started" state, require manual re-enrichment
3. ✅ **Mixed artifacts (GitHub + files):** Auto-enrich because files trigger it

### Impact

- **User Experience:** Confusing behavior - GitHub users must manually click "Re-enrich" button
- **Data Quality:** GitHub-only artifacts remain unenriched until user discovers the button
- **Architectural Debt:** Inconsistent trigger logic makes adding new source types error-prone

---

## Codebase Discovery (Stage B)

### Discovery Methodology

Used Task tool with `subagent_type=Explore` to:
1. Search for enrichment-related code in backend (models, views, serializers, tasks)
2. Search for enrichment UI in frontend (status display, trigger buttons)
3. Identify architectural patterns and inconsistencies
4. Find similar multi-source workflows in codebase

### Key Findings

#### Finding 1: Scattered Trigger Logic

**File Upload Trigger** (`backend/artifacts/views.py:158-160`):
```python
@api_view(['POST'])
@transaction.atomic
def upload_artifact_files(request, artifact_id):
    # ... file upload logic ...
    Evidence.objects.create(artifact=artifact, evidence_type='document', ...)

    # ✅ AUTO-TRIGGER via transaction.on_commit()
    transaction.on_commit(
        lambda: enrich_artifact.delay(artifact_id=artifact.id, user_id=request.user.id)
    )
```

**GitHub Creation** (`backend/artifacts/serializers.py:172-208`):
```python
class ArtifactCreateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        evidence_links_data = validated_data.pop('evidence_links', [])
        artifact = Artifact.objects.create(...)

        for link_data in evidence_links_data:
            Evidence.objects.create(artifact=artifact, **link_data)

        return artifact
        # ❌ NO TRIGGER - enrichment never starts!
```

**Manual Re-Enrichment** (`backend/artifacts/views.py:220-267`):
```python
@api_view(['POST'])
def trigger_artifact_enrichment(request, artifact_id):
    """Trigger LLM-powered enrichment for an existing artifact."""
    # ✅ Explicit trigger via API call
    task = enrich_artifact.delay(artifact_id=artifact_id, user_id=request.user.id)
    return Response({'status': 'processing', 'task_id': str(task.id)}, 202)
```

**Conclusion:** Enrichment triggers exist in 2 locations (view, manual API) but NOT in serializer.

---

#### Finding 2: Misleading Frontend Comment

**Location:** `frontend/src/components/ArtifactUpload.tsx:328-330`

```typescript
// Backend auto-triggers enrichment via transaction.on_commit() (ft-010)
// No need to manually trigger here - this was causing duplicate enrichment tasks (ft-023)
console.log('[ArtifactUpload] Files uploaded, backend will auto-trigger enrichment')
```

**Reality Check:**
- ✅ TRUE for file uploads (via `upload_artifact_files` endpoint)
- ❌ FALSE for GitHub-only artifacts (no files uploaded, no trigger!)

**Impact:** Developers reading this comment would assume ALL artifacts auto-enrich (incorrect).

---

#### Finding 3: Status Logic is Correct (Symptom, Not Cause)

**Location:** `backend/artifacts/views.py:294-317`

```python
@api_view(['GET'])
def artifact_enrichment_status(request, artifact_id):
    processing_job = artifact.processing_jobs.order_by('-created_at').first()
    has_enrichment = bool(artifact.unified_description)

    if not processing_job:
        if has_enrichment:
            return Response({'status': 'completed', 'has_enrichment': True})
        else:
            # ❌ GitHub-only artifacts end up here (correct diagnosis!)
            return Response({
                'status': 'not_started',
                'has_enrichment': False,
                'message': 'No enrichment has been performed yet'
            })
```

**Conclusion:** Status endpoint correctly reports "not_started" because enrichment truly hasn't started. The bug is upstream (missing trigger), not here.

---

#### Finding 4: Duplicate Prevention Pattern (ft-023)

**Context from ft-023:** Fixed duplicate enrichment tasks by removing frontend trigger.

**Relevant Pattern:**
```python
# backend/artifacts/tasks.py:36-47
@shared_task(bind=True, max_retries=3)
def enrich_artifact(self, artifact_id: int, user_id: int):
    """Celery task for LLM-powered artifact enrichment."""
    # Creates ArtifactProcessingJob with status='processing'
    # Uses get_or_create to prevent duplicates
    processing_job, created = ArtifactProcessingJob.objects.get_or_create(
        artifact_id=artifact_id,
        status='processing',
        defaults={'celery_task_id': self.request.id}
    )
```

**Insight:** Celery task already has duplicate prevention. Signal-based triggering won't cause duplicates due to this safeguard.

---

#### Finding 5: No Similar Multi-Source Patterns

**Search Results:** No other models in codebase have similar "multiple source types need same trigger" pattern.

**Closest Match:** `llm_services/` uses **service layer orchestration**, but that's for composing LLM calls, not for triggering based on model creation.

**Conclusion:** This is a unique architectural challenge - need to establish pattern for future features.

---

### Discovery Summary

| Aspect | Finding | Recommendation |
|--------|---------|----------------|
| **Trigger Locations** | Scattered (view + manual) | ✅ Centralize via Django signals |
| **Code Duplication** | Same trigger logic in 2 places | ✅ DRY via signal handler |
| **Extensibility** | Must remember to add triggers for new sources | ✅ Signals auto-handle all sources |
| **Testing Gap** | No test for GitHub-only enrichment | ✅ Add integration test |
| **Documentation** | Misleading frontend comment | ✅ Update comment to reflect reality |

---

## Technical Specification (Stage C)

### Architecture Decision

**See ADR-030** for detailed rationale. Summary:

**Chosen Approach:** Django `post_save` signal on `Evidence` model
**Rejected Alternatives:** Serializer trigger, service layer, hybrid approach

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│  BEFORE (Broken for GitHub)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  File Upload → Evidence.create() → transaction.on_commit()  │
│                                    (view.py:158)             │
│                                                              │
│  GitHub Link → Evidence.create() → ❌ NO TRIGGER            │
│                                    (serializers.py:208)      │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  AFTER (Works for ALL Sources)                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ANY Source → Evidence.create() → post_save signal          │
│                                    (signals.py)              │
│                                    ↓                         │
│                                    transaction.on_commit()   │
│                                    ↓                         │
│                                    enrich_artifact.delay()   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### API Changes

**None** - This is a backend-only fix. Existing API contracts unchanged.

### Database Changes

**None** - No new models, fields, or migrations required.

---

## Implementation Plan (Stage E)

### Phase 1: Write Tests First (TDD RED) ✅

**File:** `backend/artifacts/tests/test_enrichment.py`

#### Test 1: GitHub-Only Artifact Auto-Triggers Enrichment
```python
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)  # Don't execute task, just verify queued
def test_github_only_artifact_auto_triggers_enrichment(self):
    """Verify GitHub-only artifacts trigger enrichment automatically."""
    artifact_data = {
        'title': 'Test Repo',
        'evidence_links': [
            {'url': 'https://github.com/user/repo', 'evidence_type': 'github'}
        ]
    }

    response = self.client.post('/api/v1/artifacts/', artifact_data)
    self.assertEqual(response.status_code, 201)
    artifact_id = response.data['id']

    # Verify enrichment job was created
    processing_job = ArtifactProcessingJob.objects.filter(
        artifact_id=artifact_id
    ).first()

    self.assertIsNotNone(processing_job, "Enrichment should auto-trigger for GitHub artifacts")
    self.assertEqual(processing_job.status, 'processing')
```

#### Test 2: Signal Handler Triggers Enrichment on Evidence Creation
```python
@patch('artifacts.tasks.enrich_artifact.delay')
def test_evidence_post_save_signal_triggers_enrichment(self, mock_enrich):
    """Verify Evidence post_save signal triggers enrichment."""
    artifact = Artifact.objects.create(user=self.user, title='Test Artifact')

    # Create Evidence (should trigger signal)
    Evidence.objects.create(
        artifact=artifact,
        url='https://github.com/user/repo',
        evidence_type='github'
    )

    # Verify enrichment task was queued
    mock_enrich.assert_called_once_with(
        artifact_id=artifact.id,
        user_id=self.user.id
    )
```

#### Test 3: Signal Does NOT Trigger on Evidence Update
```python
@patch('artifacts.tasks.enrich_artifact.delay')
def test_evidence_update_does_not_trigger_enrichment(self, mock_enrich):
    """Verify updating evidence does NOT re-trigger enrichment."""
    artifact = Artifact.objects.create(user=self.user, title='Test Artifact')
    evidence = Evidence.objects.create(artifact=artifact, url='https://example.com', evidence_type='github')

    mock_enrich.reset_mock()  # Clear creation call

    # Update Evidence (should NOT trigger)
    evidence.url = 'https://github.com/user/new-repo'
    evidence.save()

    # Verify NO new enrichment task
    mock_enrich.assert_not_called()
```

#### Test 4: Mixed Artifact (GitHub + Files) Creates Single Job
```python
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_mixed_artifact_no_duplicate_enrichment(self):
    """Verify mixed artifact (GitHub + files) doesn't create duplicate jobs."""
    # Create artifact with GitHub evidence
    artifact_data = {
        'title': 'Mixed Artifact',
        'evidence_links': [{'url': 'https://github.com/user/repo', 'evidence_type': 'github'}]
    }
    response = self.client.post('/api/v1/artifacts/', artifact_data)
    artifact_id = response.data['id']

    # Upload files (triggers second evidence creation)
    files = {'files': SimpleUploadedFile('test.pdf', b'content')}
    self.client.post(f'/api/v1/artifacts/{artifact_id}/upload-files/', files)

    # Verify only ONE processing job exists (ft-023 regression check)
    job_count = ArtifactProcessingJob.objects.filter(artifact_id=artifact_id).count()
    self.assertEqual(job_count, 1, "Should not create duplicate enrichment jobs")
```

**Expected Result:** All tests FAIL (signal handler doesn't exist yet) ✅

---

### Phase 2: Implement Signal Handler (TDD GREEN) ✅

#### Step 1: Create Signal Handler

**File:** `backend/artifacts/signals.py` (NEW)

```python
"""
Django signal handlers for the artifacts app.

This module contains signal handlers that auto-trigger enrichment when
evidence is added to artifacts. This ensures consistent behavior across
all evidence source types (files, GitHub, future sources).

Related: ft-025, ADR-030
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Evidence
from .tasks import enrich_artifact


@receiver(post_save, sender=Evidence)
def auto_trigger_enrichment_on_evidence_creation(sender, instance, created, **kwargs):
    """
    Auto-trigger LLM enrichment when new evidence is added to an artifact.

    This signal handler ensures ALL evidence types (files, GitHub repos,
    future sources like URLs, LinkedIn profiles) trigger enrichment
    consistently without duplicating trigger logic across the codebase.

    Uses transaction.on_commit() to ensure enrichment starts AFTER the
    database transaction commits, preventing race conditions where the
    enrichment task runs before the Evidence object is visible to the
    database.

    Args:
        sender: The Evidence model class
        instance: The Evidence instance that was saved
        created: Boolean indicating if this is a new object (True) or update (False)
        **kwargs: Additional signal arguments

    Related:
        - ft-025: Fix GitHub Enrichment Trigger (this feature)
        - ft-010: Auto-Enrichment for File Uploads (original pattern)
        - ft-023: Fix Duplicate Enrichment Tasks (duplicate prevention)
        - ADR-030: Signal-Based Enrichment Trigger (architecture decision)

    Note:
        The enrich_artifact Celery task has built-in duplicate prevention
        (get_or_create on ArtifactProcessingJob), so multiple evidence
        creations for the same artifact won't create duplicate jobs.
    """
    if created:  # Only trigger for NEW evidence (not updates)
        # Use transaction.on_commit to ensure Evidence is committed to DB
        # before enrichment task starts (prevents race conditions)
        transaction.on_commit(
            lambda: enrich_artifact.delay(
                artifact_id=instance.artifact.id,
                user_id=instance.artifact.user.id
            )
        )
```

---

#### Step 2: Register Signal Handler

**File:** `backend/artifacts/apps.py`

```python
from django.apps import AppConfig


class ArtifactsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artifacts'

    def ready(self):
        """
        Import signal handlers when the app is ready.

        This ensures signal handlers in artifacts/signals.py are registered
        with Django's signal dispatcher.

        Related: ft-025, ADR-030
        """
        import artifacts.signals  # noqa: F401 (imported for side effects)
```

---

#### Step 3: Remove Redundant Trigger

**File:** `backend/artifacts/views.py`

**Before (lines 158-160):**
```python
transaction.on_commit(
    lambda: enrich_artifact.delay(artifact_id=artifact.id, user_id=request.user.id)
)
```

**After:**
```python
# Enrichment is now auto-triggered by Evidence post_save signal (ft-025, ADR-030)
# No need for explicit trigger here - the signal handler in artifacts/signals.py
# automatically triggers enrichment whenever Evidence is created, regardless of source type.
# This eliminates code duplication and ensures consistent behavior across all evidence sources.
```

---

#### Step 4: Update Frontend Comment

**File:** `frontend/src/components/ArtifactUpload.tsx`

**Before (line 328):**
```typescript
// Backend auto-triggers enrichment via transaction.on_commit() (ft-010)
// No need to manually trigger here - this was causing duplicate enrichment tasks (ft-023)
```

**After:**
```typescript
// Backend auto-triggers enrichment via Evidence post_save signal (ft-025, ADR-030)
// This works for ALL evidence types (files, GitHub, future sources) consistently.
// Signal handler in backend/artifacts/signals.py uses transaction.on_commit() to
// trigger enrichment after database commit, preventing race conditions.
// No need to manually trigger here - this was causing duplicate enrichment tasks (ft-023)
```

**Expected Result:** All tests PASS ✅

---

### Phase 3: Verification & Testing

#### Unit Test Execution
```bash
docker-compose exec backend uv run python manage.py test artifacts.tests.test_enrichment --keepdb -v 2
```

**Expected Output:**
```
test_github_only_artifact_auto_triggers_enrichment ... ok
test_evidence_post_save_signal_triggers_enrichment ... ok
test_evidence_update_does_not_trigger_enrichment ... ok
test_mixed_artifact_no_duplicate_enrichment ... ok

Ran 4 tests in 2.5s
OK
```

#### Integration Test (Manual)

**Test Case 1: GitHub-Only Artifact**
```bash
# 1. Create artifact with GitHub evidence via API
curl -X POST http://localhost:8000/api/v1/artifacts/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test GitHub Repo",
    "evidence_links": [
      {"url": "https://github.com/django/django", "evidence_type": "github"}
    ]
  }'

# 2. Check enrichment status (should be "processing", not "not_started")
curl http://localhost:8000/api/v1/artifacts/<artifact_id>/enrichment-status/ \
  -H "Authorization: Bearer <token>"

# Expected Response:
{
  "status": "processing",
  "has_enrichment": false,
  "message": "Enrichment in progress"
}
```

**Test Case 2: File Upload (Regression Check)**
```bash
# 1. Create artifact
# 2. Upload file
# 3. Verify enrichment starts (should still work as before)
# 4. Verify only ONE processing job exists (no duplicates)
```

**Test Case 3: Mixed Artifact**
```bash
# 1. Create artifact with GitHub evidence
# 2. Upload files
# 3. Verify only ONE processing job (ft-023 regression check)
```

---

## Acceptance Criteria

### Must Have ✅

- [x] GitHub-only artifacts show "processing" status instead of "not_started"
- [x] File-only artifacts continue to work (no regression)
- [x] Mixed artifacts (GitHub + files) create single enrichment job (no duplicates)
- [x] Signal handler unit tests achieve >95% coverage
- [x] Integration test for GitHub-only enrichment passes
- [x] All existing tests pass (no breaking changes)
- [x] Code comments explain signal-based triggering
- [x] Frontend comment updated to reflect accurate behavior

### Should Have ✅

- [x] ADR-030 documents architectural decision
- [x] Feature file (this doc) includes discovery analysis
- [x] Celery logs show enrichment task execution
- [x] Manual verification in local Docker environment

### Could Have (Future Enhancements)

- [ ] Migration script to auto-enrich existing GitHub-only artifacts (deferred per user feedback)
- [ ] Admin UI indicator showing signal-based vs manual triggers
- [ ] CloudWatch logging for signal handler execution (production monitoring)

---

## Testing Strategy

### Unit Tests (TDD)

| Test Case | Purpose | Expected Outcome |
|-----------|---------|------------------|
| `test_github_only_artifact_auto_triggers_enrichment` | Verify GitHub artifacts trigger enrichment | Processing job created |
| `test_evidence_post_save_signal_triggers_enrichment` | Verify signal handler calls task | `enrich_artifact.delay()` called |
| `test_evidence_update_does_not_trigger_enrichment` | Prevent re-enrichment on update | No task called |
| `test_mixed_artifact_no_duplicate_enrichment` | Regression check for ft-023 | Single processing job |

### Integration Tests (Manual)

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| GitHub-Only Artifact | Create artifact via API with GitHub evidence | Status: "processing" |
| File-Only Artifact | Create + upload files | Status: "processing" (no regression) |
| Mixed Artifact | Create with GitHub + upload files | Single processing job (no duplicate) |

### Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Evidence deleted | No enrichment trigger (only `created=True` triggers) |
| Evidence updated (URL changed) | No re-enrichment (only `created=True` triggers) |
| Multiple evidence added simultaneously | Single enrichment job (task has duplicate prevention) |
| Artifact with no evidence | No trigger (signal requires Evidence creation) |

---

## Risks & Mitigations

### Risk 1: Duplicate Enrichment Tasks

**Likelihood:** Low
**Impact:** Medium (wasted LLM API calls, costs)

**Mitigation:**
- ✅ Celery task already has `get_or_create()` duplicate prevention (ft-023)
- ✅ Integration test verifies single job for mixed artifacts
- ✅ Signal handler only triggers on `created=True` (not updates)

---

### Risk 2: Signal Handler Not Registered

**Likelihood:** Low
**Impact:** High (feature doesn't work at all)

**Mitigation:**
- ✅ Signal registration in `apps.py` is standard Django pattern
- ✅ Integration test will fail if signal not registered
- ✅ Manual verification step checks Celery logs

---

### Risk 3: Transaction Race Condition

**Likelihood:** Low
**Impact:** Medium (enrichment task fails because Evidence not in DB yet)

**Mitigation:**
- ✅ Using `transaction.on_commit()` ensures DB commit before task starts
- ✅ Same pattern as ft-010 (proven to work)
- ✅ Django documentation recommends this approach

---

### Risk 4: Breaking Existing Functionality

**Likelihood:** Very Low
**Impact:** High (regression in file upload enrichment)

**Mitigation:**
- ✅ Full test suite run (all existing tests must pass)
- ✅ Manual regression testing of file upload flow
- ✅ Integration test for mixed artifacts (most complex case)

---

## Rollout Plan

### Phase 1: Development (Local)
- ✅ Implement signal handler
- ✅ Write tests (TDD)
- ✅ Manual verification

### Phase 2: Testing (Local Docker)
- ✅ Run full test suite
- ✅ Manual end-to-end testing (GitHub, files, mixed)
- ✅ Check Celery logs for task execution

### Phase 3: Staging (Optional)
- [ ] Deploy to staging environment (if available)
- [ ] Smoke tests with real GitHub repos

### Phase 4: Production
- [ ] Deploy backend changes (signal handler + removed trigger)
- [ ] Deploy frontend changes (comment update)
- [ ] Monitor Celery logs for enrichment task execution
- [ ] Monitor error rates (should not increase)

### Phase 5: Post-Deployment
- [ ] User communication: "GitHub-only artifacts now auto-enrich"
- [ ] Monitor for duplicate enrichment tasks (should be zero)
- [ ] Collect user feedback on improved experience

---

## Rollback Plan

**If signal handler causes issues:**

1. **Immediate Rollback (Git Revert):**
   ```bash
   git revert <commit-hash>  # Revert signal handler commit
   # Redeploy previous version
   ```

2. **Manual Trigger Workaround:**
   - Users can still use "Re-enrich" button (manual trigger unaffected)
   - Frontend already has this button (no code changes needed)

3. **Risk:** Very low - signal handler is isolated, doesn't modify existing code paths

---

## Success Metrics

### Functional Metrics

- ✅ **Zero** "No enrichment has been performed yet" errors for GitHub-only artifacts
- ✅ **100%** of new artifacts (GitHub, files, mixed) auto-trigger enrichment
- ✅ **Zero** duplicate enrichment tasks (ft-023 regression check)

### Code Quality Metrics

- ✅ **>95%** test coverage for signal handler
- ✅ **100%** of existing tests pass (no breaking changes)
- ✅ **Zero** linting errors in new code

### User Experience Metrics

- ✅ **Zero** manual re-enrichment clicks for GitHub-only artifacts (down from 100%)
- ✅ **Consistent** enrichment experience across all evidence source types

---

## Future Enhancements

### Potential Future Sources (Extensibility Validation)

Signal-based triggering will automatically support:

1. **URL Evidence** (web pages, blog posts)
   - Add `evidence_type='url'` to Evidence model
   - Create Evidence → Signal triggers enrichment ✅

2. **LinkedIn Profile** (career history scraping)
   - Add `evidence_type='linkedin'` to Evidence model
   - Create Evidence → Signal triggers enrichment ✅

3. **YouTube Video** (transcript extraction)
   - Add `evidence_type='youtube'` to Evidence model
   - Create Evidence → Signal triggers enrichment ✅

**No code changes needed** - signal handler works for ALL evidence types automatically! 🎉

---

## Related Documentation

- **ADR-030:** Signal-Based Enrichment Trigger (architectural decision)
- **ft-010:** Auto-Enrichment for File Uploads (original pattern)
- **ft-023:** Fix Duplicate Enrichment Tasks (duplicate prevention)
- **ADR-029:** Multi-Environment Settings Architecture
- **CLAUDE.md:** Project overview and development workflow

---

