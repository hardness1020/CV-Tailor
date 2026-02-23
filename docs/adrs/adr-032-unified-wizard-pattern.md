# ADR — Unified Full-Page Wizard Pattern for Multi-Step Workflows

**Status:** Draft → Accepted (upon implementation completion)
**Date:** 2025-10-24
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-NEXT unified-wizard-pattern

## Context and Problem Statement

The application currently uses inconsistent UI patterns for multi-step workflows:

1. **Artifact Upload:** Modal overlay on `/artifacts` page
   - 4-step wizard (Basic Info → Technologies → Evidence → Review)
   - Centered card with background blur
   - Self-contained 1,230-line component

2. **CV Generation:** Full-page takeover on `/generate` page
   - 5-step workflow (Job Analysis → Artifacts → Customize → Bullets → Complete)
   - Immersive full-page experience
   - Self-contained 977-line component

**Problems with Current Approach:**

- **UX Inconsistency:** Users encounter different patterns for similar tasks (multi-step data collection)
- **Perception Gap:** Modal feels informal/casual; full-page feels professional/important
- **Cognitive Load:** Different navigation patterns require learning two mental models
- **Accessibility Challenges:** Modal has cramped space for accessibility features (focus traps, step indicators)
- **Code Duplication:** Both flows implement custom step management, progress tracking, validation
- **Maintenance Burden:** Changes to wizard UX require updating multiple components
- **Scalability Issues:** Adding new multi-step flows requires building wizard infrastructure from scratch

**User Feedback:**
> "The modal upload feels too casual/informal for this important action" (User testing feedback)

**We need to decide:**

1. **Which pattern to standardize on:** Modal overlay vs. full-page vs. hybrid
2. **How to share code:** Reusable component vs. copy-paste vs. abstraction library
3. **Cancellation UX:** When to show confirmation dialogs for unsaved changes
4. **Mobile strategy:** Same pattern for desktop and mobile or adaptive patterns
5. **Accessibility approach:** Minimum WCAG level and implementation strategy

## Decision Drivers

- **Professional UX:** Application should feel trustworthy and premium (S-Tier SaaS quality)
- **Consistency:** Unified patterns reduce cognitive load and improve learnability
- **Accessibility:** WCAG 2.1 AA compliance without compromising UX
- **Developer Experience:** Reusable infrastructure accelerates future development
- **Mobile Support:** Must work gracefully on mobile devices (responsive design)
- **User Confidence:** Smart cancellation prevents accidental data loss
- **Scalability:** Support future multi-step flows (cover letter, profile setup, etc.)
- **S-Tier Design Standards:** Follow `rules/design-principles.md` (Stripe, Airbnb, Linear quality)

## Considered Options

### Option A: Keep Current Mixed Patterns (Status Quo)

**Approach:** Maintain modal for upload, full-page for CV generation

**Pros:**
- No migration effort
- Familiar to existing users
- Upload keeps page context visible

**Cons:**
- Inconsistent UX creates confusion
- Unprofessional appearance (modal feels casual)
- Code duplication continues
- Difficult to add new wizards
- Accessibility challenges in modal
- No shared infrastructure

**Estimated Effort:** 0 hours (no change)

---

### Option B: Use Modal Overlay for Both Flows

**Approach:** Convert CV generation to modal pattern like artifact upload

**Pros:**
- Maintains page context
- Faster to implement (reuse existing modal)
- User can see background

**Cons:**
- Cramped multi-step UI in modal
- Still feels informal/casual
- Limited space for accessibility features
- Poor mobile experience (modal on small screens)
- 5-step CV generation wizard too complex for modal
- Doesn't solve professionalism issue

**Estimated Effort:** 4-6 hours (convert CV generation to modal)

---

### Option C: Use Drawer/Slide-over Pattern

**Approach:** Implement drawer pattern (slides from right/bottom)

**Pros:**
- Mobile-friendly (native pattern)
- Trending design pattern
- Smooth animations

**Cons:**
- Still feels secondary/less important
- Limited width on desktop (typically max 50% screen)
- Doesn't match CV generation's immersive experience
- Less space than full-page for complex forms
- Accessibility challenges (focus management across drawer and page)

**Estimated Effort:** 8-10 hours (new drawer infrastructure + migration)

---

### Option D: Full-Page with Reusable WizardFlow Component (Recommended)

**Approach:** Standardize on full-page takeover pattern with reusable wizard infrastructure

**Pros:**
- **Professional UX:** Full-page signals importance and commands attention
- **Consistent Experience:** Same pattern for all multi-step flows
- **Immersive:** User focuses on task without distractions
- **Accessibility:** Ample space for step indicators, keyboard shortcuts, focus management
- **Mobile-Friendly:** Natural full-page experience on mobile
- **Reusable:** WizardFlow component serves all future wizards
- **Scalable:** Easy to add new multi-step flows
- **S-Tier Quality:** Matches Stripe checkout, Linear issue creation patterns

**Cons:**
- **Migration Effort:** 11-16 hours development time
- **Breaking UX Change:** Existing users need brief adjustment
- **Context Loss:** User can't see artifacts list during upload (mitigated by smart cancellation)

**Estimated Effort:** 11-16 hours (build WizardFlow + migrate both flows + test)

---

### Option E: Hybrid Pattern with Context Toggle

**Approach:** Full-page wizard with optional "Show Background" toggle

**Pros:**
- Best of both worlds
- User choice (power users can toggle)

**Cons:**
- Adds complexity (two UI modes to test)
- Dilutes consistency (users still see two patterns)
- More code to maintain
- Confusing for new users (which mode to use?)
- Over-engineering for limited benefit

**Estimated Effort:** 15-20 hours (complex implementation)

## Decision Outcome

**Chosen Option: Option D - Full-Page with Reusable WizardFlow Component**

### Rationale

1. **Professional Perception:** Full-page takeover signals that artifact upload is as important as CV generation, creating trust and confidence

2. **UX Consistency:** Unified pattern across all multi-step flows reduces cognitive load and improves learnability

3. **Accessibility Excellence:** Full-page provides ample space for:
   - Clear step indicators with labels and icons
   - Keyboard shortcuts (ESC, Ctrl+Enter, Ctrl+←/→)
   - Focus management without cross-component complexity
   - WCAG 2.1 AA compliance without compromise

4. **Developer Efficiency:** Reusable WizardFlow component means:
   - Future wizards take 25% less time to build
   - Consistent behavior across all flows
   - Centralized improvements benefit all wizards
   - Easier onboarding for new developers

5. **Mobile Experience:** Full-page is natural on mobile (no cramped modals or drawers)

6. **S-Tier Design Standards:** Matches industry-leading patterns:
   - **Stripe Checkout:** Full-page payment flow with step indicators
   - **Linear Issue Creation:** Immersive full-page wizard
   - **Airbnb Listing Creation:** Multi-step full-page experience

7. **Smart Cancellation:** Unsaved changes detection prevents accidental data loss:
   - No changes → Exit immediately (no confirmation)
   - Changes detected → Show summary with clear choice (Keep Editing / Discard & Exit)

8. **Reasonable Migration Cost:** 11-16 hours is justified by:
   - Long-term maintenance savings (DRY principle)
   - Improved user experience
   - Faster future development

### Architecture Decision

**Component Structure:**
```typescript
// Reusable wizard infrastructure
WizardFlow (container)
  ├── WizardStepIndicator (progress visualization)
  └── Step Content (rendered as children)

// State management
useWizardProgress (hook)
  ├── Tracks touched/completed steps
  ├── Calculates completion percentage
  └── Detects unsaved changes

// Smart cancellation
CancelConfirmationDialog
  ├── Shows unsaved changes summary
  └── Clear action buttons
```

**Integration Pattern:**
```typescript
// Application flows (refactored)
ArtifactUploadFlow (4 steps, purple theme)
CVGenerationFlow (5 steps, blue theme)

// Both use same WizardFlow infrastructure
```

### Theme Strategy

**Visual Consistency with Distinction:**
- **Upload Flow:** Purple gradient (`from-purple-50 to-pink-50`)
- **CV Generation:** Blue gradient (`from-blue-50 to-indigo-50`)
- **Custom Flows:** Support custom gradients via props

This maintains visual identity while ensuring structural consistency.

## Consequences

### Positive

1. **Improved UX:**
   - Professional, trustworthy appearance
   - Consistent interaction patterns
   - Clear progress visualization
   - No accidental data loss (smart cancellation)

2. **Better Accessibility:**
   - WCAG 2.1 AA compliant
   - Keyboard navigation (Tab, Enter, ESC, Ctrl+shortcuts)
   - Screen reader friendly (ARIA labels, live regions)
   - High color contrast (4.5:1 for text)
   - Focus management without complexity

3. **Developer Benefits:**
   - Reusable WizardFlow reduces code duplication
   - Consistent patterns easier to maintain
   - New wizards faster to build (25% time savings)
   - Centralized improvements benefit all flows
   - Clear separation of concerns (container vs. content)

4. **Mobile Experience:**
   - Natural full-page flow on small screens
   - Touch-friendly buttons (min 44px height)
   - Responsive design at all breakpoints
   - No awkward modal sizing

5. **Business Value:**
   - Higher completion rates (better UX = less abandonment)
   - Fewer support tickets (consistent UX = less confusion)
   - Faster feature velocity (reusable infrastructure)
   - Premium brand perception (S-Tier design quality)

### Negative

1. **Breaking UX Change:**
   - **Impact:** Existing users familiar with modal upload will see different pattern
   - **Mitigation:**
     - In-app tooltip on first use: "New streamlined upload experience"
     - Monitor analytics for completion rate changes
     - Quick rollback path if major issues detected

2. **Development Cost:**
   - **Impact:** 11-16 hours to build infrastructure + migrate + test
   - **Mitigation:**
     - Phased rollout: Build foundation → Migrate upload → Align CV generation
     - Feature flag for gradual rollout to users
     - ROI positive after 3-4 new wizard implementations

3. **Context Loss:**
   - **Impact:** Users can't see artifacts list while uploading
   - **Mitigation:**
     - Smart "Back" navigation returns to exact scroll position
     - Upload confirmation includes link to view uploaded artifact
     - Future: Add "View Artifacts" link in wizard if needed

4. **Testing Burden:**
   - **Impact:** Visual regression tests for both flows across all breakpoints
   - **Mitigation:**
     - Automated Playwright tests for critical paths
     - Reusable test utilities for wizard flows
     - One-time investment, ongoing value

### Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| User confusion from UX change | Medium | Medium | In-app tooltip, monitor analytics, quick rollback |
| Performance regression (bundle size) | Low | Low | Code splitting, lazy loading, tree shaking |
| Accessibility issues missed | Low | High | Automated axe-core tests, manual screen reader testing |
| Mobile UX problems | Medium | Medium | Device testing (iOS/Android), responsive QA |
| Increased abandonment rates | Low | High | A/B test, gradual rollout, quick rollback plan |

## Implementation Notes

### Phase 1: Build Foundation (4-6 hours)

**Deliverables:**
- `frontend/src/components/ui/WizardFlow.tsx`
- `frontend/src/components/ui/WizardStepIndicator.tsx`
- `frontend/src/components/ui/CancelConfirmationDialog.tsx`
- `frontend/src/hooks/useWizardProgress.ts`

**Tests:**
- Unit tests for all components (>90% coverage)
- Accessibility tests (axe-core, keyboard navigation)

### Phase 2: Migrate Artifact Upload (3-4 hours)

**Changes:**
- Refactor `ArtifactUpload.tsx` → `ArtifactUploadFlow.tsx`
- Update `ArtifactsPage.tsx` routing (remove modal, add state toggle)
- Implement smart cancellation logic
- Extract step components

**Tests:**
- Integration tests (full 4-step flow)
- Visual regression (Playwright)

### Phase 3: Align CV Generation (2-3 hours)

**Changes:**
- Wrap `CVGenerationFlow.tsx` with WizardFlow
- Apply consistent theming
- Use useWizardProgress hook

**Tests:**
- Integration tests (full 5-step flow)
- Cross-flow consistency tests

### Phase 4: Polish & Validate (2-3 hours)

**Activities:**
- Add animations and micro-interactions
- Accessibility audit (WCAG 2.1 AA)
- Mobile responsive testing
- Performance optimization

**Success Criteria:**
- All tests passing
- WCAG 2.1 AA compliant
- <15KB gzipped bundle size
- 60fps animations

### Rollout Strategy

**Week 1:** Build foundation + tests
**Week 2:** Migrate artifact upload behind feature flag
**Week 3:** Internal testing + gather feedback
**Week 4:** Enable for 10% of users (canary)
**Week 5:** Full rollout (100%)

### Success Metrics

**Quantitative:**
- Upload completion rate: +15% increase (baseline TBD)
- Cancellation rate: -20% decrease (baseline TBD)
- Time to complete upload: <3 minutes average
- Error submission rate: <5%

**Qualitative:**
- User feedback (perceived professionalism): Track NPS
- Support ticket volume (confusion-related): Monitor decrease
- Developer satisfaction: Survey team on wizard infrastructure

## References

- **TECH SPEC:** `docs/specs/spec-frontend.md` (v2.4.0) - Multi-Step Wizard Component System
- **FEATURE:** `docs/features/ft-NEXT-unified-wizard-pattern.md` - Implementation plan
- **Discovery:** Stage B findings (modal vs. full-page analysis)
- **Design Standards:** `rules/design-principles.md` - S-Tier SaaS design checklist
- **Industry Patterns:**
  - Stripe Checkout: https://stripe.com/checkout (full-page payment flow)
  - Linear Issue Creation: https://linear.app (immersive wizard)
  - Airbnb Host Dashboard: https://airbnb.com/host (multi-step listing creation)

## Related Decisions

- **ADR-027:** User Context Field (consistent with professional UX theme)
- **ADR-029:** Multi-Environment Settings (supports feature flag rollout)
- **Future ADR:** Auto-save draft implementation (next iteration)

## Notes

- This ADR will transition from "Draft" to "Accepted" upon successful implementation and deployment
- Git tag: `adr-032-unified-wizard-pattern` after acceptance
- SPEC version v2.4.0 includes wizard component specifications
- All wizard components must pass WCAG 2.1 AA automated tests (axe-core)
