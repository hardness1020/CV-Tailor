# Feature — 022 Unified Wizard Pattern for Multi-Step Workflows

**File:** docs/features/ft-022-unified-wizard-pattern.md
**Owner:** Development Team
**TECH-SPECs:** `spec-frontend.md` (v2.4.0), `spec-api.md` (v4.0 - no changes)
**ADRs:** `adr-032-unified-wizard-pattern.md`
**Scope:** Medium (Multi-component UX refactor, no backend/contract changes)
**Status:** In Progress

## Existing Implementation Analysis

### Similar Features Identified

**Current Multi-Step Workflows:**
1. **Artifact Upload** (`frontend/src/components/ArtifactUpload.tsx` - 1,230 lines)
   - Pattern: Modal overlay on `/artifacts` page
   - Steps: 4 (Basic Info → Technologies → Evidence → Review)
   - Theme: Purple gradient
   - Navigation: URL param trigger (`?action=upload`)
   - Progress: Custom step indicator (numbered pills)
   - Validation: react-hook-form + zod

2. **CV Generation** (`frontend/src/components/CVGenerationFlow.tsx` - 977 lines)
   - Pattern: Full-page takeover on `/generate` page
   - Steps: 5 (Job Analysis → Artifacts → Customize → Bullets → Complete)
   - Theme: Blue gradient
   - Navigation: State-based toggle
   - Progress: Custom step indicator with animations
   - Validation: react-hook-form + zod

**Key Discovery:**
- ❌ No shared wizard infrastructure exists
- ✅ Both use react-hook-form for validation (can reuse pattern)
- ✅ Both use similar step management logic (can extract to hook)
- ✅ Both use Radix UI + Lucide icons (consistent dependencies)
- ⚠️ Inconsistent UX: Modal vs. full-page creates confusion

### Reusable Components Found

**Form Management:**
- `react-hook-form` - Already used in both flows
- `zod` - Schema validation (existing pattern)
- `@hookform/resolvers/zod` - Integration layer

**UI Components:**
- `@radix-ui/react-tabs` - For tabbed interfaces
- `lucide-react` icons - FileText, Code, Lightbulb, CheckCircle, ArrowLeft, ArrowRight, X, Check
- `frontend/src/components/ui/Button.tsx` - Reusable button component
- `frontend/src/components/ui/Input.tsx` - Form input component
- `frontend/src/components/ui/Modal.tsx` - Base modal (used in current upload)

**Patterns to Follow:**
- S-Tier SaaS design from `rules/design-principles.md`
- Gradient backgrounds (already used in both flows)
- Step indicators with progress visualization
- Keyboard navigation (Tab, Enter, ESC)
- WCAG 2.1 AA accessibility standards

### Code to Consolidate

**Duplicate Logic Identified:**
1. **Step Management:**
   - Both flows track `currentStep` state
   - Both implement `handleNext()` / `handleBack()` functions
   - Both validate current step before proceeding
   - **Solution:** Extract to `useWizardProgress` hook

2. **Progress Tracking:**
   - Both calculate completion percentage
   - Both track touched/completed steps
   - **Solution:** Centralize in `useWizardProgress`

3. **Step Indicators:**
   - Both render custom progress pills
   - Both use numbered/icon-based indicators
   - Both show completed state with checkmarks
   - **Solution:** Create `WizardStepIndicator` component

4. **Cancellation Logic:**
   - Artifact upload: Close modal without confirmation
   - CV generation: Close with setState
   - Neither detects unsaved changes
   - **Solution:** Smart `CancelConfirmationDialog` with change detection

### Architecture Conformance

**Layer Assignment:**
- **UI Components Layer:**
  - `WizardFlow` - Container component (`frontend/src/components/ui/`)
  - `WizardStepIndicator` - Progress visualization (`frontend/src/components/ui/`)
  - `CancelConfirmationDialog` - Exit confirmation (`frontend/src/components/ui/`)

- **Hooks Layer:**
  - `useWizardProgress` - State management (`frontend/src/hooks/`)

- **Page/Flow Layer:**
  - `ArtifactUploadFlow` - Refactored upload flow (`frontend/src/components/`)
  - `CVGenerationFlow` - Refactored CV flow (existing location)

**Pattern Compliance:**
- ✅ Follows existing component structure (ui/ for reusable, components/ for flows)
- ✅ Uses established design tokens (Tailwind utilities, gradient classes)
- ✅ Implements accessibility standards (ARIA labels, keyboard navigation)
- ✅ Uses Radix UI patterns (consistent with existing codebase)
- ✅ State management via custom hooks (similar to useAuth pattern)

**Dependencies:**
- ✅ All required packages already installed (no new dependencies)
- ✅ No API changes required (frontend-only refactor)
- ✅ No backend changes needed
- ✅ No database migrations required

### Dependencies on Existing Services

- **react-hook-form**: Form state and validation
- **zod**: Schema validation
- **lucide-react**: Icons for step indicators
- **@radix-ui/react-tabs**: Accessible UI primitives (optional, for future enhancements)
- **Tailwind CSS**: Styling and animations

## Acceptance Criteria

### 1. WizardFlow Component

#### 1.1 Component Creation
- [ ] Create `frontend/src/components/ui/WizardFlow.tsx`
- [ ] Implements WizardFlowProps interface (TypeScript strict mode)
- [ ] Exports WizardFlow and WizardStep type
- [ ] Has comprehensive JSDoc comments

#### 1.2 Layout and Styling
- [ ] Full-page takeover (min-h-screen)
- [ ] Gradient background based on theme prop
- [ ] Purple theme: `from-purple-50 to-pink-50`
- [ ] Blue theme: `from-blue-50 to-indigo-50`
- [ ] Custom theme: Accepts customGradient prop
- [ ] Responsive design (mobile/tablet/desktop breakpoints)
- [ ] Max-width container (max-w-4xl) centered with padding

#### 1.3 Close Button
- [ ] Top-right X button always visible
- [ ] Calls onCancel prop when clicked
- [ ] Clear hover state (bg-white/50 opacity)
- [ ] Accessible (aria-label="Close wizard")
- [ ] Keyboard accessible (Tab, Enter, ESC)

#### 1.4 Step Indicator Integration
- [ ] Renders WizardStepIndicator component
- [ ] Passes steps, currentStep, onStepChange props
- [ ] Positioned below title, above content area
- [ ] Responsive spacing (mb-8)

#### 1.5 Content Area
- [ ] White background card (bg-white)
- [ ] Rounded corners (rounded-2xl)
- [ ] Box shadow (shadow-xl)
- [ ] Border (border-gray-200)
- [ ] Padding (p-8)
- [ ] Renders children content
- [ ] Minimum height for consistency (min-h-[600px])

#### 1.6 Accessibility
- [ ] Role="dialog" on container
- [ ] aria-labelledby pointing to title
- [ ] aria-modal="true"
- [ ] Focus trap when opened
- [ ] ESC key closes wizard (triggers onCancel)

---

### 2. WizardStepIndicator Component

#### 2.1 Component Creation
- [ ] Create `frontend/src/components/ui/WizardStepIndicator.tsx`
- [ ] Implements WizardStepIndicatorProps interface
- [ ] Exports component

#### 2.2 Step Pills Rendering
- [ ] Renders all steps from steps prop
- [ ] Horizontal layout on desktop (flex-row)
- [ ] Vertical layout on mobile (flex-col, sm:flex-row)
- [ ] Connecting lines between steps
- [ ] Lines turn green when step completed

#### 2.3 Step States
- [ ] **Active step:** Purple/blue background, white icon, scale(1.1), shadow-lg
- [ ] **Completed step:** Green background (bg-green-500), checkmark icon
- [ ] **Pending step:** Gray background (bg-gray-200), gray icon (text-gray-500)
- [ ] **Optional step:** Badge or indicator showing "(Optional)"

#### 2.4 Step Interaction
- [ ] Steps are clickable buttons (if onStepClick provided)
- [ ] Disabled states for inaccessible steps
- [ ] Hover states for clickable steps
- [ ] Active step non-clickable (cursor-default)

#### 2.5 Icons
- [ ] Renders step.icon for pending/active steps
- [ ] Renders Check icon for completed steps
- [ ] Icon size: w-6 h-6
- [ ] Icons centered in pill

#### 2.6 Labels
- [ ] Step labels below pills on desktop
- [ ] Hidden on mobile (<640px)
- [ ] Font size: text-sm
- [ ] Active step: Bold + colored text
- [ ] Pending step: Gray text

#### 2.7 Animations
- [ ] Step transitions: 300ms ease-in-out
- [ ] Scale animation on active step
- [ ] Checkmark animation: 400ms spring
- [ ] Connector line fill: 200ms ease-out

#### 2.8 Accessibility
- [ ] role="tab" on each step button
- [ ] aria-label with step number and name
- [ ] aria-current="step" on active step
- [ ] aria-disabled on inaccessible steps
- [ ] Keyboard navigation (Tab, Arrow keys)

---

### 3. useWizardProgress Hook

#### 3.1 Hook Creation
- [ ] Create `frontend/src/hooks/useWizardProgress.ts`
- [ ] Implements UseWizardProgressReturn interface
- [ ] Accepts totalSteps and optional formMethods params

#### 3.2 State Management
- [ ] Tracks currentStep (number, 1-indexed)
- [ ] Tracks touchedSteps (Set<number>)
- [ ] Tracks completedSteps (Set<number>)
- [ ] Tracks formData (Record<string, any>)

#### 3.3 Computed Values
- [ ] isFormTouched: Returns true if formMethods.formState.isDirty OR touchedSteps.size > 0
- [ ] completionPercentage: (completedSteps.size / totalSteps) * 100

#### 3.4 Methods
- [ ] markStepTouched(step): Adds step to touchedSteps Set
- [ ] markStepCompleted(step): Adds step to completedSteps Set
- [ ] updateFormData(stepData): Merges stepData into formData
- [ ] reset(): Resets all state to initial values

#### 3.5 React Hook Form Integration
- [ ] If formMethods provided, reads formState.isDirty
- [ ] Automatically marks current step as touched on form interaction
- [ ] No integration errors if formMethods not provided

#### 3.6 State Persistence (Future)
- [ ] Optional: Save to localStorage with key prefix
- [ ] Optional: Restore on mount
- [ ] Not required for MVP

---

### 4. CancelConfirmationDialog Component

#### 4.1 Component Creation
- [ ] Create `frontend/src/components/ui/CancelConfirmationDialog.tsx`
- [ ] Implements CancelConfirmationDialogProps interface
- [ ] Exports component

#### 4.2 Smart Detection Logic
- [ ] If isOpen=false, render null
- [ ] If no changes (isFormTouched=false, touchedSteps=0), do not show
- [ ] If changes detected, show dialog with summary

#### 4.3 Dialog Layout
- [ ] Fixed overlay (bg-black/50)
- [ ] Centered modal (max-w-md)
- [ ] White background (bg-white)
- [ ] Rounded corners (rounded-xl)
- [ ] Shadow (shadow-2xl)
- [ ] Padding (p-6)

#### 4.4 Content
- [ ] **Warning icon:** AlertTriangle from lucide-react (amber-600)
- [ ] **Title:** "Unsaved Changes" (text-lg font-semibold)
- [ ] **Message:** "You have unsaved changes in Step X of Y."
- [ ] **Changes summary list:**
  - Number of fields filled (from formData)
  - Current step progress
  - Completed steps count
- [ ] Renders as bulleted list (list-disc)

#### 4.5 Action Buttons
- [ ] **"Keep Editing" button:**
  - Gray background (bg-gray-100)
  - Text color (text-gray-700)
  - Calls onCancel()
  - Primary visual emphasis
- [ ] **"Discard & Exit" button:**
  - Red background (bg-red-600)
  - White text (text-white)
  - Calls onConfirm()
  - Danger styling
- [ ] Buttons side-by-side (flex gap-3)
- [ ] Full width each (flex-1)

#### 4.6 Accessibility
- [ ] role="alertdialog"
- [ ] aria-labelledby pointing to title
- [ ] aria-describedby pointing to message
- [ ] Focus trapped within dialog
- [ ] ESC key triggers onCancel
- [ ] Focus on "Keep Editing" button on open
- [ ] Restore focus to trigger element on close

---

### 5. ArtifactUploadFlow Refactoring

#### 5.1 File Creation
- [ ] Create `frontend/src/components/ArtifactUploadFlow.tsx`
- [ ] Move logic from ArtifactUpload.tsx (1,230 lines)
- [ ] Reduce to ~600 lines by using WizardFlow

#### 5.2 WizardFlow Integration
- [ ] Wraps all content with <WizardFlow>
- [ ] Passes title="Upload Work Artifact"
- [ ] Passes steps array (4 steps)
- [ ] Passes currentStep state
- [ ] Passes onStepChange handler
- [ ] Passes onCancel handler (smart cancellation)
- [ ] Sets gradientTheme="purple"

#### 5.3 Step Definitions
- [ ] Step 1: Basic Info (FileText icon)
  - Title, description, start_date, end_date
- [ ] Step 2: Technologies (Code icon)
  - Tag input for technologies array
- [ ] Step 3: Evidence (Lightbulb icon)
  - File upload (PDF) OR GitHub URL
  - Multiple evidence items supported
- [ ] Step 4: Review (CheckCircle icon)
  - Summary cards for all data
  - Edit buttons to return to steps
  - Submit button

#### 5.4 Form State Management
- [ ] useForm from react-hook-form
- [ ] Zod schema validation
- [ ] useWizardProgress hook integration
- [ ] markStepTouched on form interaction
- [ ] markStepCompleted on successful validation

#### 5.5 Smart Cancellation
- [ ] handleCancel checks isFormTouched
- [ ] If touched, show CancelConfirmationDialog
- [ ] If not touched, call onCancel immediately
- [ ] CancelConfirmationDialog passes progress state

#### 5.6 Step Navigation
- [ ] Back button (ArrowLeft icon) on steps 2-4
- [ ] Next button (ArrowRight icon) on steps 1-3
- [ ] Submit button on step 4
- [ ] Validation before allowing next step
- [ ] Keyboard shortcuts (Ctrl+←, Ctrl+→)

#### 5.7 Step Content Components
- [ ] Extract BasicInfoStep into sub-component
- [ ] Extract TechnologiesStep into sub-component
- [ ] Extract EvidenceStep into sub-component
- [ ] Extract ReviewStep into sub-component
- [ ] Each component receives formMethods via props

---

### 6. ArtifactsPage Routing Update

#### 6.1 Remove Modal Pattern
- [ ] Remove `showUpload` modal overlay code
- [ ] Remove URL param trigger logic (`?action=upload`)
- [ ] Remove backdrop and centered modal wrapper

#### 6.2 Add Full-Page Toggle
- [ ] Add `showUploadFlow` state (boolean)
- [ ] If showUploadFlow=true, render <ArtifactUploadFlow />
- [ ] If showUploadFlow=false, render artifacts list
- [ ] No URL params needed (state-based like CV generation)

#### 6.3 Upload Button
- [ ] "Upload Artifact" button triggers setShowUploadFlow(true)
- [ ] Button maintains existing styling
- [ ] Accessible (aria-label, keyboard support)

#### 6.4 Completion Handler
- [ ] handleUploadComplete receives new artifact data
- [ ] Calls setShowUploadFlow(false)
- [ ] Refreshes artifacts list
- [ ] Shows success toast
- [ ] Auto-scrolls to new artifact (optional)

---

### 7. CVGenerationFlow Refactoring

#### 7.1 WizardFlow Wrapper
- [ ] Wrap existing flow with <WizardFlow>
- [ ] Set title="Generate Tailored CV"
- [ ] Set gradientTheme="blue"
- [ ] Pass 5 steps to steps prop
- [ ] Integrate useWizardProgress hook

#### 7.2 Step Consistency
- [ ] Ensure same step indicator style as upload
- [ ] Use same keyboard shortcuts
- [ ] Use same cancellation pattern
- [ ] Maintain existing functionality

#### 7.3 Code Reduction
- [ ] Extract step indicator logic to WizardFlow
- [ ] Remove duplicate progress tracking
- [ ] Reduce from 977 lines to ~600 lines

---

### 8. Accessibility Compliance (WCAG 2.1 AA)

#### 8.1 Keyboard Navigation
- [ ] Tab navigates between interactive elements
- [ ] Enter activates buttons
- [ ] Space toggles checkboxes/radios
- [ ] ESC closes wizard (with confirmation)
- [ ] Ctrl+Enter proceeds to next step (if valid)
- [ ] Ctrl+← goes to previous step
- [ ] Ctrl+→ goes to next step

#### 8.2 ARIA Labels
- [ ] All buttons have aria-label
- [ ] Step indicators have aria-current="step"
- [ ] Dialog has role="alertdialog"
- [ ] Wizard has role="dialog"
- [ ] Form fields have associated labels

#### 8.3 Focus Management
- [ ] Focus trapped in dialog when open
- [ ] Focus restored to trigger on close
- [ ] Visible focus indicators (2px blue ring)
- [ ] Focus visible on all interactive elements
- [ ] No focus lost during step transitions

#### 8.4 Color Contrast
- [ ] Text on backgrounds: 4.5:1 minimum
- [ ] UI components: 3:1 minimum
- [ ] Active states clearly visible
- [ ] Disabled states indicated beyond color (opacity)

#### 8.5 Screen Reader Support
- [ ] Step changes announced (aria-live)
- [ ] Dialog open/close announced
- [ ] Form errors announced
- [ ] Progress updates announced

---

### 9. Responsive Design

#### 9.1 Mobile (<640px)
- [ ] Vertical step indicator (stacked)
- [ ] Full-width content cards
- [ ] Touch-friendly buttons (min 44px height)
- [ ] Simplified animations (prefers-reduced-motion)
- [ ] No horizontal scroll

#### 9.2 Tablet (640-1024px)
- [ ] Horizontal compact step pills
- [ ] 2-column layouts where applicable
- [ ] Moderate spacing
- [ ] Touch-friendly (44px touch targets)

#### 9.3 Desktop (>1024px)
- [ ] Full horizontal step indicators with labels
- [ ] Spacious layouts (max-w-4xl)
- [ ] Enhanced animations
- [ ] Hover states on all interactive elements

---

### 10. Animations and Micro-Interactions

#### 10.1 Step Transitions
- [ ] Fade-in animation (opacity 0 → 1)
- [ ] Slide animation (translateX 20px → 0)
- [ ] Duration: 300ms
- [ ] Timing: ease-in-out

#### 10.2 Progress Indicators
- [ ] Active step scale(1.1) with shadow
- [ ] Completed checkmark spring animation (400ms)
- [ ] Connector line fill transition (200ms)

#### 10.3 Buttons
- [ ] Hover state transitions (150ms)
- [ ] Active state (scale 0.98)
- [ ] Disabled state (opacity 0.5, cursor-not-allowed)

#### 10.4 Dialog
- [ ] Fade-in backdrop (200ms)
- [ ] Scale-in dialog (0.95 → 1, 200ms)
- [ ] Fade-out on close (200ms)

#### 10.5 Performance
- [ ] All animations 60fps (no jank)
- [ ] GPU-accelerated (transform, opacity only)
- [ ] Respects prefers-reduced-motion

---

### 11. Testing Requirements

#### 11.1 Unit Tests (>90% coverage)

**WizardFlow.test.tsx:**
- [ ] Renders with correct title
- [ ] Renders step indicator
- [ ] Renders children content
- [ ] Applies correct gradient theme
- [ ] Calls onCancel when close button clicked
- [ ] Calls onCancel on ESC key
- [ ] Responsive design (mobile/tablet/desktop snapshots)

**WizardStepIndicator.test.tsx:**
- [ ] Renders all steps
- [ ] Shows active step correctly
- [ ] Shows completed steps with checkmarks
- [ ] Shows pending steps grayed out
- [ ] Calls onStepClick when step clicked
- [ ] Disables inaccessible steps
- [ ] Renders connector lines
- [ ] Animations trigger correctly

**useWizardProgress.test.ts:**
- [ ] Initializes with default state
- [ ] Tracks touched steps correctly
- [ ] Tracks completed steps correctly
- [ ] Calculates completion percentage
- [ ] Detects form changes via formMethods
- [ ] Updates formData on updateFormData call
- [ ] Resets state on reset call

**CancelConfirmationDialog.test.tsx:**
- [ ] Renders when isOpen=true
- [ ] Does not render when isOpen=false
- [ ] Shows changes summary
- [ ] Calls onConfirm when "Discard & Exit" clicked
- [ ] Calls onCancel when "Keep Editing" clicked
- [ ] Closes on ESC key (calls onCancel)
- [ ] Focuses "Keep Editing" button on open

#### 11.2 Integration Tests

**ArtifactUploadFlow.integration.test.tsx:**
- [ ] Completes full 4-step flow without errors
- [ ] Validates each step before proceeding
- [ ] Shows cancel dialog when exiting with changes
- [ ] Submits data correctly on completion
- [ ] Handles errors gracefully
- [ ] Keyboard navigation works (Ctrl+←, Ctrl+→, Enter)

**CVGenerationFlow.integration.test.tsx:**
- [ ] Completes full 5-step flow without errors
- [ ] Uses WizardFlow wrapper correctly
- [ ] Consistent UX with upload flow

#### 11.3 Visual Regression Tests (Playwright)

**Desktop (1440px):**
- [ ] Upload flow - all 4 steps
- [ ] CV generation flow - all 5 steps
- [ ] Cancel dialog
- [ ] Step transitions

**Tablet (768px):**
- [ ] Upload flow step 1
- [ ] Compact step indicator

**Mobile (375px):**
- [ ] Vertical step indicator
- [ ] Touch-friendly buttons

#### 11.4 Accessibility Tests

**Automated (axe-core):**
- [ ] WCAG 2.1 AA compliance
- [ ] No critical or serious issues
- [ ] Color contrast passing

**Manual Testing:**
- [ ] Keyboard navigation (all shortcuts work)
- [ ] Screen reader (NVDA) announces correctly
- [ ] Focus management works
- [ ] Tab order logical

---

### 12. Performance Targets

#### 12.1 Bundle Size
- [ ] Wizard system <15KB gzipped
- [ ] Code splitting for wizard flows
- [ ] Tree shaking removes unused code

#### 12.2 Runtime Performance
- [ ] <100ms response to user interactions
- [ ] 60fps animations (no dropped frames)
- [ ] <300ms form validation
- [ ] <50ms state updates (useWizardProgress)

#### 12.3 Loading Performance
- [ ] Lazy load wizard components
- [ ] First render <100ms
- [ ] No layout shift (CLS = 0)

---

## Design Changes

### UI Layout Changes

#### Before: Artifact Upload (Modal Pattern)

```
┌────────────────────── Artifacts Page ──────────────────────┐
│  [Artifacts] [Generate CV] [Profile]                 [User]│
│                                                             │
│  🔍 Search...                      [+ Upload Artifact]     │
│                                                             │
│  ┌─────────────┬─────────────┬─────────────┐              │
│  │ Artifact 1  │ Artifact 2  │ Artifact 3  │              │
│  └─────────────┴─────────────┴─────────────┘              │
│          │ Modal Overlay (on click Upload)                 │
│          ↓                                                  │
│  ╔═══════════════════════════════════════════╗            │
│  ║  ✖  Upload Work Artifact                  ║            │
│  ║                                            ║            │
│  ║  Step 1: Basic Info  [•○○○]               ║            │
│  ║  ┌────────────────────────────────────┐   ║            │
│  ║  │ Title: _________________           │   ║            │
│  ║  │ Description: __________            │   ║            │
│  ║  └────────────────────────────────────┘   ║            │
│  ║                  [Back]  [Next →]          ║            │
│  ╚═══════════════════════════════════════════╝            │
│  └─────── Background blurred ──────┘                       │
└─────────────────────────────────────────────────────────────┘
```

#### After: Artifact Upload (Full-Page Pattern)

```
┌─────────────── ArtifactUploadFlow (Full-Page) ─────────────┐
│  Upload Work Artifact                                    ✖  │
│                                                             │
│  ● ━━━━ ○ ━━━━ ○ ━━━━ ○                                   │
│  Basic Info   Tech   Evidence   Review                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Step 1: Basic Information                           │  │
│  │                                                       │  │
│  │  Title *                                              │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ My Project Title                                │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                                                       │  │
│  │  Description                                          │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ Brief description...                            │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                                                       │  │
│  │                                          [Next →]     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### CV Generation Flow (After - Wrapped with WizardFlow)

```
┌────────────── CVGenerationFlow (Full-Page) ────────────────┐
│  Generate Tailored CV                                    ✖  │
│                                                             │
│  ● ━━━━ ○ ━━━━ ○ ━━━━ ○ ━━━━ ○                            │
│  Job   Artifacts   Customize   Bullets   Complete          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Step 1: Job Description Analysis                    │  │
│  │  [Consistent layout with upload flow]                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Cancel Confirmation Dialog

```
┌─────────────────────────────────────────────────────────────┐
│  [Background blurred with black overlay 50% opacity]        │
│                                                             │
│          ┌────────────────────────────────────┐            │
│          │  ⚠️  Unsaved Changes               │            │
│          │                                    │            │
│          │  You have unsaved changes in       │            │
│          │  Step 2 of 4. Are you sure you     │            │
│          │  want to exit?                     │            │
│          │                                    │            │
│          │  • 5 fields filled                 │            │
│          │  • 1 of 4 steps completed          │            │
│          │                                    │            │
│          │  [Keep Editing] [Discard & Exit]   │            │
│          └────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure Changes

**Before:**
```
frontend/src/components/
├── ArtifactUpload.tsx (1,230 lines - self-contained)
├── CVGenerationFlow.tsx (977 lines - self-contained)
└── ui/
    ├── Button.tsx
    ├── Input.tsx
    └── Modal.tsx
```

**After:**
```
frontend/src/components/
├── ArtifactUploadFlow.tsx (~600 lines - uses WizardFlow)
├── CVGenerationFlow.tsx (~600 lines - uses WizardFlow)
└── ui/
    ├── WizardFlow.tsx (NEW - ~200 lines)
    ├── WizardStepIndicator.tsx (NEW - ~150 lines)
    ├── CancelConfirmationDialog.tsx (NEW - ~100 lines)
    ├── Button.tsx
    ├── Input.tsx
    └── Modal.tsx

frontend/src/hooks/
└── useWizardProgress.ts (NEW - ~150 lines)
```

**Code Reduction:**
- Before: 2,207 lines (1,230 + 977)
- After: 1,800 lines (600 + 600 + 200 + 150 + 100 + 150)
- **Net reduction: 407 lines (18% less code)**
- **Reusability gain:** 4 reusable components for future wizards

---

## Test & Evaluation Plan

### Test Coverage Targets

| Component | Unit Tests | Integration Tests | E2E Tests | Total Coverage |
|-----------|------------|-------------------|-----------|----------------|
| WizardFlow | >90% | N/A | N/A | >90% |
| WizardStepIndicator | >90% | N/A | N/A | >90% |
| CancelConfirmationDialog | >90% | N/A | N/A | >90% |
| useWizardProgress | >95% | N/A | N/A | >95% |
| ArtifactUploadFlow | >85% | Full flow | Critical paths | >90% |
| CVGenerationFlow | >85% | Full flow | Critical paths | >90% |

### Test Execution Order (TDD Workflow)

**Phase 1: RED (Failing Tests) - Stage F**
1. WizardFlow.test.tsx - Write failing tests
2. WizardStepIndicator.test.tsx - Write failing tests
3. useWizardProgress.test.ts - Write failing tests
4. CancelConfirmationDialog.test.tsx - Write failing tests
5. **Verify all tests FAIL** with NotImplementedError

**Phase 2: GREEN (Pass Tests) - Stage G**
1. Implement WizardFlow component - Tests pass
2. Implement WizardStepIndicator - Tests pass
3. Implement useWizardProgress hook - Tests pass
4. Implement CancelConfirmationDialog - Tests pass
5. **Verify all unit tests PASS** (>90% coverage)

**Phase 3: REFACTOR + Integration - Stage H**
1. Write ArtifactUploadFlow.integration.test.tsx
2. Refactor ArtifactUpload → ArtifactUploadFlow
3. Write CVGenerationFlow.integration.test.tsx
4. Refactor CVGenerationFlow wrapper
5. Run visual regression tests (Playwright)
6. Run accessibility tests (axe-core)
7. **Verify all tests PASS** with no regressions

### Success Metrics

**Quantitative:**
- [ ] Upload completion rate: +15% increase (baseline: TBD in production)
- [ ] Cancellation rate: -20% decrease (baseline: TBD)
- [ ] Average time to complete upload: <3 minutes
- [ ] Error submission rate: <5%
- [ ] Bundle size: Wizard system <15KB gzipped
- [ ] Performance: <100ms interaction response, 60fps animations

**Qualitative:**
- [ ] User feedback: Perceived professionalism improved (NPS survey)
- [ ] Support tickets: Confusion-related tickets decrease
- [ ] Developer satisfaction: Team survey on wizard infrastructure ease-of-use
- [ ] Accessibility: WCAG 2.1 AA compliant (axe-core passing)

### Test Automation

**CI/CD Pipeline:**
```yaml
# .github/workflows/frontend-tests.yml
test-wizard-components:
  - Run unit tests (vitest)
  - Run integration tests (vitest + testing-library)
  - Run accessibility tests (axe-core)
  - Run visual regression (Playwright)
  - Coverage threshold: >90%
```

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking UX change confuses users** | Medium | Medium | In-app tooltip on first use, monitor analytics, quick rollback plan |
| **Performance regression (bundle size)** | Low | Low | Code splitting, lazy loading, tree shaking, <15KB target |
| **Accessibility issues missed** | Low | High | Automated axe-core tests, manual screen reader testing (NVDA/JAWS) |
| **Mobile UX problems** | Medium | Medium | Device testing (iOS Safari, Android Chrome), responsive QA checklist |
| **Increased abandonment rates** | Low | High | A/B test with 10% users, gradual rollout, quick rollback if rates spike |
| **Development time overrun** | Medium | Low | Phased approach (4 stages), time-boxed to 16 hours max |
| **Test coverage gaps** | Low | Medium | TDD workflow ensures tests written before code, coverage threshold >90% |

---

## Migration Strategy

### Rollout Plan

**Week 1: Build Foundation (Stages C-G)**
- Create TECH SPEC, ADR, FEATURE docs
- Write failing unit tests (TDD RED)
- Implement wizard components (TDD GREEN)
- Verify >90% test coverage

**Week 2: Migrate Upload Flow (Stage H - Substeps 1-2)**
- Write integration tests for ArtifactUploadFlow
- Refactor ArtifactUpload → ArtifactUploadFlow
- Update ArtifactsPage routing
- Deploy behind feature flag (`ENABLE_NEW_UPLOAD_WIZARD`)

**Week 3: Internal Testing**
- Enable for internal users (team@company.com)
- Gather feedback via survey
- Monitor analytics (completion rates, errors)
- Fix bugs and polish UX

**Week 4: Canary Release**
- Enable for 10% of production users
- Monitor success metrics (completion, cancellation, errors)
- A/B test results vs. old modal pattern
- Decision point: Proceed or rollback

**Week 5: Full Rollout**
- Enable for 100% of users
- Remove feature flag code
- Remove old ArtifactUpload.tsx component
- Monitor for 2 weeks post-rollout

### Feature Flag Configuration

```typescript
// frontend/src/config/featureFlags.ts
export const FEATURE_FLAGS = {
  ENABLE_NEW_UPLOAD_WIZARD: process.env.REACT_APP_ENABLE_NEW_UPLOAD_WIZARD === 'true',
  // ... other flags
}

// Usage in ArtifactsPage.tsx
if (FEATURE_FLAGS.ENABLE_NEW_UPLOAD_WIZARD) {
  return <ArtifactUploadFlow onComplete={handleComplete} onCancel={handleCancel} />
} else {
  return <ArtifactUpload onClose={closeUpload} /> // Old modal
}
```

### Rollback Plan

**If abandonment rate increases >10%:**
1. Disable feature flag immediately (< 5 minutes)
2. Investigate root cause (analytics, user recordings, support tickets)
3. Gather user feedback (exit surveys)
4. Iterate on issues and re-deploy with fixes
5. Re-test with 10% canary before full rollout

**Rollback Criteria:**
- Upload completion rate drops >15%
- Error rate increases >10%
- Critical accessibility issues found
- Negative user feedback >25% of responses

---

## Dependencies

**External Packages:**
- ✅ `react` (already installed)
- ✅ `react-hook-form` (already installed)
- ✅ `zod` (already installed)
- ✅ `@hookform/resolvers` (already installed)
- ✅ `lucide-react` (already installed)
- ✅ `tailwindcss` (already installed)

**Internal Dependencies:**
- ✅ `frontend/src/components/ui/Button.tsx` (existing)
- ✅ `frontend/src/components/ui/Input.tsx` (existing)
- ✅ Tailwind configuration (existing)
- ✅ Design tokens (colors, spacing, animations)

**No New Dependencies Required** ✅

---

## Success Criteria Summary

**MVP Complete When:**
- ✅ All 12 acceptance criteria sections completed
- ✅ Unit tests passing (>90% coverage)
- ✅ Integration tests passing (both flows)
- ✅ Accessibility tests passing (WCAG 2.1 AA)
- ✅ Visual regression tests passing (no unintended changes)
- ✅ Performance targets met (<15KB, 60fps, <100ms)
- ✅ Both flows (upload + CV generation) using WizardFlow
- ✅ Smart cancellation preventing data loss
- ✅ Deployed to production with monitoring

**Done Definition:**
- ✅ Code merged to main branch
- ✅ Deployed to production (100% rollout)
- ✅ Monitoring shows stable metrics (2 weeks)
- ✅ No critical bugs or accessibility issues
- ✅ User feedback neutral or positive
- ✅ Documentation updated (SPEC, ADR, FEATURE)

---

## Timeline Estimate

| Phase | Tasks | Estimated Hours | Status |
|-------|-------|----------------|--------|
| **Stage C-D** | TECH SPEC + ADR | 2-3h | ✅ Complete |
| **Stage E** | FEATURE spec + schedule | 1h | 🔄 In Progress |
| **Stage F** | Failing unit tests (TDD RED) | 2-3h | ⏳ Pending |
| **Stage G** | Implement components (TDD GREEN) | 4-6h | ⏳ Pending |
| **Stage H** | Integration + refactor + polish | 4-6h | ⏳ Pending |
| **Total** | End-to-end implementation | **13-19h** | ⏳ Pending |

**Target Completion:** 2-3 days (8-hour work days)

---

## References

- **TECH SPEC:** `docs/specs/spec-frontend.md` (v2.4.0) - Multi-Step Wizard Component System
- **ADR:** `docs/adrs/adr-032-unified-wizard-pattern.md` - Decision rationale
- **Design Standards:** `rules/design-principles.md` - S-Tier SaaS design checklist
- **TDD Workflow:** `rules/05-tdd.md` - Hybrid TDD practices
- **Workflow:** `rules/00-workflow.md` - Development pipeline stages

**Industry References:**
- Stripe Checkout: Full-page payment flow with step indicators
- Linear Issue Creation: Immersive wizard with smart exit
- Airbnb Host Dashboard: Multi-step listing creation

---

## Notes

- This is a **frontend-only refactor** - no backend or API changes
- Follows **TDD workflow** strictly (RED → GREEN → REFACTOR)
- Uses **feature flag** for gradual rollout and easy rollback
- Maintains **backward compatibility** during migration (old modal + new full-page coexist)
- Implements **WCAG 2.1 AA** accessibility from day 1 (not retrofitted)
- **Code reduction:** 18% fewer lines while adding 4 reusable components
- **Future-proof:** Wizard infrastructure supports profile setup, cover letter, onboarding flows

**Post-MVP Enhancements (Future):**
- Auto-save drafts to localStorage
- Step validation preview (show errors before clicking Next)
- Progress persistence across sessions
- Analytics tracking (step abandonment, time per step)
- Onboarding tour for first-time users
- Custom wizard themes (beyond purple/blue)
