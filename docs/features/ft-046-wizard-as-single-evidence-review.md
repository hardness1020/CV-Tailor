# Feature — 046 wizard-as-single-evidence-review
**File:** docs/features/ft-046-wizard-as-single-evidence-review.md
**Owner:** Marcus
**TECH-SPECs:** `spec-frontend.md` (v2.1), `spec-api.md` (v1.3)

## Overview

**Problem**: Evidence review/acceptance UI is duplicated between wizard (Step 5 in 6-step consolidated wizard) and artifact detail page (AI Suggestions tab), creating UX confusion. Re-enrichment bypasses evidence review entirely, skipping quality control.

**Solution**: Make wizard the ONLY place for evidence review/acceptance. Detail page provides dropdown "Re-enrich" button that redirects to wizard at appropriate step (Step 3 for evidence changes, Step 5 for content-only review).

**Related Features**: ft-045 (Evidence Review Workflow), ft-022 (Unified Wizard Pattern)

---

## Stage B Discovery Findings

### Test Impact Analysis

**Tests to Update:**
- `frontend/src/components/wizard/__tests__/ArtifactUpload.test.tsx` - add wizard resume mode tests
- `frontend/src/components/wizard/__tests__/ReunificationStep.test.tsx` - update navigation assertion (detail page, not list page)
- `frontend/src/pages/__tests__/ArtifactDetailPage.test.tsx` - remove AI Suggestions tab tests, add re-enrich dropdown tests

**Tests to Remove:**
- AI Suggestions tab interaction tests (tab removal)
- Detail page "Accept All" button tests (functionality removed)

**Coverage Gaps:**
- Wizard resume flow with pre-populated artifact data (0% coverage) - NEW
- URL parameter parsing for startStep (0% coverage) - NEW
- Dropdown re-enrich button interactions (0% coverage) - NEW

**Test Update Checklist:**
- [ ] Add wizard resume mode unit tests (Step 3 and Step 5 entry points)
- [ ] Add URL parameter parsing tests
- [ ] Update ReunificationStep navigation tests
- [ ] Remove AI Suggestions tab tests from detail page
- [ ] Add re-enrich dropdown interaction tests
- [ ] Add enriched content inline editing tests

### Existing Implementation Analysis

**Similar Features:**
- `frontend/src/components/ArtifactUpload.tsx` - existing wizard with 6-step consolidated flow (includes Step 6: Final Review with artifact acceptance)
- `frontend/src/components/wizard/ConsolidatedProcessingStep.tsx` - consolidated evidence processing + review UI (Step 5)
- `frontend/src/components/wizard/ConsolidatedReunificationStep.tsx` - consolidated reunification + acceptance UI (Step 6)
- `frontend/src/pages/ArtifactDetailPage.tsx` - existing detail page with tabs

**Reusable Components:**
- `EvidenceReviewStep` - no changes needed, already supports evidence review
- `EvidenceCard` - reusable for both create and edit flows
- `EnrichedContentViewer` - can be refactored for inline use in Details tab

**Patterns to Follow:**
- Wizard step pattern from ft-022 (unified wizard architecture)
- URL parameter navigation (React Router `useSearchParams`)
- Dropdown menu pattern (Radix UI `DropdownMenu`)

**Code to Refactor:**
- `ArtifactDetailPage.tsx` - Remove AI Suggestions tab, reorganize Details tab
- `EnrichedContentViewer.tsx` - Convert from tab component to inline component
- `ArtifactUpload.tsx` - Add resume mode logic

### Dependency & Side Effect Mapping

**Dependencies:**
- `apiClient.getArtifact()` - fetch artifact data for wizard pre-population
- React Router `useSearchParams` - parse URL parameters
- Wizard state management (Zustand or React state) - handle pre-populated data

**Side Effects:**
- Navigation flow changes (Step 6 Phase 2 → detail page after artifact acceptance)
- Detail page tab structure changes (removal of AI Suggestions)
- URL structure changes (addition of `?artifactId=X&startStep=Y` parameters)
- Consolidated acceptance UI (Step 6 Phase 2) already exists in wizard flow

**Impact Radius:**
- **Frontend Wizard**: Medium impact - add resume mode, navigation change
- **Frontend Detail Page**: High impact - tab removal, content reorganization, new dropdown
- **Backend**: Low impact - no API changes needed (existing endpoints support edit operations)

**Risk Areas:**
- Wizard state management with pre-populated data (untested) - **HIGH RISK**
- Navigation loop potential (detail page → wizard → detail page) - **MEDIUM RISK**
- Data synchronization between wizard and detail page - **MEDIUM RISK**

---

## Architecture Conformance

**Layer Assignment:**
- Frontend wizard updates in `frontend/src/components/ArtifactUpload.tsx` (presentation layer)
- Frontend detail page updates in `frontend/src/pages/ArtifactDetailPage.tsx` (presentation layer)
- No backend layer changes required

**Pattern Compliance:**
- Follows React Router navigation pattern ✓
- Uses existing wizard step architecture from ft-022 ✓
- Maintains separation of concerns (wizard = review, detail page = view/edit) ✓

**Dependencies:**
- React Router `useSearchParams` hook
- Radix UI `DropdownMenu` component
- Existing wizard state management

---

## Acceptance Criteria

### Wizard Resume Mode
- [ ] Wizard can be opened with `?artifactId=X&startStep=3` URL parameter
- [ ] Wizard can be opened with `?artifactId=X&startStep=5` URL parameter
- [ ] When resuming, wizard pre-populates all form data from existing artifact
- [ ] Resuming at Step 3 shows evidence list from existing artifact
- [ ] Resuming at Step 5 shows evidence review from latest enrichment
- [ ] Wizard submit updates existing artifact (not create new one)

### Detail Page Redesign
- [ ] AI Suggestions tab is removed entirely
- [ ] Enriched content visible in Details tab (inline, not separate tab)
- [ ] Dropdown "Re-enrich" button with two options visible
- [ ] "Re-enrich Evidence" navigates to `/upload-artifact?artifactId={id}&startStep=3`
- [ ] "Re-enrich Artifact" navigates to `/upload-artifact?artifactId={id}&startStep=5`
- [ ] Enriched fields (description, technologies, achievements) editable inline
- [ ] Manual edits to enriched fields save via PATCH API

### Navigation Changes
- [ ] Step 6 Phase 1 (ConsolidatedReunificationStep auto-processing) auto-transitions to Phase 2 (Artifact Acceptance)
- [ ] Step 6 Phase 2 (Artifact Acceptance UI) "Accept Artifact" button navigates to `/artifacts/{id}` (detail page)
- [ ] Detail page shows updated enriched content after artifact acceptance
- [ ] No navigation loops or infinite redirects

### Data Consistency
- [ ] Re-enriching updates artifact in-place (same artifact ID)
- [ ] Detail page refreshes with latest data after returning from wizard
- [ ] Manual edits on detail page persist correctly

---

## Design Changes

### Frontend - Wizard Resume Mode

**ArtifactUpload.tsx** (lines ~1-100):
```typescript
// NEW: Parse URL parameters for resume mode
const [searchParams] = useSearchParams()
const resumeArtifactId = searchParams.get('artifactId')
const startStep = searchParams.get('startStep')

// NEW: State for resume mode
const [isResumeMode, setIsResumeMode] = useState(false)
const [resumedArtifact, setResumedArtifact] = useState<Artifact | null>(null)

useEffect(() => {
  if (resumeArtifactId && startStep) {
    // Fetch artifact data and pre-populate wizard
    apiClient.getArtifact(parseInt(resumeArtifactId))
      .then(artifact => {
        setResumedArtifact(artifact)
        setIsResumeMode(true)
        setCurrentStep(parseInt(startStep))
        // Pre-populate form fields from artifact
        setFormData({
          title: artifact.title,
          description: artifact.description,
          artifactType: artifact.artifactType,
          // ... other fields
        })
      })
  }
}, [resumeArtifactId, startStep])
```

**ReunificationStep.tsx** (line 39-50):
```typescript
// CHANGED: Navigate to detail page instead of list page
if (status === 'complete') {
  clearInterval(intervalRef.current)
  intervalRef.current = null
  console.log('[ReunificationStep] Artifact complete, navigating to detail page')
  navigate(`/artifacts/${artifactId}`) // CHANGED from '/artifacts'
}
```

### Frontend - Detail Page Redesign

**ArtifactDetailPage.tsx** (major restructure):
```typescript
// REMOVED: AI Suggestions tab (lines ~297-400)
// REMOVED: handleAcceptAll functionality

// ADDED: Dropdown re-enrich button
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="outline">
      <RefreshCw className="mr-2 h-4 w-4" />
      Re-enrich
      <ChevronDown className="ml-2 h-4 w-4" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem onClick={() => navigate(`/upload-artifact?artifactId=${artifact.id}&startStep=3`)}>
      <FileEdit className="mr-2 h-4 w-4" />
      Re-enrich Evidence
      <span className="text-xs text-gray-500 ml-2">Review evidence sources</span>
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => navigate(`/upload-artifact?artifactId=${artifact.id}&startStep=5`)}>
      <Sparkles className="mr-2 h-4 w-4" />
      Re-enrich Artifact
      <span className="text-xs text-gray-500 ml-2">Fast content refresh</span>
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>

// ADDED: Enriched content inline in Details tab
<div className="space-y-4">
  <h3>Original Information</h3>
  {/* Existing artifact fields */}

  <Separator />

  <h3>AI-Generated Content</h3>
  <EnrichedContentInline
    artifact={artifact}
    onEdit={handleEditEnrichedField}
  />
</div>
```

**EnrichedContentViewer.tsx** → **EnrichedContentInline.tsx** (refactor):
```typescript
// NEW: Inline editable version for Details tab
export function EnrichedContentInline({ artifact, onEdit }: Props) {
  const [editMode, setEditMode] = useState(false)
  const [editedDescription, setEditedDescription] = useState(artifact.unifiedDescription)

  return (
    <div className="space-y-3">
      <div>
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium">Enriched Description</label>
          <Button variant="ghost" size="sm" onClick={() => setEditMode(!editMode)}>
            {editMode ? 'Cancel' : 'Edit'}
          </Button>
        </div>
        {editMode ? (
          <Textarea
            value={editedDescription}
            onChange={(e) => setEditedDescription(e.target.value)}
            onBlur={() => onEdit('unifiedDescription', editedDescription)}
          />
        ) : (
          <p className="text-sm text-gray-700">{artifact.unifiedDescription}</p>
        )}
      </div>

      {/* Similar for technologies, achievements */}
    </div>
  )
}
```

### Backend - No Changes Required

Existing endpoints already support editing:
- `GET /api/v1/artifacts/{id}/` - fetch artifact for wizard pre-population
- `PATCH /api/v1/artifacts/{id}/` - update enriched fields inline
- `POST /api/v1/artifacts/{id}/trigger-enrichment/` - re-enrich from detail page

---

## Test & Eval Plan

### Unit Tests (Jest + React Testing Library)

**Wizard Resume Mode** (`ArtifactUpload.test.tsx`):
```typescript
describe('Wizard Resume Mode', () => {
  test('should parse URL parameters and fetch artifact', async () => {
    // Mock useSearchParams to return artifactId=123&startStep=5
    // Mock apiClient.getArtifact
    // Assert wizard jumps to Step 5 with pre-populated data
  })

  test('should pre-populate form fields from artifact', () => {
    // Assert title, description, technologies filled
  })

  test('should update existing artifact on submit, not create new', () => {
    // Mock PATCH call, assert artifact ID unchanged
  })
})
```

**Detail Page Dropdown** (`ArtifactDetailPage.test.tsx`):
```typescript
describe('Re-enrich Dropdown', () => {
  test('should show two re-enrich options', () => {
    // Assert dropdown has "Re-enrich Evidence" and "Re-enrich Artifact"
  })

  test('should navigate to Step 3 on "Re-enrich Evidence"', () => {
    // Click option, assert navigate('/upload-artifact?artifactId=123&startStep=3')
  })

  test('should navigate to Step 5 on "Re-enrich Artifact"', () => {
    // Click option, assert navigate('/upload-artifact?artifactId=123&startStep=5')
  })
})
```

**Inline Editing** (`EnrichedContentInline.test.tsx`):
```typescript
describe('Enriched Content Inline Editing', () => {
  test('should show edit button for each field', () => {
    // Assert edit buttons visible
  })

  test('should save changes on blur', () => {
    // Edit field, blur, assert onEdit callback called with new value
  })
})
```

### Integration Tests (Playwright E2E)

**Full Re-enrichment Flow**:
```typescript
test('Re-enrich Evidence flow (Step 3 entry)', async ({ page }) => {
  // 1. Navigate to artifact detail page
  // 2. Click re-enrich dropdown → "Re-enrich Evidence"
  // 3. Assert wizard opens at Step 3 with existing evidence
  // 4. Proceed through Steps 3 → 4 → 5 (consolidated) → 6 (consolidated)
  // 5. Assert navigation to detail page
  // 6. Assert enriched content updated
})

test('Re-enrich Artifact flow (Step 5 entry)', async ({ page }) => {
  // 1. Navigate to artifact detail page
  // 2. Click re-enrich dropdown → "Re-enrich Artifact"
  // 3. Assert wizard opens at Step 5 (evidence review)
  // 4. Proceed through Steps 5 (Phase 2) → 6 (consolidated)
  // 5. Assert navigation to detail page
})

test('Inline editing enriched fields', async ({ page }) => {
  // 1. Navigate to artifact detail page
  // 2. Click edit on enriched description
  // 3. Modify text, blur
  // 4. Assert PATCH API called
  // 5. Refresh page, assert changes persisted
})
```

### Manual Test Scenarios

1. **First-time artifact creation** → Verify Step 6 Phase 2 shows artifact acceptance, "Accept" button navigates to detail page
2. **Re-enrich with evidence changes** → Add new GitHub link, re-enrich via Step 3, verify new content at Step 6 Phase 2
3. **Re-enrich without evidence changes** → Re-enrich via Step 5, verify faster flow, Step 6 acceptance
4. **Artifact acceptance flow** → Complete Step 6 Phase 1 reunification, review content at Phase 2, click "Accept Artifact"
5. **Manual edit enriched fields** → Edit description inline on detail page, verify persistence
6. **Navigation loop check** → Ensure no infinite redirects between detail page and wizard

---

## Telemetry & Metrics to Watch

**Metrics**:
- **Wizard resume rate**: % of wizard sessions started with `?artifactId` parameter
- **Re-enrich button clicks**: Track which option users prefer (Step 3 vs Step 5)
- **Inline edit usage**: % of users editing enriched fields manually vs. re-enriching
- **Navigation flow**: Track user path (create → detail vs. edit → detail)

**Dashboards**:
- Wizard completion funnel (with resume mode segmentation)
- Detail page engagement (time spent, re-enrich frequency)
- Error rate for wizard resume mode (failed artifact fetch, invalid step numbers)

**Alerts**:
- Alert if wizard resume rate drops below expected baseline (indicates UX issue)
- Alert if inline edit save failures exceed 2% (API/network issues)

---

## Edge Cases & Risks

### Edge Cases

1. **Invalid URL parameters**:
   - `?artifactId=invalid` → Show error, redirect to list page
   - `?startStep=99` → Clamp to valid range (1-6), default to Step 1
   - `?artifactId=999` (not found) → Show error, redirect to list page

2. **Artifact in wrong status**:
   - Resume wizard for artifact with `status='processing'` → Show warning, allow anyway
   - Resume wizard for artifact with `status='abandoned'` → Show warning, reactivate artifact

3. **Concurrent edits**:
   - User edits artifact inline while re-enrichment running → Show conflict warning, prefer latest
   - Two tabs open editing same artifact → Last write wins (eventual consistency)

4. **Missing enriched data**:
   - Artifact never enriched → Inline editing shows empty state with "No enriched content yet"
   - Re-enrich fails → Detail page shows old enriched content (if exists)

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Wizard state corruption with pre-populated data** | HIGH | Thorough unit tests, validation of artifact data before pre-population |
| **Navigation loop (detail → wizard → detail infinitely)** | MEDIUM | Add navigation guards, track navigation history |
| **Data loss during re-enrichment** | MEDIUM | Keep old enriched content until new enrichment succeeds |
| **Performance degradation with large artifacts** | LOW | Lazy load evidence content, paginate if needed |
| **User confusion with two re-enrich options** | LOW | Clear labels with descriptions, tooltips |

---

## Implementation Phases

### Phase 1: Backend Validation (1 hour)
- Verify existing endpoints support wizard resume use case
- Test PATCH endpoint for enriched field editing
- Add any missing validations

### Phase 2: Frontend Wizard Resume (3 hours)
- Add URL parameter parsing
- Implement artifact pre-population logic
- Update wizard state management
- Add unit tests

### Phase 3: Frontend Detail Page Redesign (4 hours)
- Remove AI Suggestions tab
- Add dropdown re-enrich button
- Move enriched content to Details tab
- Implement inline editing
- Add unit tests

### Phase 4: Navigation Updates (1 hour)
- Update ReunificationStep navigation
- Add navigation guards
- Test navigation flows

### Phase 5: Testing & Documentation (2 hours)
- E2E tests for full flows
- Update ft-045 with re-enrichment workflows
- Update ADR-046 with wizard resume pattern

**Total Estimated Effort**: ~11 hours

---

## Rollout Strategy

**Deployment**:
1. Backend changes (if any) - deploy first
2. Frontend changes - deploy together (wizard + detail page)
3. Monitor error rates for 24h post-deployment

**Rollback Plan**:
- If critical issues, rollback frontend to previous version
- Detail page shows "Feature under maintenance" message
- Wizard creation flow still works (Step 1-8 for new artifacts)

**Feature Flag** (optional):
- `ENABLE_WIZARD_RESUME_MODE` - toggle re-enrich dropdown visibility
- Allows gradual rollout, A/B testing

---

## Related Documentation

- **ft-045**: Evidence Review Workflow (wizard Step 5 consolidated implementation)
- **ft-022**: Unified Wizard Pattern (wizard architecture)
- **ADR-046**: Blocking Evidence Review Workflow (decision rationale)
- **spec-frontend.md**: Frontend architecture and patterns
- **spec-api.md**: API endpoint specifications

---

