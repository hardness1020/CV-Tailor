# Feature — 045 Evidence Review & Acceptance Workflow

**File:** docs/features/ft-045-evidence-review-workflow.md
**Owner:** Engineering Team
**TECH-SPECs:** `spec-frontend.md` (v3.0.0), `spec-api.md` (v4.9.0), `spec-llm.md` (v4.3.0)
**PRD:** `prd.md` (v1.5.0) - Evidence Review & Acceptance workflow requirements
**Discovery:** `disco-001-evidence-review-workflow.md` - Comprehensive workflow analysis
**ADRs:**
- ADR-046: Blocking Evidence Review Workflow in Artifact Upload Wizard
- ADR-047: EnhancedEvidence Consolidation (Remove ExtractedContent)
- ADR-048: LLM-Based Re-unification from User-Edited Evidence

**Status:** Approved (2025-01-06)
**Priority:** P0 (Critical for evidence quality and hallucination prevention)
**Target Date:** 2025-01-20 (2 weeks)
**Dependencies:** ft-022 (Unified Wizard Pattern), ft-005 (Multi-Source Preprocessing), ft-013 (GitHub Agent Traversal)

---

## Overview

Implement mandatory evidence review and acceptance workflow in the artifact upload wizard to prevent AI hallucinations from propagating to CV/cover letter generation. Users must review and accept ALL extracted evidence content before artifact finalization, with inline editing capabilities to correct errors.

**User Problem:**
> "The AI extracted wrong technologies from my project. By the time I noticed in the CV, I had to start over." (Beta user feedback)

**Solution:**
- Blocking wizard Steps 5 & 6 (Processing + Evidence Review)
- Inline editing for summaries, technologies, achievements
- 100% acceptance requirement (no shortcuts)
- LLM re-unification from user-edited evidence

---

## Stage B Discovery Findings

**Source:** `docs/discovery/disco-001-evidence-review-workflow.md`

### Test Impact Analysis

**Tests to Update (103 tests affected):**
1. **Artifact Upload Tests** (8 tests)
   - `frontend/src/components/__tests__/ArtifactUpload.test.tsx` - Update wizard to 6 steps
   - Add ProcessingStep and EvidenceReviewStep rendering tests

2. **Evidence API Tests** (12 tests)
   - `backend/artifacts/tests/test_views.py` - Update EnhancedEvidence serialization
   - Add acceptance status endpoint tests

3. **Service Layer Tests** (18 tests)
   - `backend/llm_services/tests/unit/services/core/test_artifact_enrichment_service.py`
   - Update unify_content_with_llm tests, add reunify_from_accepted_evidence tests

4. **Model Tests** (5 tests)
   - `backend/llm_services/tests/test_models.py` - EnhancedEvidence.accepted field usage

**Tests to Remove:**
- ExtractedContent-related tests (32 files) - Will be cleaned up in ADR-047 implementation

**New Tests to Add (15 backend + 8 frontend = 23 tests):**

**Backend Unit Tests (15):**
1. `test_accept_evidence` - Mark evidence as accepted
2. `test_reject_evidence` - Mark evidence as rejected
3. `test_edit_evidence_content` - Update processed_content
4. `test_get_acceptance_status` - Fetch acceptance summary
5. `test_finalize_evidence_review_success` - All accepted
6. `test_finalize_evidence_review_partial` - Not all accepted (403 error)
7. `test_reunify_from_accepted_evidence` - LLM re-unification
8. `test_reunify_with_user_context` - User context integration
9. `test_reunify_excluded_rejected` - Rejected evidence not used
10. `test_reunify_confidence_calculation` - Processing confidence
11. `test_reunify_technologies_extraction` - Technology deduplication
12. `test_reunify_achievements_extraction` - Achievement aggregation
13. `test_reunify_llm_failure_fallback` - Graceful degradation
14. `test_edit_evidence_validation` - Invalid content rejected
15. `test_acceptance_status_calculation` - can_finalize logic

**Frontend Unit Tests (8):**
1. `test_processing_step_polling` - Enrichment status polling
2. `test_processing_step_completion` - Auto-advance to Step 6
3. `test_evidence_review_step_rendering` - Evidence card display
4. `test_evidence_card_editing` - Inline content editing
5. `test_evidence_accept_action` - Accept evidence action
6. `test_evidence_reject_action` - Reject evidence action
7. `test_finalize_button_state` - Disabled until 100% accepted
8. `test_finalize_success_redirect` - Navigate to detail page

**Integration Tests (8):**
1. `test_full_wizard_flow_with_review` - Steps 1-6 end-to-end
2. `test_evidence_edit_propagates_to_artifact` - User edit → finalize → verify artifact updated
3. `test_rejected_evidence_excluded` - Rejected evidence not in unified description
4. `test_acceptance_status_updates` - Real-time acceptance tracking
5. `test_finalize_llm_reunification` - LLM call integration
6. `test_frontend_backend_evidence_review_flow` - Full stack integration
7. `test_mobile_evidence_review_ux` - Touch-friendly editing on mobile
8. `test_error_handling_llm_failure` - Fallback when LLM fails

**Coverage Gaps:**
- Circuit breaker scenarios for re-unification (need integration tests)
- Mobile touch editing UX (need manual testing + Playwright)
- Confidence badge color thresholds (need visual regression tests)

**Test Update Checklist:**
- [ ] Update ArtifactUpload wizard tests (6 steps)
- [ ] Add ProcessingStep unit tests (2 tests)
- [ ] Add EvidenceReviewStep unit tests (6 tests)
- [ ] Add backend API endpoint tests (15 tests)
- [ ] Add integration tests (8 tests)
- [ ] Clean up ExtractedContent tests (Stage F)
- [ ] Add visual regression tests for ConfidenceBadge (Stage H)

### Existing Implementation Analysis

**Similar Features:**
1. **Bullet Review Workflow (ft-024):**
   - Location: `frontend/src/components/BulletReviewStep.tsx` (261 lines)
   - Reusable Patterns:
     - Inline editing with auto-save on blur
     - Accept/reject/regenerate actions
     - Progress tracking (X/Y accepted)
     - Disabled finalize button until 100% accepted
   - **Reuse:** Copy review card pattern, acceptance tracking logic

2. **Artifact Upload Wizard (ft-022):**
   - Location: `frontend/src/components/ArtifactUpload.tsx` (5 steps currently)
   - Reusable Patterns:
     - WizardFlow container with step indicators
     - useWizardProgress hook for progress tracking
     - CancelConfirmationDialog for unsaved changes
   - **Reuse:** Extend to 6 steps, add new ProcessingStep and EvidenceReviewStep

3. **Enrichment Processing Feedback (ft-015):**
   - Location: `frontend/src/components/ArtifactDetailPage.tsx`
   - Reusable Patterns:
     - LoadingOverlay component for blocking spinners
     - Polling enrichment_status with 3-second intervals
     - Error handling for failed enrichment
   - **Reuse:** LoadingOverlay for Step 5, polling pattern

**Reusable Components:**
1. **ConfidenceBadge** (`frontend/src/components/ConfidenceBadge.tsx`, 247 lines)
   - Color-coded badges (red <50%, yellow 50-80%, green ≥80%)
   - Already implemented with Tailwind variants
   - **Reuse:** Display processing_confidence in EvidenceCard

2. **LoadingOverlay** (`frontend/src/components/LoadingOverlay.tsx`)
   - Non-dismissible blocking spinner with message
   - **Reuse:** Step 5 processing screen

3. **useGenerationStatus Hook** (`frontend/src/hooks/useGenerationStatus.ts`)
   - Polling pattern with race condition prevention
   - Auto-stop on terminal states
   - **Reuse:** Adapt for enrichment_status polling in Step 5

4. **Circuit Breaker** (`backend/llm_services/services/reliability/circuit_breaker.py`)
   - LLM API fault tolerance
   - **Reuse:** Wrap reunify_from_accepted_evidence LLM calls

**Patterns to Follow:**
1. **Service Layer Architecture** (docs/architecture/patterns.md):
   - Base → Core → Infrastructure → Reliability layers
   - **Apply:** ArtifactEnrichmentService.reunify_from_accepted_evidence in core layer

2. **Task Executor with Retries** (`llm_services/services/base/task_executor.py`):
   - Unified retry logic with exponential backoff
   - **Apply:** _execute_llm_task for re-unification calls

3. **TDD Workflow** (rules/06-tdd/policy.md):
   - Write failing tests → Implement → Refactor
   - **Apply:** All 23 new tests before implementation

**Code to Refactor:**
- `ArtifactUpload.tsx` - Extend to 6 steps (Steps 5 & 6 added)
- `llm_services/models.py` - Remove ExtractedContent model (ADR-047)
- `artifact_enrichment_service.py` - Add reunify_from_accepted_evidence method
- 32 files with ExtractedContent references - Clean up in Stage F

### Dependency & Side Effect Mapping

**Dependencies:**

1. **Backend Services:**
   - `ArtifactEnrichmentService` - Add reunify_from_accepted_evidence method
   - `EvidenceContentExtractor` - Already creates EnhancedEvidence
   - `CircuitBreaker` - Fault tolerance for LLM calls
   - `ModelSelector` - GPT-5 selection for re-unification

2. **Frontend Components:**
   - `WizardFlow` (ft-022) - Container for 6-step wizard
   - `ConfidenceBadge` - Reuse for confidence display
   - `LoadingOverlay` - Reuse for Step 5 processing

3. **Database Models:**
   - `EnhancedEvidence` - Use existing accepted/accepted_at fields
   - `Artifact` - Update unified_description/enriched_technologies/enriched_achievements

**Side Effects:**

1. **Database Writes:**
   - EnhancedEvidence updates (processed_content, accepted, accepted_at)
   - Artifact updates (unified_description, enriched_technologies, enriched_achievements, processing_confidence)
   - No new tables (using existing EnhancedEvidence.accepted field)

2. **LLM API Calls:**
   - One additional GPT-5 call per artifact finalization (~$0.01-0.03)
   - Re-unification call after user accepts all evidence
   - Circuit breaker tracks failures

3. **Frontend State:**
   - Wizard state extends to 6 steps
   - Evidence acceptance state tracked in useEvidenceReview hook
   - Polling state for enrichment_status in Step 5

**Impact Radius:**

1. **Frontend:**
   - **High Impact:** ArtifactUpload wizard (extend to 6 steps)
   - **Medium Impact:** Wizard step indicators (update to show Steps 5 & 6)
   - **Low Impact:** Artifact detail page (no changes needed)
   - **Isolated:** New components (ProcessingStep, EvidenceReviewStep, EvidenceCard)

2. **Backend:**
   - **High Impact:** Artifact upload flow (add finalize-evidence-review endpoint)
   - **Medium Impact:** EnhancedEvidence serialization (expose accepted field)
   - **Low Impact:** Existing artifact endpoints (no breaking changes)
   - **Isolated:** New service method (reunify_from_accepted_evidence)

3. **Database:**
   - **Zero Impact:** No schema changes (EnhancedEvidence.accepted already exists)
   - **Migration Needed:** Remove ExtractedContent table (ADR-047)

**Risk Areas:**

1. **HIGH RISK: LLM Re-unification Failures**
   - If reunify_from_accepted_evidence fails, user cannot finalize artifact
   - **Mitigation:** Fallback to concatenation, retry with exponential backoff, circuit breaker

2. **MEDIUM RISK: Wizard Abandonment at Step 6**
   - Users might abandon wizard during review (long blocking step)
   - **Mitigation:** Progress counter, clear messaging, save draft option (future)

3. **MEDIUM RISK: Mobile Editing UX**
   - Inline editing on small screens might be difficult
   - **Mitigation:** Touch-friendly inputs, responsive design, device testing

4. **LOW RISK: ExtractedContent Migration**
   - Removing ExtractedContent might break references
   - **Mitigation:** Comprehensive grep search, phased cleanup, test coverage

---

## Architecture Conformance

**Layer Assignment:**

1. **Service Layer (Backend):**
   - `backend/llm_services/services/core/artifact_enrichment_service.py`
   - New method: `reunify_from_accepted_evidence(artifact_id, user_id) -> Dict`
   - Layer: **Core** (business logic for evidence unification)

2. **API Layer (Backend):**
   - `backend/artifacts/views.py` - ArtifactViewSet
   - New endpoints: finalize_evidence_review, accept_evidence, reject_evidence, edit_evidence_content, get_evidence_acceptance_status
   - Layer: **Interface** (HTTP API for frontend)

3. **Component Layer (Frontend):**
   - `frontend/src/components/wizard/ProcessingStep.tsx` (new)
   - `frontend/src/components/wizard/EvidenceReviewStep.tsx` (new)
   - `frontend/src/components/wizard/EvidenceCard.tsx` (new)
   - Layer: **Presentation** (UI components)

4. **Hook Layer (Frontend):**
   - `frontend/src/hooks/useEvidenceReview.ts` (new)
   - Layer: **State Management** (evidence acceptance state)

**Pattern Compliance:**

✅ **Service Layer Pattern:**
- Follows llm_services architecture (base → core → infrastructure → reliability)
- reunify_from_accepted_evidence in core layer (business logic)
- Uses _execute_llm_task from base layer (unified retry logic)
- Uses CircuitBreaker from reliability layer (fault tolerance)

✅ **Wizard Pattern (ADR-032):**
- Full-page wizard with blocking steps
- WizardFlow container with step indicators
- useWizardProgress hook for state tracking
- CancelConfirmationDialog for unsaved changes

✅ **TDD Workflow (rules/06-tdd/policy.md):**
- Write failing tests (Stage F)
- Implement code (Stage G)
- Refactor (Stage H)
- 23 new tests + 103 updated tests

✅ **API Design (spec-api v4.9.0):**
- RESTful endpoints with clear resource names
- Consistent error responses (400, 403, 500)
- Idempotent operations (accept/reject)

**Dependencies:**

1. **Backend:**
   - `llm_services.services.base.BaseLLMService` (inheritance)
   - `llm_services.services.reliability.CircuitBreaker` (composition)
   - `llm_services.services.base.TaskExecutor` (retry logic)
   - `artifacts.models.Artifact` (update artifact fields)
   - `llm_services.models.EnhancedEvidence` (read/write evidence)

2. **Frontend:**
   - `@radix-ui/react-tabs` (tabbed evidence content display)
   - `react-hook-form` (inline editing forms)
   - `zod` (content validation schemas)
   - `axios` (API client for evidence endpoints)

---

## Acceptance Criteria

### Functional Requirements

**Evidence Processing (Step 5):**
- [ ] Wizard automatically submits artifact after Step 4 (Evidence)
- [ ] Step 5 displays blocking LoadingOverlay with message: "Extracting content from your evidence sources..."
- [ ] Step 5 polls GET /api/v1/artifacts/{id}/ every 3 seconds for enrichment_status
- [ ] Step 5 unblocks when enrichment_status === 'completed'
- [ ] Step 5 auto-advances to Step 6 (Evidence Review)
- [ ] Step 5 shows error message if enrichment_status === 'failed'
- [ ] **Performance SLO:** Unblock within 30 seconds for 95% of artifacts (3 evidence sources)

**Evidence Review (Step 6):**
- [ ] Step 6 fetches all EnhancedEvidence for artifact
- [ ] Each evidence displayed in EvidenceCard with ConfidenceBadge
- [ ] ConfidenceBadge shows green (≥80%), yellow (50-80%), or red (<50%) based on processing_confidence
- [ ] User can edit summary (textarea), technologies (tag list), achievements (list items)
- [ ] Edits auto-save on blur via PATCH /api/v1/artifacts/{id}/evidence/{id}/content/
- [ ] User can accept evidence via POST /api/v1/artifacts/{id}/evidence/{id}/accept/
- [ ] User can reject evidence via POST /api/v1/artifacts/{id}/evidence/{id}/reject/
- [ ] Progress counter shows "X/Y accepted" (e.g., "2/3 accepted")
- [ ] Finalize button disabled when not all evidence accepted (any pending or rejected)
- [ ] Finalize button enabled when ALL evidence accepted (100% acceptance)
- [ ] Finalize button calls POST /api/v1/artifacts/{id}/finalize-evidence-review/
- [ ] Backend re-unifies artifact from accepted evidence via reunify_from_accepted_evidence()
- [ ] Backend returns updated artifact with unified_description, enriched_technologies, enriched_achievements
- [ ] **Performance SLO:** Evidence edit auto-save ≤2 seconds
- [ ] **Performance SLO:** Evidence accept/reject ≤1 second
- [ ] **Performance SLO:** Finalize re-unification ≤5 seconds

**Data Quality:**
- [ ] Only accepted evidence (accepted=True) used in re-unification
- [ ] Rejected evidence (accepted=False) excluded from artifact content
- [ ] User edits to processed_content preserved in unified_description
- [ ] User-provided user_context preserved exactly (numbers, metrics, team sizes)
- [ ] Technologies deduplicated (e.g., "React, React" → "React")
- [ ] Achievements aggregated from all accepted evidence
- [ ] Processing confidence recalculated after re-unification

**Error Handling:**
- [ ] 403 Forbidden if not all evidence accepted → Show toast: "Please accept all evidence before finalizing"
- [ ] 400 Bad Request if edited content invalid → Show inline error on field
- [ ] 500 Server Error if LLM re-unification fails → Show retry option with error message
- [ ] Network errors during auto-save → Show warning, retry on next edit
- [ ] Timeout during Step 5 processing (>60s) → Show error message with support link

### Non-Functional Requirements

**Performance:**
- [ ] Step 5 unblocks in <30 seconds (95th percentile)
- [ ] Evidence edit auto-save in <2 seconds
- [ ] Evidence accept/reject in <1 second
- [ ] Finalize re-unification in <5 seconds
- [ ] Mobile wizard loading <3 seconds (4G connection)

**Accessibility (WCAG 2.1 AA):**
- [ ] Keyboard navigation (Tab, Enter, Esc)
- [ ] Screen reader support (ARIA labels, live regions)
- [ ] High color contrast (4.5:1 for text)
- [ ] Focus indicators visible
- [ ] Form validation messages announced

**Mobile UX:**
- [ ] Touch-friendly buttons (min 44px height)
- [ ] Responsive layout at all breakpoints (320px+)
- [ ] Inline editing works on mobile keyboards
- [ ] No horizontal scroll
- [ ] Confidence badges legible on small screens

**Browser Support:**
- [ ] Chrome/Edge (last 2 versions)
- [ ] Firefox (last 2 versions)
- [ ] Safari (last 2 versions)
- [ ] Mobile Safari (iOS 14+)
- [ ] Mobile Chrome (Android 10+)

---

## Design Changes

### API Changes (spec-api v4.9.0)

**New Endpoints:**

1. **Finalize Evidence Review**
```
POST /api/v1/artifacts/{artifact_id}/finalize-evidence-review/

Request: {}

Response: 200 OK
{
  "artifact_id": 123,
  "unified_description": "Led a cross-functional team of 5...",
  "enriched_technologies": ["React", "Django", "PostgreSQL"],
  "enriched_achievements": ["Improved performance by 40%", ...],
  "processing_confidence": 0.92,
  "evidence_acceptance_summary": {
    "total_evidence": 3,
    "accepted": 3,
    "rejected": 0,
    "pending": 0,
    "can_finalize": true
  }
}

Errors:
- 403 Forbidden: Not all evidence accepted
- 500 Internal Server Error: LLM re-unification failed
```

2. **Edit Evidence Content**
```
PATCH /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/content/

Request:
{
  "processed_content": {
    "summary": "User-edited summary...",
    "technologies": ["React", "TypeScript"],
    "achievements": ["Led team of 5", "Improved performance by 40%"]
  }
}

Response: 200 OK
{
  "id": 456,
  "processed_content": { ... },
  "processing_confidence": 0.85,
  "updated_at": "2025-01-06T10:30:00Z"
}

Errors:
- 400 Bad Request: Invalid content structure
```

3. **Accept Evidence**
```
POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/accept/

Request:
{
  "review_notes": "Optional notes" // optional
}

Response: 200 OK
{
  "id": 456,
  "accepted": true,
  "accepted_at": "2025-01-06T10:30:00Z",
  "review_notes": "Optional notes"
}
```

4. **Reject Evidence**
```
POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/reject/

Request: {}

Response: 200 OK
{
  "id": 456,
  "accepted": false,
  "accepted_at": null
}
```

5. **Get Evidence Acceptance Status**
```
GET /api/v1/artifacts/{artifact_id}/evidence-acceptance-status/

Response: 200 OK
{
  "can_finalize": false,
  "total_evidence": 3,
  "accepted": 2,
  "rejected": 0,
  "pending": 1,
  "evidence_details": [
    {
      "id": 456,
      "title": "my-awesome-project",
      "accepted": true,
      "accepted_at": "2025-01-06T10:30:00Z"
    },
    ...
  ]
}
```

### Artifact Status Transitions

**Status Values (Artifact Model):**

```python
# backend/artifacts/models.py
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('processing', 'Processing Evidence'),           # Phase 1: Per-source extraction
    ('review_pending', 'Evidence Review Pending'),   # Extraction complete, awaiting user review
    ('reunifying', 'Reunifying Evidence'),           # Phase 2: LLM reunification in progress
    ('review_finalized', 'Review Finalized'),        # Reunification complete, awaiting user acceptance
    ('complete', 'Complete'),                        # User accepted artifact
    ('abandoned', 'Abandoned'),                      # Inactive >24h or user-abandoned
]
```

**Valid Transitions:**
```
draft → processing (when enrichment task starts - trigger_artifact_enrichment endpoint)
processing → review_pending (when Phase 1 extraction completes successfully)
processing → draft (if Phase 1 extraction fails)
review_pending → reunifying (when user finalizes evidence review - finalize_evidence_review endpoint)
reunifying → review_finalized (when Phase 2 reunification succeeds)
reunifying → review_pending (if Phase 2 reunification fails)
review_finalized → complete (when user accepts artifact - accept_artifact endpoint)
review_finalized → reunifying (if user edits and re-triggers reunification)
{draft, processing, review_pending, review_finalized} → abandoned (if inactive >24h or user-initiated)
```

**Invalid Transitions:**
- `draft → reunifying` (must go through processing → review_pending)
- `processing → complete` (must go through review_pending → reunifying → review_finalized)
- `review_pending → complete` (must go through reunifying → review_finalized)
- `reunifying → complete` (must go through review_finalized)
- `complete → {any}` (terminal state)
- `abandoned → {any}` (terminal state)

**Race Condition Prevention:**

To prevent race conditions where frontend polls and sees stale status before async task updates it:
- `trigger_artifact_enrichment` sets `artifact.status='processing'` **BEFORE** triggering `enrich_artifact.delay()`
- `finalize_evidence_review` sets `artifact.status='reunifying'` **BEFORE** triggering `reunify_artifact_evidence.delay()`
- Both endpoints use `@transaction.atomic` decorator for atomic status updates

**Wizard Step Mapping (6-step consolidated):**
- Step 1-4: `status='draft'`, `last_wizard_step=1-4` (Basic Info → Your Context → Evidence → Confirm Details)
- Step 5 (Consolidated Processing + Review):
  - Phase 1: `status='processing'`, `last_wizard_step=5` (Auto-show spinner: "Extracting content...")
  - Phase 2: `status='review_pending'`, `last_wizard_step=5` (Auto-transition to evidence review UI)
  - User reviews individual evidence items with inline editing
- Step 6 (Consolidated Reunification + Acceptance):
  - Phase 1: `status='reunifying'`, `last_wizard_step=6` (Auto-show spinner: "Finalizing your artifact...")
  - Phase 2: `status='review_finalized'`, `last_wizard_step=6` (Auto-transition to acceptance UI)
  - User reviews final artifact (unified_description, enriched_technologies, enriched_achievements)
  - Click "Accept Artifact" → Navigate to detail page
- Complete: `status='complete'`, `last_wizard_step=6`, `wizard_completed_at` set

---

### Re-Enrichment Workflows (ft-046)

After initial artifact creation, users may want to re-enrich artifacts when:
- They add new evidence sources (GitHub repos, PDFs, etc.)
- They want to refresh enriched content without modifying evidence
- They discover errors in enriched content and want AI to regenerate

**Two Re-Enrichment Options** (via dropdown button on artifact detail page):

#### Option 1: Re-enrich Evidence (Full Refresh)
**Entry Point**: Detail page → "Re-enrich Evidence" → Wizard Step 3 (Evidence)
**Use Case**: User added new GitHub links or uploaded new files

**Flow:**
```
Artifact Detail Page (status='complete')
  ↓
User clicks "Re-enrich Evidence" dropdown option
  ↓
Navigate to /upload-artifact?artifactId={id}&startStep=3
  ↓
Wizard loads in "resume mode":
  - Pre-populates form data from existing artifact
  - Shows Step 3 (Evidence List) with existing evidence
  - User can add/remove/edit evidence sources
  ↓
Step 4: Confirm Details
  - User confirms changes
  - Artifact status → 'processing'
  - Trigger enrich_artifact Celery task
  ↓
Step 5: Consolidated Processing + Evidence Review
  - Phase 1 (Auto): Processing spinner "Extracting content..." (polls every 10s)
  - Phase 2 (Auto-transition): Evidence review UI when status='review_pending'
  - User reviews ALL evidence (including new items) with inline editing
  - Must accept 100% to proceed
  - User clicks "Finalize & Continue"
  ↓
Step 6: Consolidated Reunification + Acceptance
  - Phase 1 (Auto): "Finalizing..." spinner (polls every 3s)
  - Phase 2 (Auto-transition): Acceptance UI when status='review_finalized'
  - User reviews final artifact (unified_description, enriched_technologies, enriched_achievements)
  - User clicks "Accept Artifact"
  - Artifact status → 'complete'
  - Navigate to /artifacts/{id}
  ↓
Artifact Detail Page (accepted artifact)
```

**Status Transitions:**
```
complete → processing (on submit Step 4)
processing → review_pending (Phase 1 complete)
review_pending → reunifying (on finalize Step 5)
reunifying → review_finalized (Phase 2 complete)
review_finalized → complete (user accepts Step 6)
```

**API Calls:**
```
GET /api/v1/artifacts/{id}/ (fetch artifact data for pre-population)
PATCH /api/v1/artifacts/{id}/ (update evidence sources if modified)
POST /api/v1/artifacts/{id}/trigger-enrichment/ (start Phase 1)
POST /api/v1/artifacts/{id}/finalize-evidence-review/ (start Phase 2)
POST /api/v1/artifacts/{id}/accept-artifact/ (accept final artifact, set status='complete')
```

---

#### Option 2: Re-enrich Artifact (Fast Content Refresh)
**Entry Point**: Detail page → "Re-enrich Artifact" → Wizard Step 5 (Evidence Review)
**Use Case**: Evidence sources unchanged, user wants fresh enriched content

**Flow:**
```
Artifact Detail Page (status='complete')
  ↓
User clicks "Re-enrich Artifact" dropdown option
  ↓
Navigate to /upload-artifact?artifactId={id}&startStep=5
  ↓
Wizard loads in "resume mode":
  - Skips Steps 1-4 (evidence unchanged)
  - Jumps directly to Step 5 Phase 2 (Evidence Review)
  - Shows existing EnhancedEvidence records (from previous enrichment)
  ↓
Step 5 Phase 2: Evidence Review
  - User reviews existing evidence content
  - Can edit summaries/technologies/achievements inline
  - Must accept 100% to proceed
  - User clicks "Finalize & Continue"
  ↓
Step 6: Consolidated Reunification + Acceptance
  - Phase 1 (Auto): "Finalizing..." spinner
    - Artifact status → 'reunifying'
    - LLM re-unifies from user-edited evidence
    - Poll artifact.status every 3s
  - Phase 2 (Auto-transition): Acceptance UI when status='review_finalized'
    - User reviews final artifact content (unified_description, enriched_technologies, enriched_achievements)
    - User clicks "Accept Artifact"
  - Artifact status → 'complete'
  - Navigate to /artifacts/{id}
  ↓
Artifact Detail Page (accepted artifact)
```

**Status Transitions:**
```
complete → reunifying (on finalize Step 5, skipping processing phase)
reunifying → review_finalized (Phase 2 complete)
review_finalized → complete (user accepts Step 6)
```

**Note:** This flow bypasses Phase 1 extraction entirely since evidence sources haven't changed. It only triggers Phase 2 reunification from existing EnhancedEvidence records.

**API Calls:**
```
GET /api/v1/artifacts/{id}/ (fetch artifact data)
GET /api/v1/artifacts/{id}/evidence/ (fetch existing evidence)
POST /api/v1/artifacts/{id}/finalize-evidence-review/ (start Phase 2 reunification)
POST /api/v1/artifacts/{id}/accept-artifact/ (accept final artifact, set status='complete')
```

---

#### Wizard Resume Mode Implementation

**URL Parameters:**
- `?artifactId={id}` - Artifact to edit (triggers resume mode)
- `&startStep={4|7}` - Step to jump to (4 for full re-enrich, 7 for fast refresh)

**Frontend Wizard Behavior:**
```typescript
// ArtifactUpload.tsx
const [searchParams] = useSearchParams()
const resumeArtifactId = searchParams.get('artifactId')
const startStep = searchParams.get('startStep')

if (resumeArtifactId && startStep) {
  // Resume mode:
  // 1. Fetch artifact via apiClient.getArtifact()
  // 2. Pre-populate form state with artifact data
  // 3. Set currentStep = parseInt(startStep)
  // 4. Show wizard from specified step
  // 5. On submit, PATCH existing artifact (not create new)
}
```

**Backend Handling:**
- Existing endpoints already support PATCH operations
- No new endpoints needed for re-enrichment
- `trigger_artifact_enrichment` can be called multiple times (idempotent)
- `finalize_evidence_review` uses EnhancedEvidence.accepted records (same logic)

---

#### Re-Enrichment vs. Inline Editing

| Action | Method | Use Case | Speed |
|--------|--------|----------|-------|
| **Inline Edit** (Detail Page) | PATCH enriched fields directly | Minor tweaks to enriched description/technologies | Instant |
| **Re-enrich Artifact** (Step 5) | LLM re-unification from edited evidence | Refresh AI-generated content from evidence | 30-45s |
| **Re-enrich Evidence** (Step 3) | Full Phase 1 + Phase 2 pipeline | New evidence sources added | 60-90s |

**Recommendation**: Users should prefer inline editing for small changes, re-enrichment for substantial updates.

---

### Frontend Changes (spec-frontend v3.0.0)

**New Components:**

1. **ProcessingStep.tsx**
```tsx
interface ProcessingStepProps {
  artifactId: string
  onProcessingComplete: () => void
  onError: (error: string) => void
}

// Displays LoadingOverlay, polls enrichment_status every 3s
// Calls onProcessingComplete when status === 'completed'
```

2. **EvidenceReviewStep.tsx**
```tsx
interface EvidenceReviewStepProps {
  artifactId: string
  onFinalize: () => void
  onBack: () => void
}

// Displays all evidence cards with inline editing
// Tracks acceptance progress (X/Y accepted)
// Enables/disables finalize button based on 100% acceptance
```

3. **EvidenceCard.tsx**
```tsx
interface EvidenceCardProps {
  evidence: EnhancedEvidenceResponse
  onAccept: (evidenceId: number, reviewNotes?: string) => Promise<void>
  onReject: (evidenceId: number) => Promise<void>
  onEdit: (evidenceId: number, content: ProcessedContent) => Promise<void>
  isEditing: boolean
  onToggleEdit: () => void
}

// Displays evidence content with ConfidenceBadge
// Inline editing for summary, technologies, achievements
// Accept/reject actions
```

**New Hook:**

```tsx
// useEvidenceReview.ts
interface UseEvidenceReviewReturn {
  evidence: EnhancedEvidenceResponse[]
  acceptanceStatus: AcceptanceStatus
  isLoading: boolean
  error: string | null
  acceptEvidence: (evidenceId: number, reviewNotes?: string) => Promise<void>
  rejectEvidence: (evidenceId: number) => Promise<void>
  editEvidenceContent: (evidenceId: number, content: ProcessedContent) => Promise<void>
  finalizeReview: () => Promise<void>
  refetch: () => Promise<void>
}
```

**Updated Component:**

```tsx
// ArtifactUpload.tsx - Extend to 6 steps
const WIZARD_STEPS = [
  { id: 1, title: 'Basic Info', component: BasicInfoStep },
  { id: 2, title: 'Your Context', component: UserContextStep },
  { id: 3, title: 'Technologies', component: TechnologiesStep },
  { id: 4, title: 'Evidence', component: EvidenceStep },
  { id: 5, title: 'Processing', component: ProcessingStep }, // NEW
  { id: 6, title: 'Review Evidence', component: EvidenceReviewStep }, // NEW
]
```

### Backend Changes (spec-llm v4.3.0)

**New Service Method:**

```python
# backend/llm_services/services/core/artifact_enrichment_service.py

class ArtifactEnrichmentService(BaseLLMService):

    async def reunify_from_accepted_evidence(
        self,
        artifact_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Re-unify artifact content from user-accepted and edited evidence.

        Reads from EnhancedEvidence.processed_content (user-edited) instead of
        ExtractedContent, uses LLM to generate professional narrative, updates
        Artifact fields with unified content.

        Args:
            artifact_id: Artifact ID to re-unify
            user_id: User ID for tracking

        Returns:
            {
                'artifact_id': int,
                'unified_description': str,
                'enriched_technologies': List[str],
                'enriched_achievements': List[str],
                'processing_confidence': float,
                'evidence_acceptance_summary': AcceptanceStatus
            }

        Raises:
            LLMError: If re-unification fails (fallback to concatenation)
        """
```

---

## Test & Eval Plan

### Unit Tests (15 backend + 8 frontend = 23 tests)

**Backend Unit Tests:**

| Test | File | Description | Coverage Target |
|------|------|-------------|----------------|
| test_accept_evidence | test_artifact_views.py | Accept evidence sets accepted=True, accepted_at | 100% |
| test_reject_evidence | test_artifact_views.py | Reject evidence sets accepted=False | 100% |
| test_edit_evidence_content | test_artifact_views.py | PATCH updates processed_content | 100% |
| test_get_acceptance_status | test_artifact_views.py | Returns accurate acceptance summary | 100% |
| test_finalize_success | test_artifact_views.py | Finalize when 100% accepted | 100% |
| test_finalize_partial_403 | test_artifact_views.py | 403 when not all accepted | 100% |
| test_reunify_from_accepted | test_artifact_enrichment_service.py | LLM re-unification from EnhancedEvidence | 100% |
| test_reunify_user_context | test_artifact_enrichment_service.py | User context preserved in prompt | 100% |
| test_reunify_excluded_rejected | test_artifact_enrichment_service.py | Rejected evidence not used | 100% |
| test_reunify_confidence | test_artifact_enrichment_service.py | Confidence = avg + 0.1 bonus | 100% |
| test_reunify_technologies | test_artifact_enrichment_service.py | Technologies deduplicated | 100% |
| test_reunify_achievements | test_artifact_enrichment_service.py | Achievements aggregated | 100% |
| test_reunify_llm_failure | test_artifact_enrichment_service.py | Fallback to concatenation | 100% |
| test_edit_validation | test_artifact_views.py | Invalid content rejected (400) | 100% |
| test_acceptance_calculation | test_artifact_views.py | can_finalize logic correct | 100% |

**Frontend Unit Tests:**

| Test | File | Description | Coverage Target |
|------|------|-------------|----------------|
| test_processing_step_polling | ProcessingStep.test.tsx | Polls every 3s, stops on completion | 100% |
| test_processing_step_advance | ProcessingStep.test.tsx | Calls onComplete when status=completed | 100% |
| test_evidence_review_rendering | EvidenceReviewStep.test.tsx | Renders all evidence cards | 100% |
| test_evidence_card_editing | EvidenceCard.test.tsx | Inline editing updates state | 100% |
| test_evidence_accept | EvidenceCard.test.tsx | Accept button calls API | 100% |
| test_evidence_reject | EvidenceCard.test.tsx | Reject button calls API | 100% |
| test_finalize_disabled | EvidenceReviewStep.test.tsx | Disabled when pending exists | 100% |
| test_finalize_redirect | EvidenceReviewStep.test.tsx | Navigates on success | 100% |

### Integration Tests (8 tests)

| Test | Description | Layers Tested |
|------|-------------|---------------|
| test_full_wizard_flow | Steps 1-6 end-to-end with real API | Frontend + Backend + Database |
| test_edit_propagates | User edit → finalize → verify artifact | Frontend + Backend + LLM + Database |
| test_rejected_excluded | Rejected evidence not in description | Backend + LLM |
| test_acceptance_updates | Real-time status tracking | Frontend + Backend |
| test_finalize_llm | LLM re-unification integration | Backend + LLM API |
| test_frontend_backend_flow | Full stack API integration | Frontend + Backend |
| test_mobile_editing_ux | Touch-friendly on mobile (Playwright) | Frontend (mobile viewport) |
| test_llm_failure_fallback | Graceful degradation on LLM error | Backend + LLM + Error handling |

### AI Evaluation (LLM Quality)

**Goal:** Verify reunify_from_accepted_evidence produces professional CV-quality output

**Test Cases (Golden Examples):**

1. **User Context Integration:**
   - Input: user_context with specific numbers ("team of 5", "40% improvement")
   - Expected: Output preserves exact numbers
   - Threshold: 100% fact preservation

2. **Technology Deduplication:**
   - Input: Multiple evidence with overlapping technologies ("React", "React", "TypeScript")
   - Expected: Output lists "React, TypeScript" (no duplicates)
   - Threshold: 100% deduplication

3. **Achievement Aggregation:**
   - Input: 3 evidence sources with 5 achievements each
   - Expected: Output combines into cohesive narrative (not bullet list)
   - Threshold: Perplexity <50, BLEU >0.7 (professional quality)

4. **Rejected Evidence Exclusion:**
   - Input: 3 evidence, 1 rejected
   - Expected: Output only mentions accepted evidence topics
   - Threshold: 0% rejected content in output

**Automated Tests:**
```python
# backend/llm_services/tests/eval/test_reunification_quality.py

def test_user_context_fact_preservation():
    """Verify exact numbers/metrics preserved"""
    user_context = "Led team of 5 engineers. Improved performance by 40%."
    result = await service.reunify_from_accepted_evidence(artifact_id)
    assert "team of 5" in result['unified_description']
    assert "40%" in result['unified_description']

def test_technology_deduplication():
    """Verify no duplicate technologies"""
    # Setup: 3 evidence with ["React", "React", "TypeScript"]
    result = await service.reunify_from_accepted_evidence(artifact_id)
    tech_counts = Counter(result['enriched_technologies'])
    assert all(count == 1 for count in tech_counts.values())
```

### Performance Testing

**Load Tests:**
- 100 concurrent finalize-evidence-review requests
- Target: p95 latency <5 seconds, p99 <10 seconds
- Failure threshold: >10% requests exceed 10 seconds

**LLM Cost Monitoring:**
- Track GPT-5 token usage per re-unification
- Target: <3000 tokens per artifact (~$0.03)
- Alert if daily cost >$10

---

## Telemetry & Metrics

### Application Metrics (CloudWatch)

**Key Metrics:**
1. **evidence_acceptance_rate** (target: 100%)
   - Percentage of artifacts with all evidence accepted
   - Alert if <95% (indicates workflow issues)

2. **evidence_edit_rate** (target: 40-60%)
   - Percentage of evidence edited by users
   - Validates need for review (too low = wasted time, too high = poor extraction)

3. **average_review_time_per_evidence** (target: ≤3 minutes)
   - Time spent reviewing each evidence item
   - Alert if >5 minutes (UX too complex)

4. **reunification_success_rate** (target: ≥95%)
   - Percentage of successful LLM re-unifications
   - Alert if <90% (LLM reliability issues)

5. **step5_processing_time_p95** (target: <30 seconds)
   - 95th percentile processing time for evidence extraction
   - Alert if >60 seconds (performance degradation)

6. **wizard_abandonment_rate_step6** (target: <10%)
   - Percentage of users abandoning wizard at Step 6
   - Alert if >15% (review too burdensome)

### Analytics Events (User Tracking)

**Events to Track:**
```javascript
// Evidence review started
analytics.track('evidence_review_started', {
  artifact_id: 123,
  evidence_count: 3,
  user_id: 456
})

// Evidence accepted
analytics.track('evidence_accepted', {
  artifact_id: 123,
  evidence_id: 789,
  confidence: 0.85,
  edited: true // was content edited before acceptance?
})

// Evidence rejected
analytics.track('evidence_rejected', {
  artifact_id: 123,
  evidence_id: 789,
  confidence: 0.45,
  rejection_reason: 'incorrect_technologies' // optional
})

// Evidence edited
analytics.track('evidence_edited', {
  artifact_id: 123,
  evidence_id: 789,
  field_edited: 'technologies', // summary | technologies | achievements
  edit_type: 'add_item' // add_item | remove_item | modify_text
})

// Artifact finalization triggered
analytics.track('artifact_reunification_triggered', {
  artifact_id: 123,
  accepted_evidence_count: 3,
  total_edits: 5
})

// Reunification completed
analytics.track('artifact_reunification_completed', {
  artifact_id: 123,
  duration_ms: 4200,
  llm_tokens_used: 2500,
  processing_confidence: 0.92
})

// Wizard abandoned
analytics.track('wizard_abandoned', {
  artifact_id: 123,
  step: 6,
  acceptance_progress: '2/3'
})
```

### Dashboards

**Evidence Review Quality Dashboard:**
- Evidence acceptance rate (last 7 days)
- Evidence edit rate by field (summary, technologies, achievements)
- Average review time per evidence (trend)
- Wizard abandonment funnel (Step 1 → 6)

**LLM Performance Dashboard:**
- Re-unification success rate
- LLM cost per artifact (daily trend)
- LLM latency p50/p95/p99
- Circuit breaker state (open/closed)

**User Experience Dashboard:**
- Step 5 processing time (histogram)
- Step 6 completion time (histogram)
- Evidence confidence distribution (red/yellow/green)
- Mobile vs. Desktop review time comparison

### Alerts

**Critical Alerts (PagerDuty):**
- Reunification success rate <80% (5 minutes)
- Step 5 processing time p95 >60 seconds (5 minutes)
- Evidence acceptance rate <80% (30 minutes)

**Warning Alerts (Slack):**
- Wizard abandonment rate Step 6 >15% (1 hour)
- Daily LLM cost >$10 (daily digest)
- Evidence edit rate <20% or >80% (1 hour)

---

## Edge Cases & Risks

### Edge Cases

**1. All Evidence Rejected**
- **Scenario:** User rejects all evidence (0% acceptance)
- **Behavior:** Finalize button remains disabled, user cannot proceed
- **Alternative:** Show helper text: "At least one evidence source must be accepted. You can also delete this artifact if the evidence is completely incorrect."

**2. Zero Evidence Sources**
- **Scenario:** User uploads artifact with no evidence (GitHub links, PDFs)
- **Behavior:** Skip Steps 5 & 6 entirely, go directly to artifact detail page
- **Alternative:** Show warning in Step 4 (Confirm Details): "No evidence sources added. Your artifact will use only the basic info and user context."

**3. Very Long Summaries (>5000 chars)**
- **Scenario:** User edits summary to extremely long text
- **Behavior:** Warn user when exceeding 1000 chars, hard limit at 2000 chars
- **Alternative:** Show character counter, disable save button if >2000 chars

**4. LLM Re-unification Timeout (>30s)**
- **Scenario:** GPT-5 takes >30 seconds to respond
- **Behavior:** Show progress spinner, retry once, fallback to concatenation after 2 failures
- **Alternative:** Queue re-unification as background task, notify user when complete

**5. Network Failure During Auto-Save**
- **Scenario:** User edits content, blurs field, network drops before save completes
- **Behavior:** Show warning icon on field, retry on next edit, persist draft locally
- **Alternative:** Show toast: "Failed to save changes. Retrying..."

**6. Simultaneous Edits from Multiple Tabs**
- **Scenario:** User opens wizard in two tabs, edits same evidence in both
- **Behavior:** Last write wins, show conflict warning if timestamps differ
- **Alternative:** Lock artifact for editing (single-session enforcement)

**7. Mobile Keyboard Overlap**
- **Scenario:** Mobile keyboard covers save/cancel buttons when editing
- **Behavior:** Scroll form to keep buttons visible, add "Done" button on keyboard toolbar
- **Alternative:** Dismiss keyboard on scroll, show floating save button

**8. Very Low Confidence Evidence (<30%)**
- **Scenario:** Evidence extraction quality extremely poor
- **Behavior:** Show red badge with warning: "This content may be inaccurate. Please review carefully."
- **Alternative:** Auto-suggest deletion option: "This evidence has very low confidence. Delete instead?"

### Risk Assessment

**HIGH RISK: LLM Cost Overruns**
- **Scenario:** Many users finalize artifacts multiple times (re-unification costs add up)
- **Impact:** API costs exceed budget ($100/month → $500/month)
- **Mitigation:**
  - Cache re-unification results (if evidence unchanged, return cached)
  - Rate limit re-unifications (max 3 per hour per user)
  - Monitor daily costs, implement circuit breaker at $20/day

**MEDIUM RISK: Wizard Abandonment Spike**
- **Scenario:** Users find Step 6 too burdensome, abandon wizard at 50% rate
- **Impact:** Poor UX, feature adoption fails
- **Mitigation:**
  - A/B test: Optional review (with warnings) vs. mandatory review
  - Add "Save Draft" option (resume later)
  - Reduce review depth (e.g., only review low-confidence evidence)

**MEDIUM RISK: Mobile UX Issues**
- **Scenario:** Inline editing difficult on small screens, high error rates
- **Impact:** Mobile users cannot complete review, abandon wizard
- **Mitigation:**
  - Device testing (iOS/Android) before launch
  - Touch-friendly inputs (larger buttons, spacing)
  - Alternative: Full-screen edit mode for mobile

**LOW RISK: Data Loss During Finalization**
- **Scenario:** Re-unification fails after user spent 5 minutes reviewing
- **Impact:** User frustration, lost work
- **Mitigation:**
  - Transactional updates (rollback on failure)
  - Persist accepted state before re-unification
  - Retry option with same acceptance state

**LOW RISK: ExtractedContent Migration Breaks Tests**
- **Scenario:** Removing ExtractedContent breaks 32 files, tests fail
- **Impact:** Delayed deployment, rollback needed
- **Mitigation:**
  - Phased cleanup (file by file)
  - Comprehensive test run after each cleanup
  - Database backup before migration

---

## Implementation Timeline

**Total Estimated Effort:** 28 hours (disco-001 analysis)

### Phase 1: Backend Infrastructure (Days 1-4, 14-18 hours)

**Day 1-2: Service Layer (6-8 hours)**
- [ ] Implement `reunify_from_accepted_evidence()` method
- [ ] Build evidence summaries from `processed_content`
- [ ] Call LLM with ft-018 prompt pattern (user context integration)
- [ ] Extract technologies and achievements
- [ ] Calculate reunification confidence
- [ ] Unit tests (7 tests: reunify success, user context, excluded rejected, confidence, tech, achievements, LLM failure)

**Day 3: API Endpoints (4-6 hours)**
- [ ] Implement `finalize_evidence_review` endpoint
- [ ] Implement `accept_evidence` endpoint
- [ ] Implement `reject_evidence` endpoint
- [ ] Implement `edit_evidence_content` endpoint
- [ ] Implement `get_evidence_acceptance_status` endpoint
- [ ] Unit tests (8 tests: accept, reject, edit, status, finalize success, finalize 403, edit validation, status calculation)

**Day 4: Error Handling & Fallbacks (2-3 hours)**
- [ ] LLM failure fallback (concatenation)
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker integration
- [ ] Error messages and logging

**Day 4: Migration (ADR-047) (2 hours)**
- [ ] Remove `GitHubRepositoryAnalysis.extracted_content` field
- [ ] Update `GitHubRepositoryAgent` to not create ExtractedContent
- [ ] Create migration to drop `extracted_content` table
- [ ] Database backup and verification

### Phase 2: Frontend Components (Days 5-7, 6-8 hours)

**Day 5: ProcessingStep Component (2 hours)**
- [ ] Create `ProcessingStep.tsx` component
- [ ] Implement enrichment_status polling (3s intervals)
- [ ] LoadingOverlay integration
- [ ] Auto-advance to Step 6 on completion
- [ ] Error handling (failed enrichment)
- [ ] Unit tests (2 tests: polling, advance)

**Day 6: EvidenceReviewStep & EvidenceCard (3-4 hours)**
- [ ] Create `EvidenceReviewStep.tsx` container
- [ ] Create `EvidenceCard.tsx` component
- [ ] Inline editing (summary textarea, tech tags, achievement list)
- [ ] Accept/reject actions
- [ ] ConfidenceBadge integration
- [ ] Progress counter (X/Y accepted)
- [ ] Finalize button state (disabled/enabled)
- [ ] Unit tests (4 tests: rendering, editing, accept, reject)

**Day 7: useEvidenceReview Hook & Integration (1-2 hours)**
- [ ] Create `useEvidenceReview.ts` hook
- [ ] State management (evidence list, acceptance status)
- [ ] API integration (all 5 endpoints)
- [ ] Error handling and loading states
- [ ] Unit tests (2 tests: finalize disabled, finalize redirect)

**Day 7: Wizard Integration (1 hour)**
- [ ] Update `ArtifactUpload.tsx` to 6 steps
- [ ] Add ProcessingStep and EvidenceReviewStep to wizard
- [ ] Update step indicators (show Steps 5 & 6)

### Phase 3: Testing & Polish (Days 8-10, 4.5-6 hours)

**Day 8: Integration Tests (2-3 hours)**
- [ ] Full wizard flow (Steps 1-6 end-to-end)
- [ ] User edit propagation (edit → finalize → verify artifact)
- [ ] Rejected evidence exclusion
- [ ] Acceptance status updates
- [ ] LLM re-unification integration
- [ ] Frontend-backend flow
- [ ] Mobile editing UX (Playwright)
- [ ] LLM failure fallback

**Day 9: Code Cleanup (1-2 hours)**
- [ ] Remove ExtractedContent imports (32 files)
- [ ] Update test factories
- [ ] Remove ExtractedContent from admin
- [ ] Documentation updates

**Day 10: Polish & Validation (1.5-2 hours)**
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Mobile responsive testing
- [ ] Performance optimization (caching, lazy loading)
- [ ] Final test run (all 23 new + 103 updated = 126 tests)

### Phase 4: Deployment (Day 11, 0.5 hours)

- [ ] Deploy backend to staging
- [ ] Deploy frontend to staging
- [ ] Smoke tests on staging
- [ ] Deploy to production
- [ ] Monitor metrics (acceptance rate, LLM costs, latency)

---

## Rollout Strategy

**Gradual Rollout (3 Phases):**

**Phase 1: Internal Testing (Week 1)**
- Deploy to staging environment
- Internal team testing (5-10 artifacts)
- Monitor: acceptance rate, edit rate, LLM costs, latency
- Fix critical issues

**Phase 2: Beta Users (Week 2)**
- Deploy to production with feature flag
- Enable for 10% of users (beta cohort)
- Monitor: wizard abandonment, evidence quality, support tickets
- Gather feedback via in-app survey

**Phase 3: Full Rollout (Week 3)**
- Enable for 100% of users
- Monitor: all metrics dashboard
- Alert on: acceptance rate <95%, LLM costs >$10/day
- Iterate based on feedback

---

## Success Metrics (from PRD v1.5.0)

**Quantitative:**
- [ ] Evidence acceptance rate: 100% (all evidence reviewed before finalization)
- [ ] Average review time per evidence: ≤3 minutes
- [ ] Evidence edit rate: 40-60% (users editing extracted content to improve accuracy)
- [ ] Re-unification success rate: ≥95%
- [ ] Wizard abandonment at Step 6: <10%
- [ ] Step 5 processing time p95: <30 seconds
- [ ] Finalize re-unification latency p95: <5 seconds

**Qualitative:**
- [ ] User feedback: "Evidence review caught errors before they reached my CV"
- [ ] Support tickets: Decrease in "incorrect CV content" complaints
- [ ] User trust: Increased confidence in AI-extracted content

---

## Rollback Plan

**If Critical Issues Detected:**

1. **Immediate Rollback (Minutes):**
   - Disable feature flag (revert to 4-step wizard)
   - Users bypass Steps 5 & 6 (skip to artifact detail page)
   - Evidence review skipped (use original unification)

2. **Database Rollback (Hours):**
   - Restore database from backup (if ExtractedContent migration breaks)
   - Revert migrations: `python manage.py migrate llm_services <previous_migration>`

3. **Code Rollback (Hours):**
   - Revert git commits: `git revert <commit_hash>`
   - Redeploy previous version

**Rollback Triggers:**
- Wizard abandonment rate >30% at Step 6
- Re-unification success rate <70%
- LLM costs >$50/day
- Critical bugs preventing artifact finalization

---

## Future Enhancements

**Post-Launch Iterations:**

1. **Save Draft (P1):**
   - Allow users to save wizard progress and resume later
   - Store evidence acceptance state in database
   - Resume wizard from Step 6 with saved state

2. **Async Re-unification (P2):**
   - Queue re-unification as background Celery task
   - Return immediately to artifact detail page
   - Notify user when re-unification completes

3. **Selective Review (P2):**
   - Only require review of low-confidence evidence (<70%)
   - Auto-accept high-confidence evidence (≥90%)
   - Reduces review burden for high-quality extractions

4. **Evidence History (P3):**
   - Track evidence edit history (audit trail)
   - Show diffs between original and user-edited content
   - Allow rollback to previous versions

5. **Batch Operations (P3):**
   - "Accept All" button (with confirmation dialog)
   - "Reject All Low Confidence" (<50%)
   - "Edit Multiple" mode (select multiple evidence, bulk edit)

---

## References

- **PRD:** `docs/prds/prd.md` (v1.5.0)
- **Discovery:** `docs/discovery/disco-001-evidence-review-workflow.md`
- **TECH SPECs:**
  - `docs/specs/spec-frontend.md` (v3.0.0)
  - `docs/specs/spec-api.md` (v4.9.0)
  - `docs/specs/spec-llm.md` (v4.3.0)
- **ADRs:**
  - ADR-046: Blocking Evidence Review Workflow
  - ADR-047: EnhancedEvidence Consolidation
  - ADR-048: LLM Re-unification Strategy
  - ADR-032: Unified Wizard Pattern
  - ADR-027: User Context Field (immutable ground truth)
- **Related Features:**
  - ft-022: Unified Wizard Pattern
  - ft-024: CV Bullet Review & Edit
  - ft-015: Artifact Detail Page Enhancements
  - ft-005: Multi-Source Artifact Preprocessing

---

## Change Log

- **2025-01-06:** Feature spec created (Stage E of workflow)
- **2025-01-06:** Approved for implementation (Priority P0)
