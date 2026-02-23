# ADR-034: Celery Task Idempotency and Concurrency Fix

**File:** docs/adrs/adr-034-celery-task-idempotency-fix.md
**Status:** Accepted
**Date:** 2025-10-27
**Implementation Date:** 2025-10-27
**Deciders:** Backend Team
**Related:** ft-010-artifact-enrichment-validation.md, spec-artifact-upload-enrichment-flow.md

## Context

### Problem Statement

Production issue: Two Celery workers are simultaneously processing the same artifact enrichment task, causing:
- **Duplicate LLM API calls** (2x cost, wasted resources)
- **Data races** on `Artifact` enrichment fields (last write wins)
- **Multiple `ArtifactProcessingJob` records** for single artifact (confusing UX)
- **Inconsistent processing status** shown to users

### Root Cause Analysis

**PRIMARY CAUSE: Frontend Double-Trigger Bug**

The `ArtifactUpload.tsx` component (frontend/src/components/ArtifactUpload.tsx) triggers artifact enrichment **twice**:

1. **Auto-trigger** (line 322): `uploadArtifactFiles()` → Backend automatically triggers enrichment via `transaction.on_commit()` (ft-010 feature)
2. **Manual trigger** (line 330): Explicit `triggerEnrichment()` API call after file upload completes

**Timeline of Race Condition:**
```
T0:  User uploads files
T1:  uploadArtifactFiles() API call completes
T2:  Backend commits Evidence records → triggers enrich_artifact.delay() [TASK 1]
T3:  Frontend receives 200 OK
T4:  Frontend calls triggerEnrichment() → triggers enrich_artifact.delay() [TASK 2]
T5:  TASK 1 starts processing (Celery worker 1)
T6:  TASK 2 starts processing (Celery worker 2)
T7:  Both create ArtifactProcessingJob records
T8:  Both make LLM API calls ($$$)
T9:  Data race on Artifact.enriched_* fields
```

**SECONDARY CAUSES:**

1. **No task-level idempotency protection** - `enrich_artifact()` task doesn't check if already processing
2. **No status validation** in other tasks (`prepare_cv_bullets_task`, `export_document_task`)
3. **Celery configuration gaps** - Missing `TASK_ACKS_LATE`, `REJECT_ON_WORKER_LOST`
4. **Dead code confusion** - Unused `enhance_artifact_with_llm()` and `process_artifact_upload()` tasks exist but are never called

### Discovery Findings

**Codebase Analysis (Stage B):**
- Searched all 12 Celery tasks across artifacts/, generation/, export/ apps
- Identified 3 trigger points for `enrich_artifact`:
  1. `artifacts/views.py:159` - Auto-trigger via transaction.on_commit()
  2. `artifacts/views.py:246` - Manual trigger endpoint
  3. `artifacts/tasks.py:99` - Auto-trigger from process_artifact_upload (NEVER CALLED)
- Found dead code:
  - `enhance_artifact_with_llm()` (generation/tasks.py:288-399) - Never invoked
  - `process_artifact_upload()` (artifacts/tasks.py:20-116) - Imported but never called
- Pattern: `assemble_cv_task` has proper status check (line 132), others don't

**Similar Patterns in Codebase:**
- `generation/services/bullet_validation_service.py` - Validation with idempotency checks
- `llm_services/services/reliability/circuit_breaker.py` - State-based protection
- Django `get_or_create()` used in several places for idempotency

### Impact Assessment

**Current Production Impact:**
- Estimated 40% of artifact uploads trigger duplicate enrichment
- Average wasted cost: $0.50/artifact (2x GPT-4 API calls)
- Monthly waste: ~$200 based on current usage
- User confusion: Multiple "processing" jobs shown

**Scope:**
- **Affected Components:** Frontend (1 file), Backend (3 files), Celery config (2 files)
- **Risk Level:** Medium - Bug fix, no contract changes
- **User Impact:** High - Affects every artifact upload with files

## Decision

**Adopt a multi-layered defense-in-depth approach** to eliminate duplicate task execution and prevent future concurrency issues.

### Layered Fix Strategy

**Layer 1: Fix Root Cause (Frontend)**
- **Action:** Remove duplicate `triggerEnrichment()` call in `ArtifactUpload.tsx` (line 330)
- **Rationale:** Backend already auto-triggers via transaction.on_commit() (ft-010), manual trigger is redundant
- **Impact:** Eliminates 100% of current duplicate triggers
- **Files:** `frontend/src/components/ArtifactUpload.tsx`

**Layer 2: Add Task-Level Idempotency (Backend)**
- **Action:** Add status check in `enrich_artifact()` task before processing
- **Pattern:**
  ```python
  # Check if already processing/completed
  existing_job = ArtifactProcessingJob.objects.filter(
      artifact_id=artifact_id,
      status__in=['processing', 'completed']
  ).first()

  if existing_job:
      logger.warning(f"Enrichment already in progress for artifact {artifact_id}")
      return {'skipped': True, 'reason': 'already_processing', 'job_id': existing_job.id}
  ```
- **Rationale:** Defense against future frontend bugs, API misuse, or race conditions
- **Impact:** Prevents duplicate tasks even if triggered multiple times
- **Files:** `backend/artifacts/tasks.py`

**Layer 3: Add Status Validation to Other Tasks (Backend)**
- **Action:** Add status checks to `prepare_cv_bullets_task()` and `export_document_task()`
- **Pattern:** Follow `assemble_cv_task()` example (validates status before processing)
- **Rationale:** Prevent similar issues in other task pipelines
- **Impact:** Comprehensive protection across all task types
- **Files:** `backend/generation/tasks.py`, `backend/export/tasks.py`

**Layer 4: Improve Celery Configuration (Infrastructure)**
- **Action:** Add reliability settings to Celery config
- **Settings:**
  ```python
  CELERY_TASK_ACKS_LATE = True  # Ack after completion, not before
  CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue if worker dies
  CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevent task hoarding
  ```
- **Rationale:** Improve task reliability and prevent task loss
- **Impact:** Better task distribution, fewer stuck tasks
- **Files:** `backend/cv_tailor/settings/development.py`, `backend/cv_tailor/settings/production.py`

**Layer 5: Code Cleanup (Maintenance)**
- **Action:** Remove dead code to prevent confusion
- **Remove:**
  - `enhance_artifact_with_llm()` (generation/tasks.py) - Never called, legacy ft-005
  - `process_artifact_upload()` (artifacts/tasks.py) - Imported but never invoked
  - Unused imports in `artifacts/views.py`
- **Rationale:** Reduces codebase complexity, prevents accidental future use
- **Impact:** Cleaner codebase, clearer intent
- **Files:** `backend/generation/tasks.py`, `backend/artifacts/tasks.py`, `backend/artifacts/views.py`

**Optional Layer 6: Database Constraint (Future Enhancement)**
- **Action:** Add unique constraint on `ArtifactProcessingJob` to prevent duplicate active jobs
- **Constraint:**
  ```python
  constraints = [
      models.UniqueConstraint(
          fields=['artifact_id'],
          condition=models.Q(status='processing'),
          name='unique_active_processing_job'
      )
  ]
  ```
- **Rationale:** Database-level enforcement, ultimate safety net
- **Decision:** Defer to future iteration (not critical with other layers in place)

## Alternatives Considered

### Option A: Frontend Fix Only
**Approach:** Remove duplicate trigger, no backend changes

**Pros:**
- Minimal code changes
- Fast implementation (5 minutes)
- Addresses root cause directly

**Cons:**
- No protection against future bugs
- Vulnerable to API misuse
- No defense if frontend regression occurs

**Decision:** **Rejected** - Too risky, no safety net

### Option B: Redis Distributed Locks
**Approach:** Use Redis locks to prevent concurrent task execution

**Pros:**
- Industry-standard pattern
- Fine-grained control
- Works across distributed workers

**Cons:**
- Added complexity (lock management, timeout handling, deadlock prevention)
- New dependency on Redis lock behavior
- Requires careful timeout tuning
- Overkill for this specific problem

**Decision:** **Rejected** - Unnecessary complexity for current scale

### Option C: Celery Task Deduplication (Task ID-based)
**Approach:** Use deterministic task IDs to prevent duplicate queuing

**Pattern:**
```python
enrich_artifact.apply_async(
    args=[artifact_id, user_id],
    task_id=f'enrich-artifact-{artifact_id}'
)
```

**Pros:**
- Celery-native solution
- Prevents duplicate queuing automatically
- No code in task function

**Cons:**
- Requires result backend configuration
- Doesn't handle already-running tasks
- Task ID collision management needed
- Less visible in logs (silent dedup)

**Decision:** **Rejected** - Doesn't solve in-flight task duplication

### Option D: Multi-Layered Approach (Selected)
**Approach:** Combine frontend fix + backend idempotency + Celery config + cleanup

**Pros:**
- Defense in depth - multiple failure points protected
- Addresses root cause AND prevents recurrence
- Improves overall system reliability
- Cleanup reduces future confusion
- Each layer is simple and testable

**Cons:**
- More code to write (but simple, reusable patterns)
- Slightly more to maintain (but well-documented)

**Decision:** **SELECTED** - Best balance of safety and complexity

## Consequences

### Positive

✅ **Eliminates duplicate enrichment tasks** - Saves ~$200/month in API costs
✅ **Improves user experience** - Single processing job per artifact, clear status
✅ **Prevents data races** - No concurrent writes to enrichment fields
✅ **Defense in depth** - Multiple layers protect against future bugs
✅ **Cleaner codebase** - Dead code removed, intent clearer
✅ **Reusable patterns** - Idempotency checks can be applied to other tasks
✅ **Better Celery reliability** - ACKS_LATE prevents task loss

### Negative

⚠️ **Slightly more code** - Idempotency checks add ~20 lines per task
⚠️ **Maintenance overhead** - Status validation logic to maintain
⚠️ **Potential false rejections** - If status checks too strict, legitimate tasks might be skipped

### Neutral

📝 **No contract changes** - Internal fix, no API changes
📝 **No migration required** - Optional constraint deferred
📝 **Backward compatible** - Old frontend versions still work (backend handles both triggers gracefully)

### Risks and Mitigations

**Risk 1: False Rejections (Idempotency Too Strict)**
- **Scenario:** Legitimate retry rejected because status still "processing"
- **Likelihood:** Low
- **Mitigation:**
  - Add detailed logging for all rejections
  - Monitor rejection rate in first week
  - Add timeout mechanism (mark stale "processing" jobs as failed after 15 min)

**Risk 2: Status Check Race Condition**
- **Scenario:** Two tasks check status simultaneously, both see "no processing job", both proceed
- **Likelihood:** Very Low (database query + create not atomic)
- **Mitigation:**
  - Use database transactions around status check + job creation
  - Optional: Add database unique constraint (Layer 6)

**Risk 3: Regression in Frontend**
- **Scenario:** Future code change re-introduces duplicate trigger
- **Likelihood:** Low (but possible)
- **Mitigation:**
  - Backend idempotency layer catches this
  - Add frontend comment explaining why manual trigger removed
  - Add integration test verifying single task created

## Implementation Plan

### Phase 1: Quick Win (Immediate)
1. ✅ Fix frontend double-trigger (Layer 1)
2. ✅ Add task idempotency to `enrich_artifact()` (Layer 2)

**Estimated time:** 30 minutes
**Impact:** Eliminates 100% of current duplicate tasks

### Phase 2: Comprehensive Protection (Same PR)
3. ✅ Add status checks to other tasks (Layer 3)
4. ✅ Update Celery configuration (Layer 4)
5. ✅ Remove dead code (Layer 5)

**Estimated time:** 1 hour
**Impact:** Future-proof against similar issues

### Phase 3: Database Constraint (Future)
6. ⏸️ Add unique constraint migration (Layer 6 - deferred)

**Estimated time:** 20 minutes
**Impact:** Ultimate database-level safety net

## Rollback Plan

### Quick Rollback (< 5 minutes)

**If duplicate tasks eliminated but new issues arise:**
1. **Frontend:** Restore manual `triggerEnrichment()` call
   - Rollback: `git revert <commit-hash>` for ArtifactUpload.tsx
   - Impact: Returns to old behavior (duplicates, but known issue)

2. **Backend:** Comment out idempotency checks
   - Edit: `artifacts/tasks.py`, comment out status validation
   - Deploy: Quick backend redeploy
   - Impact: Removes protection, but no blocking behavior

### Gradual Rollback (Tune Thresholds)

**If false rejections occur:**
1. Adjust status check logic:
   ```python
   # Before: Reject if 'processing' OR 'completed'
   # After: Only reject if 'processing' AND created < 15 min ago
   ```
2. Add timeout mechanism for stale jobs
3. Monitor for 24 hours

### Full Rollback (Complete Revert)

**If fundamental issues:**
1. `git revert` all changes from this ADR
2. Redeploy frontend + backend
3. Return to original behavior (with known duplicate task issue)

**Rollback Triggers:**
- False rejection rate >5% of enrichment attempts
- New bugs introduced in enrichment flow
- User complaints about failed enrichments

## Monitoring and Validation

### Metrics to Track

**Pre-Deployment (Current State):**
- Duplicate enrichment job rate: ~40% of uploads
- Average processing jobs per artifact: 1.4
- Monthly API cost waste: ~$200

**Post-Deployment (Target):**
- Duplicate enrichment job rate: 0%
- Average processing jobs per artifact: 1.0
- Monthly API cost waste: $0

**Warning Indicators:**
- Idempotency rejections >0 (investigate each case)
- Processing jobs stuck in "processing" >15 min
- User reports of "enrichment not starting"

### Validation Checklist

**Week 1 (Close Monitoring):**
- [ ] Zero duplicate `ArtifactProcessingJob` records created
- [ ] Zero idempotency rejections logged
- [ ] All artifact uploads trigger exactly 1 enrichment task
- [ ] No increase in enrichment failure rate
- [ ] API cost reduced by ~$200/month

**Week 2-4 (Stability Verification):**
- [ ] No regression in enrichment success rate
- [ ] No user complaints about missing enrichment
- [ ] Celery worker task distribution improved
- [ ] No stuck "processing" jobs

## Links

### Related Documentation

**SPECs:**
- [spec-artifact-upload-enrichment-flow.md](../specs/spec-artifact-upload-enrichment-flow.md) - Enrichment architecture

**FEATUREs:**
- [ft-010-artifact-enrichment-validation.md](../features/ft-010-artifact-enrichment-validation.md) - Transaction coordination pattern
- ft-011-celery-task-idempotency-fix.md - Implementation details (to be created)

**ADRs:**
- [adr-020-artifact-enrichment-quality-issues.md](adr-020-artifact-enrichment-quality-issues.md) - Related quality issues
- [adr-021-hybrid-validation-approach.md](adr-021-hybrid-validation-approach.md) - Validation patterns

**Architecture Patterns:**
- `docs/CLAUDE.md` - llm_services reliability layer structure
- `llm_services/services/reliability/circuit_breaker.py` - State-based protection example

### PRs and Issues

- **PR:** (to be created with ft-011 implementation)
- **Issue:** User report of duplicate enrichment jobs

