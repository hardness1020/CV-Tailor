# ADR — Blocking Evidence Review Workflow in Artifact Upload Wizard

**Status:** Draft → Accepted (upon implementation completion)
**Date:** 2025-01-06
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-045 Evidence Review & Acceptance Workflow

## Context and Problem Statement

The application currently processes evidence extraction automatically but **lacks a review and acceptance mechanism** before using extracted content in downstream workflows:

**Current Flow (Problematic):**
```
User uploads artifact with evidence sources
  ↓
Backend extracts content via LLM (GitHub, PDFs)
  ✗ NO REVIEW STEP - content immediately used
  ✗ NO EDIT CAPABILITY - errors cannot be corrected
  ✗ NO ACCEPTANCE TRACKING - EnhancedEvidence.accepted field unused
  ↓
Artifact unified with potentially incorrect content
  ↓
Bullet generation uses flawed data
  ↓
User discovers errors only at final CV review (too late!)
```

**Problems with Current Approach:**

1. **Hallucination Propagation:** AI-extracted content may contain errors (wrong technologies, fabricated achievements, incorrect summaries) that propagate to CV/cover letters
2. **No User Control:** Users cannot verify or correct extracted content before it affects downstream generation
3. **Late Error Discovery:** Users only see extraction errors after bullet generation completes, requiring full regeneration
4. **Wasted Resources:** LLM calls for bullet generation based on incorrect evidence waste API costs
5. **Trust Issues:** Users lose confidence when CVs contain incorrect information they never verified
6. **Unused Infrastructure:** EnhancedEvidence.accepted field exists but is completely unused (no code queries it)

**User Feedback:**
> "The AI extracted wrong technologies from my project. By the time I noticed in the CV, I had to start over." (Beta user feedback)

**We need to decide:**

1. **When to review:** During upload wizard vs. separate detail page vs. before each generation
2. **How blocking:** Mandatory review before finalization vs. optional review with warnings
3. **Review depth:** Quick approve/reject vs. inline editing vs. comprehensive editing
4. **UX pattern:** Blocking wizard step vs. modal overlay vs. separate page
5. **Acceptance model:** 100% acceptance required vs. partial acceptance allowed

## Decision Drivers

- **Content Accuracy:** Prevent hallucinations and errors from propagating to CV/cover letters
- **User Control:** Users must verify and correct AI-extracted content before use
- **Early Validation:** Catch errors immediately after extraction, not after bullet generation
- **Resource Efficiency:** Avoid wasting LLM API calls on incorrect evidence
- **User Trust:** Build confidence by showing extracted content and allowing corrections
- **Professional UX:** Serious review process matching S-Tier SaaS quality standards
- **No Shortcuts:** Force comprehensive review (user requirement: "don't provide any efficient way to let user easy approve")
- **Ease of Editing:** Make it simple to correct mistakes inline (user requirement: "allow user to easy edit the content")

## Considered Options

### Option A: Post-Upload Detail Page Review (Asynchronous)

**Approach:** Evidence review happens in artifact detail page after upload wizard completes

**Flow:**
```
Upload wizard (4 steps) → Complete → Artifact detail page → Evidence tab → Review & accept
```

**Pros:**
- Non-blocking wizard (faster completion)
- More space for comprehensive editing
- Can review evidence multiple times
- Existing detail page infrastructure

**Cons:**
- **Async review gap:** User might forget to review before generation
- **Inconsistent enforcement:** No guarantee user completes review
- **Context switching:** User must navigate away from wizard to detail page
- **Poor UX:** Breaks natural workflow (upload → review → finalize)
- **Delayed validation:** User might start generation with unreviewed evidence
- **No blocking mechanism:** Cannot prevent premature bullet generation

**Estimated Effort:** 6-8 hours (detail page UI + tab integration)

---

### Option B: Modal Overlay During Wizard (Non-Blocking)

**Approach:** Show modal overlay with evidence review in Step 5 (optional review)

**Flow:**
```
Upload wizard Step 4 (Evidence) → Step 5 (Optional Review Modal) → Step 6 (Complete)
```

**Pros:**
- In-wizard experience (no navigation)
- Quick implementation (reuse modal)
- User can skip if confident

**Cons:**
- **Optional review:** User can skip and propagate errors
- **Cramped UI:** Modal limits space for inline editing
- **Inconsistent with wizard pattern:** Modal breaks full-page experience (ADR-032)
- **No blocking:** Cannot enforce 100% acceptance
- **Poor mobile UX:** Modal on small screens
- **Violates user requirement:** Allows "easy approve" shortcuts

**Estimated Effort:** 8-10 hours (modal UI + integration)

---

### Option C: Blocking Wizard Steps with Inline Editing (Recommended)

**Approach:** Add two blocking wizard steps (Step 5: Processing, Step 6: Evidence Review) with mandatory 100% acceptance

**Flow:**
```
Step 1-4: Artifact upload (existing)
  ↓
Step 5: Evidence Processing [PHASE 1: EXTRACTION] (blocking spinner, ~30 seconds)
  - Backend extracts content via Celery (per-source extraction)
  - Creates EnhancedEvidence records (NOT unified yet)
  - Sets artifact.status='processing' BEFORE task trigger (race condition prevention)
  - Frontend polls artifact.status every 10s
  - Unblocks when status='review_pending'
  ↓
Step 6: Evidence Review & Acceptance (blocking on user action)
  - User reviews ALL evidence content (summary, technologies, achievements)
  - User edits content inline (fix errors, add missing items)
  - User accepts each evidence individually
  - Finalize button disabled until 100% acceptance
  ↓
Step 6: Artifact Finalization [PHASE 2: REUNIFICATION] (blocking spinner, ~30-45 seconds)
  - Backend re-unifies artifact from accepted evidence via LLM
  - Sets artifact.status='reunifying' BEFORE task trigger (race condition prevention)
  - Frontend polls artifact.status every 3s
  - Unblocks when status='complete'
  ↓
Artifact finalization complete → Navigate to artifacts page
```

**Pros:**
- **Guaranteed review:** Users cannot skip (100% acceptance required)
- **Early validation:** Errors caught before bullet generation starts
- **Natural workflow:** Upload → Process → Review → Finalize (logical progression)
- **Inline editing:** Easy corrections directly in review step
- **Consistent UX:** Full-page wizard pattern (aligns with ADR-032)
- **Clear blocking:** Users understand what's required to proceed
- **Mobile-friendly:** Full-page works on all screen sizes
- **Prevents hallucinations:** User verifies all content before use
- **Meets user requirements:** Forces serious review, allows easy editing

**Cons:**
- **Longer wizard:** 6 steps instead of 4 (adds ~2-5 minutes)
- **Development complexity:** 14-18 hours (new components, API endpoints, service methods)
- **Blocking UX:** Users must wait for processing (Step 5) and complete review (Step 6)

**Estimated Effort:** 14-18 hours (backend + frontend + tests)

---

### Option D: Hybrid with Quick-Approve Shortcuts

**Approach:** Blocking wizard step but with "Accept All" and confidence-based auto-accept (≥90%)

**Flow:**
```
Step 6: Evidence Review
  - High confidence (≥90%): Auto-accepted, user can unaccept
  - Medium confidence (50-90%): Requires review
  - Low confidence (<50%): Requires detailed review
  - "Accept All" button for power users
```

**Pros:**
- Faster for high-quality evidence
- Reduced friction for confident users
- Smart automation based on confidence

**Cons:**
- **Violates user requirement:** "Don't provide any efficient way to let user easy approve"
- **False confidence:** High AI confidence ≠ guaranteed accuracy
- **Shortcuts undermine trust:** Users might skip review
- **Complex logic:** Auto-accept rules add complexity
- **Inconsistent enforcement:** Some evidence reviewed, some not

**Estimated Effort:** 16-20 hours (complex conditional logic)

---

### Option E: Separate Evidence Review Page

**Approach:** Dedicated `/artifacts/:id/review-evidence` page separate from wizard

**Flow:**
```
Upload wizard (4 steps) → Complete → Auto-navigate to /artifacts/:id/review-evidence → Review → Detail page
```

**Pros:**
- Clean separation of concerns
- Dedicated review experience
- Can bookmark/share review page

**Cons:**
- **Breaks wizard flow:** Context loss between wizard and review page
- **Extra navigation:** User must move between pages
- **Inconsistent UX:** Not part of wizard pattern
- **More complex routing:** Additional route and navigation logic
- **Poor mobile UX:** Full page transition on mobile

**Estimated Effort:** 12-16 hours (new page + routing + integration)

## Decision Outcome

**Chosen Option: Option C - Blocking Wizard Steps with Inline Editing**

### Rationale

1. **Prevents Hallucinations (Primary Goal):** 100% acceptance requirement ensures users verify ALL AI-extracted content before it affects downstream workflows. No shortcuts, no bypasses.

2. **User Control & Editing:** Inline editing makes corrections simple:
   - Edit summary in textarea (fix errors, add context)
   - Add/remove technologies via tag list
   - Edit achievements line-by-line
   - Auto-save on blur (immediate persistence)

3. **Natural Workflow:** Upload → Process → Review → Finalize is the logical progression users expect. Blocking at the right time (after extraction completes) minimizes frustration.

4. **Early Validation:** Errors caught immediately after extraction:
   - Before bullet generation starts
   - Before LLM API costs incurred
   - Before user investment in downstream tasks
   - When context is fresh (user just uploaded evidence)

5. **Meets User Requirements:**
   - ✅ "All evidence should be reviewed seriously before proceeding" → 100% acceptance required
   - ✅ "Don't provide any efficient way to let user easy approve" → No quick-accept shortcuts
   - ✅ "Allow user to easy edit the content" → Inline editing with auto-save

6. **Consistent with Wizard Pattern (ADR-032):** Full-page wizard with blocking steps aligns with unified wizard design system. Professional, immersive experience.

7. **Mobile-Friendly:** Full-page works naturally on mobile (no cramped modals or drawers).

8. **Clear Progress Indicators:**
   - Step 5: Spinner with message "Extracting content from your evidence sources..."
   - Step 6: Progress counter "2/3 accepted" + disabled/enabled Finalize button
   - Users understand what's blocking and why

9. **Resource Efficiency:** Prevents wasted LLM API calls by validating evidence before bullet generation.

10. **Trust & Confidence:** Users see exactly what AI extracted and verify it before use. Builds confidence in system accuracy.

### Architecture Decision

**Wizard Flow Structure:**
```
ArtifactUploadFlow (6 steps, purple theme)
├── Step 1: Basic Info (existing)
├── Step 2: Your Context (existing)
├── Step 3: Evidence (Technologies removed)
├── Step 4: Confirm Details (review before artifact creation)
├── Step 5: Evidence Review (consolidated Processing + Review - blocking)
│   ├── Component: ConsolidatedProcessingStep
│   ├── Phase 1: Auto-show "Extracting content..." spinner
│   ├── Phase 2: Auto-transition to evidence review UI
│   ├── Behavior: Review all evidence, inline editing, accept/reject
│   ├── Unblock: ALL evidence accepted (100%)
│   └── SLO: <3 minutes for processing, user-paced review
└── Step 6: Final Review (consolidated Reunification + Acceptance - blocking on user)
    ├── Component: ConsolidatedReunificationStep
    ├── Phase 1: Auto-show "Finalizing..." spinner (~30-45s)
    ├── Phase 2: Auto-transition to acceptance UI
    ├── Behavior: Review unified_description, technologies, achievements
    ├── Unblock: User clicks "Accept Artifact"
    └── Action: Set status='complete' → Navigate to detail page
```

**Two-Phase Consolidated Blocking Pattern:**
1. **Step 5 - Phase 1:** Backend processing block (~1-3 minutes)
   - Technical constraint (backend extraction time)
   - Auto-show spinner: "Extracting content from your evidence sources..."
   - Non-interactive (user waits with progress indicator)
   - Auto-transition to Phase 2 when status='review_pending'

   **Step 5 - Phase 2:** User evidence review block (user-paced)
   - Auto-show evidence review UI
   - User action required (review and accept ALL evidence)
   - Interactive (user edits, accepts, rejects evidence items)
   - Variable duration (depends on user review depth)
   - Unblock: Click "Finalize & Continue" when all evidence accepted

2. **Step 6 - Phase 1:** LLM reunification block (~30-45 seconds)
   - Auto-show spinner: "Finalizing your artifact..."
   - Non-interactive (user waits for reunification)
   - Auto-transition to Phase 2 when status='review_finalized'

   **Step 6 - Phase 2:** Final artifact acceptance (user-paced)
   - Auto-show acceptance UI with unified content
   - User reviews final unified_description, technologies, achievements
   - Unblock: Click "Accept Artifact" to complete wizard

**Component Architecture:**
```typescript
ConsolidatedProcessingStep (Step 5 - consolidated)
  ├── State Machine: 'processing' | 'reviewing' | 'finalizing'
  ├── Phase 1 (processing):
  │   ├── Polls: GET /api/v1/artifacts/{id}/ every 10s
  │   ├── Displays: Spinner with "Extracting content..." message
  │   └── Auto-transition: When status='review_pending'
  ├── Phase 2 (reviewing):
  │   ├── Fetches: GET /api/v1/artifacts/{id}/evidence-acceptance-status/
  │   ├── Renders: EvidenceCard[] (one per evidence)
  │   ├── Tracks: Acceptance progress (2/3 accepted)
  │   └── Actions: "Finalize & Continue" when 100% accepted
  └── Phase 3 (finalizing):
      ├── Triggers: POST /api/v1/artifacts/{id}/finalize-review/
      ├── Polls: Waiting for status='reunifying'
      └── Auto-advance: To Step 6 when reunification starts

ConsolidatedReunificationStep (Step 6 - consolidated)
  ├── State Machine: 'finalizing' | 'accepting'
  ├── Phase 1 (finalizing):
  │   ├── Polls: GET /api/v1/artifacts/{id}/ every 3s
  │   ├── Displays: Spinner with "Finalizing your artifact..." message
  │   └── Auto-transition: When status='review_finalized'
  └── Phase 2 (accepting):
      ├── Displays: unified_description, enriched_technologies, enriched_achievements
      ├── Action: "Accept Artifact" button
      └── API: POST /api/v1/artifacts/{id}/accept/ → status='complete'

EvidenceCard (new)
  ├── Displays: Evidence content (summary, technologies, achievements)
  ├── Shows: ConfidenceBadge (red <50%, yellow 50-80%, green ≥80%)
  ├── Editing: Inline textarea (summary), tag list (technologies), list items (achievements)
  ├── Actions: Accept, Reject, Edit
  └── API Calls:
      ├── PATCH /api/v1/artifacts/{id}/evidence/{id}/content/ (edit)
      ├── POST /api/v1/artifacts/{id}/evidence/{id}/accept/ (accept)
      └── POST /api/v1/artifacts/{id}/evidence/{id}/reject/ (reject)

useEvidenceReview (new hook)
  ├── State: evidence[], acceptanceStatus, isLoading, error
  ├── Methods: acceptEvidence(), rejectEvidence(), editContent(), finalizeReview()
  └── API: All evidence review endpoints
```

**Backend Integration:**
```
POST /api/v1/artifacts/{id}/finalize-evidence-review/
  ↓
ArtifactEnrichmentService.reunify_from_accepted_evidence(artifact_id)
  ↓
Reads EnhancedEvidence.processed_content (user-edited) where accepted=True
  ↓
Calls GPT-5 to re-unify artifact description/technologies/achievements
  ↓
Updates Artifact fields (description, enriched_technologies, enriched_achievements)
  ↓
Returns unified artifact with acceptance summary
```

### Validation Rules

**Step 5 (Processing):**
- ✅ Cannot proceed until `enrichment_status === 'completed'`
- ✅ Show error if `enrichment_status === 'failed'`

**Step 6 (Review):**
- ✅ Cannot finalize until ALL evidence accepted (100%)
- ✅ Rejection prevents finalization (must accept all)
- ✅ Edits auto-saved on blur (PATCH endpoint)
- ✅ Backend validates edited content structure

## Consequences

### Positive

1. **Prevents Hallucinations:**
   - Users verify ALL AI-extracted content before use
   - Errors caught immediately (before bullet generation)
   - High confidence in CV/cover letter accuracy

2. **Better User Control:**
   - Inline editing for easy corrections
   - Clear accept/reject actions per evidence
   - Visual confidence indicators guide review

3. **Resource Efficiency:**
   - No wasted LLM API calls on incorrect evidence
   - Re-unification uses verified content only
   - Fewer regeneration requests (errors caught early)

4. **Improved Trust:**
   - Users see what AI extracted
   - Users verify before use
   - Transparent process builds confidence

5. **Consistent UX:**
   - Aligns with ADR-032 full-page wizard pattern
   - Professional, immersive experience
   - Clear progress visualization

6. **Mobile-Friendly:**
   - Full-page works on all devices
   - Touch-friendly buttons
   - Responsive layout

### Negative

1. **Longer Wizard:**
   - **Impact:** 6 steps instead of 4 (adds ~2-5 minutes to upload)
   - **Mitigation:**
     - Step 5 auto-completes (~30 seconds)
     - Step 6 is valuable time (catches errors early)
     - Overall time saved (fewer regenerations)
     - User expectation: serious review is worth the time

2. **Development Cost:**
   - **Impact:** 14-18 hours to implement (backend + frontend + tests)
   - **Mitigation:**
     - Reuse existing components (ConfidenceBadge, LoadingOverlay)
     - Clear specifications reduce rework
     - ROI positive (prevents support tickets, improves accuracy)

3. **Blocking UX:**
   - **Impact:** Users must wait for processing (Step 5) and complete review (Step 6)
   - **Mitigation:**
     - Step 5: Clear progress message, expected ~30s
     - Step 6: User-paced (no time pressure), progress counter
     - Smart blocking (unblock as soon as possible)
     - Alternative: Could allow save as draft (future enhancement)

4. **Potential User Resistance:**
   - **Impact:** Some users may want to skip review (trust AI)
   - **Mitigation:**
     - User requirement confirms mandatory review desired
     - Analytics will validate (expect high edit rates 40-60%)
     - Future: Could add "Express Upload" for power users (separate ADR)

### Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users abandon wizard at Step 6 | Medium | High | Clear messaging ("Almost done! Review to ensure accuracy"), progress counter, save draft option (future) |
| Step 5 processing takes >30s | Medium | Medium | Performance optimization (parallel extraction), backend caching, clear timeout messages |
| Inline editing UX confusing | Low | Medium | User testing, tooltips, visual feedback (save indicators) |
| Backend re-unification fails | Low | High | Retry logic, fallback to original unification, error message with support link |
| Mobile editing difficult | Medium | Medium | Touch-friendly inputs, responsive design, device testing |
| Users edit too much (break structure) | Low | Low | Backend validation, input constraints, preview before finalize |

## Implementation Notes

### Phase 1: Backend Infrastructure (6-8 hours)

**Deliverables:**
- `backend/llm_services/services/core/artifact_enrichment_service.py`
  - New method: `reunify_from_accepted_evidence(artifact_id)`
- `backend/artifacts/views.py`
  - New endpoints: finalize_evidence_review, accept_evidence, reject_evidence, edit_evidence_content, get_evidence_acceptance_status
- `backend/artifacts/serializers.py`
  - New serializers: AcceptanceStatusSerializer, ProcessedContentSerializer
- `backend/llm_services/models.py`
  - Use existing EnhancedEvidence.accepted field (no schema changes needed)

**Tests:**
- Unit tests for reunify_from_accepted_evidence (15 tests)
- Integration tests for evidence review endpoints (5 tests)

### Phase 2: Frontend Components (6-8 hours)

**Deliverables:**
- `frontend/src/components/wizard/ProcessingStep.tsx`
- `frontend/src/components/wizard/EvidenceReviewStep.tsx`
- `frontend/src/components/wizard/EvidenceCard.tsx`
- `frontend/src/hooks/useEvidenceReview.ts`

**Tests:**
- Unit tests for components (8 tests)
- Integration tests for full wizard flow (3 tests)

### Phase 3: Integration & Polish (2-3 hours)

**Activities:**
- Update ArtifactUploadFlow to 6 consolidated steps (includes Step 6: Final Review with auto-transition acceptance)
- Wire up API endpoints (including new POST /accept-artifact/)
- Add error handling and loading states
- Accessibility audit (WCAG 2.1 AA)
- Mobile responsive testing

**Success Criteria:**
- All tests passing
- WCAG 2.1 AA compliant
- Step 5 unblocks in <30s (95% of cases)
- Step 5 Finalize button state correct (enabled when 100% accepted)
- Step 6 Phase 2 Accept button navigates to artifact detail page on success

### Performance SLOs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Step 5 processing time | <30s (95th percentile) | CloudWatch metrics |
| Evidence edit auto-save | <2s | API response time |
| Evidence accept/reject | <1s | API response time |
| Finalize re-unification | <45s | API response time |
| Page load (Step 5) | <2s | Lighthouse performance |
| Accept artifact action | <1s | API response time |

### Success Metrics

**Quantitative:**
- Evidence acceptance rate: 100% (enforced by design)
- Evidence edit rate: 40-60% (users editing extracted content)
- Average review time per evidence: ≤3 minutes
- Re-unification success rate: ≥95%
- Wizard abandonment at Step 5 (Evidence Review): <10%
- Artifact acceptance rate: ≥90% (users accepting at Step 6 vs editing)

**Qualitative:**
- User feedback on review process (NPS)
- Support tickets related to incorrect evidence (expect decrease)
- User confidence in CV accuracy (survey)

---

### Phase 4: Wizard Resume Pattern for Re-Enrichment (ft-046)

**Problem**: After initial artifact creation, users need to re-enrich artifacts when adding new evidence sources or refreshing enriched content. Original ADR-046 only covered first-time creation flow.

**Solution**: Extend wizard to support "resume mode" via URL parameters, allowing users to jump directly to Step 3 (evidence changes) or Step 5 (content refresh) for existing artifacts.

**Deliverables:**

**Frontend:**
- `frontend/src/components/ArtifactUpload.tsx`
  - Add URL parameter parsing (`?artifactId={id}&startStep={3|5}`)
  - Implement "resume mode" state (pre-populate form from existing artifact)
  - Handle PATCH operations (update existing artifact, not create new)

- `frontend/src/components/wizard/ConsolidatedReunificationStep.tsx`
  - Update navigation: complete → `/artifacts/{id}` (detail page, not list page)

- `frontend/src/pages/ArtifactDetailPage.tsx`
  - Remove "AI Suggestions" tab (eliminate duplicate evidence review UI)
  - Add dropdown "Re-enrich" button with two options:
    - "Re-enrich Evidence" → Navigate to `/upload-artifact?artifactId={id}&startStep=3`
    - "Re-enrich Artifact" → Navigate to `/upload-artifact?artifactId={id}&startStep=5`
  - Move enriched content display to Details tab (inline, editable)

**Backend:**
- No new endpoints needed (existing endpoints support re-enrichment)
- Verification: `trigger_artifact_enrichment` is idempotent (can be called multiple times)
- Verification: `finalize_evidence_review` uses EnhancedEvidence.accepted (same logic for re-enrichment)

**Tests:**
- Wizard resume mode unit tests (URL param parsing, pre-population)
- Re-enrich dropdown interaction tests
- Navigation flow tests (detail page → wizard → detail page)
- Inline editing tests (enriched field edits)

**Implementation Timeline**: 11 hours
- Backend validation: 1 hour
- Frontend wizard resume: 3 hours
- Frontend detail page redesign: 4 hours
- Navigation updates: 1 hour
- Testing & documentation: 2 hours

**Re-Enrichment Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                   Artifact Detail Page                       │
│                   (status='complete')                        │
│                                                              │
│  [Re-enrich ▼]                                              │
│     ├─ Re-enrich Evidence (Step 3 entry)                   │
│     └─ Re-enrich Artifact (Step 5 entry)                   │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
        ┌─────────┴────────┐    ┌────────┴─────────┐
        │ Option 1:        │    │ Option 2:        │
        │ Full Re-enrich   │    │ Fast Refresh     │
        │ (with evidence   │    │ (content only)   │
        │  changes)        │    │                  │
        └─────────┬────────┘    └────────┬─────────┘
                  │                      │
        ┌─────────▼────────┐    ┌───────▼──────────┐
        │ Step 3: Evidence │    │ Step 5: Evidence │
        │ (add/remove/edit)│    │ Review (existing)│
        └─────────┬────────┘    └───────┬──────────┘
                  │                      │
        ┌─────────▼────────┐             │
        │ Step 4: Confirm  │             │
        │ Details          │             │
        └─────────┬────────┘             │
                  │                      │
        ┌─────────▼────────┐             │
        │ Step 5: Evidence │             │
        │ Review           │             │
        │ (Phase 1: Auto-  │             │
        │  show processing)│             │
        │ (Phase 2: Review)│             │
        └─────────┬────────┘             │
                  │                      │
                  │        ┌─────────────┘
                  │        │
        ┌─────────▼────────▼─────────────────────────┐
        │ Step 6: Final Review                       │
        │ (Phase 1: Auto-show reunification spinner) │
        │ (Phase 2: Acceptance UI)                   │
        │ (review final content, click Accept)       │
        └─────────┬──────────────────────────────────┘
                  │
        ┌─────────▼────────┐
        │ Artifact Detail  │
        │ (accepted)       │
        └──────────────────┘
```

**Status Transition Updates:**

Original transitions (first-time creation):
```
draft → processing → review_pending → reunifying → review_finalized → complete
```

New transitions (re-enrichment):
```
Option 1 (Full Re-enrich):
complete → processing → review_pending → reunifying → review_finalized → complete

Option 2 (Fast Refresh):
complete → reunifying → review_finalized → complete
(skips processing phase since evidence unchanged)
```

**Design Decision**: Make wizard the SINGLE source of truth for evidence review/acceptance. Detail page shows enriched content (read-only or inline editable) but does NOT duplicate the evidence review UI.

**Rationale**:
- Eliminates UX confusion (one way to review evidence)
- Prevents duplicate code (EvidenceReviewStep used for both create and re-enrich)
- Consistent workflow (same review UI for first-time and updates)
- Wizard pattern scales (can add steps without detail page bloat)

**Risks**:
- Navigation complexity (detail page → wizard → detail page)
- State management (pre-populating wizard from existing artifact)
- Data synchronization (ensuring detail page refreshes after re-enrichment)

**Mitigation**:
- Thorough unit tests for wizard resume mode
- Navigation guards to prevent loops
- Clear loading states during re-enrichment
- Graceful error handling (redirect to list page on fetch failure)

---

## References

- **PRD:** `docs/prds/prd.md` (v1.5.0) - Evidence Review & Acceptance workflow requirements
- **DISCOVERY:** `docs/discovery/disco-001-evidence-review-workflow.md` - Comprehensive workflow analysis
- **TECH SPECS:**
  - `docs/specs/spec-frontend.md` (v3.0.0) - Evidence Review & Acceptance Workflow
  - `docs/specs/spec-api.md` (v4.9.0) - Evidence review endpoints
  - `docs/specs/spec-llm.md` (v4.3.0) - reunify_from_accepted_evidence method
- **FEATURE:** `docs/features/ft-045-evidence-review-workflow.md` - Implementation plan (to be created in Stage E)
- **Related ADRs:**
  - ADR-032: Unified Full-Page Wizard Pattern (blocking wizard foundation)
  - ADR-015: Multi-Source Artifact Preprocessing (evidence extraction context)
  - ADR-020: Artifact Enrichment Quality Issues (hallucination prevention motivation)

## Related Decisions

- **ADR-047:** EnhancedEvidence Consolidation (remove ExtractedContentModel redundancy)
- **ADR-048:** LLM Re-unification Strategy (how to re-unify from user-edited evidence)

## Notes

- This ADR will transition from "Draft" to "Accepted" upon successful implementation and deployment
- Git tag: `adr-046-blocking-evidence-review-workflow` after acceptance
- SPEC versions v3.0.0 (frontend), v4.9.0 (api), v4.3.0 (llm) include this workflow
- EnhancedEvidence.accepted field will be used for the first time (currently unused)
- Two-phase blocking pattern (processing + review) is novel; monitor UX metrics closely
