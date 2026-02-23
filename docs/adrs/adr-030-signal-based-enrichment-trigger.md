# ADR-030: Signal-Based Enrichment Auto-Trigger

**Status:** Accepted
**Date:** 2025-10-30
**Authors:** Claude Code
**Related:** ft-025, ft-010 (auto-enrichment), ft-023 (duplicate task fix), ADR-029 (environment config)

---

## Context

### Problem Statement

Artifacts with only GitHub repository uploads show "No enrichment has been performed yet" because enrichment only auto-triggers for file uploads, not for GitHub evidence creation. This creates an **inconsistent user experience** and **architectural fragility** when adding new evidence source types.

### Current State (Before ADR-030)

The enrichment trigger logic is **scattered and inconsistent**:

| Evidence Source | Trigger Location | Mechanism | Status |
|----------------|------------------|-----------|--------|
| **File Upload** | `artifacts/views.py:158-160` | `transaction.on_commit()` | ✅ Works |
| **GitHub Link** | `artifacts/serializers.py:208` | ❌ MISSING | ❌ Broken |
| **Manual Re-enrich** | `artifacts/views.py:244` | Explicit API call | ✅ Works |

**Code Example (File Upload - Working):**
```python
# backend/artifacts/views.py:158-160
transaction.on_commit(
    lambda: enrich_artifact.delay(artifact_id=artifact.id, user_id=request.user.id)
)
```

**Code Example (GitHub Creation - Broken):**
```python
# backend/artifacts/serializers.py:172-208
def create(self, validated_data):
    evidence_links_data = validated_data.pop('evidence_links', [])
    artifact = Artifact.objects.create(...)

    for link_data in evidence_links_data:
        Evidence.objects.create(artifact=artifact, **link_data)

    return artifact  # ❌ NO ENRICHMENT TRIGGER!
```

### Why This Matters

1. **User Impact:** GitHub-only artifacts require manual re-enrichment (poor UX)
2. **Code Duplication:** Each evidence source needs its own trigger logic
3. **Fragility:** Developers must remember to add triggers for new source types
4. **Inconsistency:** Violates principle of least surprise (file uploads auto-enrich, GitHub doesn't)

---

## Decision

We will implement a **Django signal-based auto-trigger** using the `post_save` signal on the `Evidence` model to centralize enrichment triggering for ALL evidence source types.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Evidence Creation (Any Source Type)                        │
│  - File Upload (views.py)                                   │
│  - GitHub Link (serializers.py)                             │
│  - Future Sources (URLs, LinkedIn, etc.)                    │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ Evidence.objects.create()
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Django Signal: post_save(sender=Evidence)                  │
│  Handler: auto_trigger_enrichment_on_evidence_creation()    │
│  Location: artifacts/signals.py                             │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ if created (new Evidence)
              ▼
┌─────────────────────────────────────────────────────────────┐
│  transaction.on_commit()                                     │
│  → enrich_artifact.delay(artifact_id, user_id)              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

**Signal Handler (`artifacts/signals.py`):**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Evidence
from .tasks import enrich_artifact

@receiver(post_save, sender=Evidence)
def auto_trigger_enrichment_on_evidence_creation(sender, instance, created, **kwargs):
    """
    Auto-trigger LLM enrichment when new evidence is added to an artifact.

    This ensures ALL evidence types (files, GitHub, future sources) trigger
    enrichment consistently without duplicating trigger logic.

    Uses transaction.on_commit() to ensure enrichment starts AFTER the
    database transaction commits, preventing race conditions.

    Related: ft-025 (GitHub enrichment fix), ft-010 (auto-enrichment), ADR-030
    """
    if created:  # Only trigger for NEW evidence (not updates)
        transaction.on_commit(
            lambda: enrich_artifact.delay(
                artifact_id=instance.artifact.id,
                user_id=instance.artifact.user.id
            )
        )
```

**Signal Registration (`artifacts/apps.py`):**
```python
class ArtifactsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artifacts'

    def ready(self):
        """Import signal handlers when app is ready."""
        import artifacts.signals  # noqa: F401
```

---

## Alternatives Considered

### Alternative 1: Add Trigger to Serializer Only (Rejected)

**Approach:** Add `transaction.on_commit()` to `ArtifactCreateSerializer.create()` to match file upload pattern.

**Pros:**
- ✅ Minimal code change
- ✅ Fast to implement
- ✅ Fixes immediate issue

**Cons:**
- ❌ Maintains architectural inconsistency (triggers in 2+ locations)
- ❌ Code duplication (same trigger logic in serializer and view)
- ❌ Fragile (future source types need same fix)
- ❌ Harder to maintain (scattered logic)

**Decision:** Rejected - Technical debt would accumulate with each new source type.

---

### Alternative 2: Hybrid Approach (Rejected)

**Approach:** Quick serializer fix now, refactor to signals later.

**Pros:**
- ✅ Immediate user unblocking
- ✅ Allows learning/validation before refactor

**Cons:**
- ❌ "Later" often never happens (technical debt)
- ❌ Two rounds of testing/deployment
- ❌ Temporary inconsistency confuses developers

**Decision:** Rejected - Signal-based approach is low-risk enough to implement directly.

---

### Alternative 3: Service Layer Method (Rejected)

**Approach:** Create `EvidenceService.create_evidence()` that encapsulates trigger logic.

**Pros:**
- ✅ Explicit service layer (follows llm_services pattern)
- ✅ Testable business logic

**Cons:**
- ❌ Requires refactoring all Evidence creation sites
- ❌ Easy to bypass (developers can still use `Evidence.objects.create()`)
- ❌ More boilerplate than signals

**Decision:** Rejected - Signals are more idiomatic Django and harder to bypass.

---

## Consequences

### Positive

1. **✅ Centralized Logic:** Single source of truth for enrichment triggering
2. **✅ Extensibility:** New evidence types (URLs, LinkedIn, etc.) auto-trigger with zero code changes
3. **✅ Consistency:** ALL evidence sources behave identically
4. **✅ Testability:** Signal handler can be unit tested in isolation
5. **✅ Maintainability:** Developers can't forget to trigger enrichment (automatic via signal)
6. **✅ Backwards Compatible:** Existing file upload flow still works (no breaking changes)

### Negative

1. **⚠️ Implicit Behavior:** Enrichment trigger is "hidden" in signal handler (less obvious than explicit calls)
   - **Mitigation:** Document signal-based triggering in code comments and CLAUDE.md
2. **⚠️ Testing Complexity:** Signal handlers require careful test setup (Django test client auto-triggers signals)
   - **Mitigation:** Use `@override_settings(CELERY_TASK_ALWAYS_EAGER=False)` to prevent side effects in unrelated tests
3. **⚠️ Debugging:** Signal-based flow requires understanding Django signal lifecycle
   - **Mitigation:** Add logging to signal handler for visibility

### Migration Impact

**No database migrations required.**

**Existing Data:**
- Artifacts with evidence but no enrichment job: Users must manually re-enrich (acceptable per user feedback)
- Newly created artifacts: Auto-trigger via signal

**Code Changes:**
- Remove redundant trigger from `artifacts/views.py:158-160` (file upload endpoint)
- Update frontend comment in `ArtifactUpload.tsx:328` (fix misleading docs)

---

## Validation

### Test Coverage

1. **Unit Tests:**
   - Signal handler triggers enrichment on Evidence creation ✓
   - Signal handler does NOT trigger on Evidence update ✓
   - Signal handler does NOT trigger on Evidence deletion ✓

2. **Integration Tests:**
   - GitHub-only artifact creates `ArtifactProcessingJob` ✓
   - File-only artifact creates `ArtifactProcessingJob` ✓
   - Mixed artifact (GitHub + files) creates single job (no duplicates) ✓
   - No-evidence artifact does NOT create job ✓

3. **Manual Tests:**
   - Create GitHub-only artifact → verify enrichment starts
   - Upload files to existing artifact → verify no duplicate enrichment
   - Check Celery logs for task execution

### Success Criteria

- ✅ GitHub-only artifacts show "processing" status instead of "not_started"
- ✅ No duplicate enrichment tasks (ft-023 regression check)
- ✅ All existing tests pass (no breaking changes)
- ✅ New tests achieve >95% coverage for signal handler

---

## Implementation Checklist

- [ ] Create `backend/artifacts/signals.py` with Evidence post_save handler
- [ ] Register signal in `backend/artifacts/apps.py`
- [ ] Remove redundant trigger from `backend/artifacts/views.py:158-160`
- [ ] Add code comments explaining signal-based triggering
- [ ] Update frontend comment in `frontend/src/components/ArtifactUpload.tsx:328`
- [ ] Write unit tests for signal handler
- [ ] Write integration tests for GitHub-only enrichment
- [ ] Run full test suite (verify no regressions)
- [ ] Manual verification with local Docker environment
- [ ] Update CLAUDE.md if needed (enrichment architecture section)

---

## References

- **ft-025:** Fix GitHub Enrichment Trigger (this feature)
- **ft-010:** Auto-Enrichment for File Uploads (original implementation)
- **ft-023:** Fix Duplicate Enrichment Tasks (race condition fix)
- **ADR-029:** Multi-Environment Settings Architecture
- **Django Signals Documentation:** https://docs.djangoproject.com/en/4.2/topics/signals/
- **llm_services Architecture:** Pattern reference for service layers (not directly applicable, signals are better fit here)

---

## Decision Outcome

**ACCEPTED** - Signal-based enrichment auto-trigger provides the best balance of:
- Centralization (single source of truth)
- Extensibility (future-proof for new source types)
- Maintainability (impossible to forget)
- Low Risk (well-established Django pattern)

This decision aligns with the project's **docs-first, TDD-driven workflow** and ensures **consistent user experience** across all evidence source types.
