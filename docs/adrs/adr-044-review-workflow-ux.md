# ADR-044: User Review Workflow for Low-Confidence Content

**File:** docs/adrs/adr-044-review-workflow-ux.md
**Status:** Draft
**Date:** 2025-11-04
**Decision Makers:** Engineering, Product, Design
**Related:** PRD v1.4.0, spec-llm.md v4.0.0, spec-frontend.md, ft-030-anti-hallucination-improvements.md, adr-041, adr-042, adr-043

## Context

With confidence thresholds in place (ADR-043), low-confidence content will be flagged for manual review. We need a user-friendly workflow that:

1. **Presents flagged content** clearly without disrupting the generation workflow
2. **Explains why content was flagged** (transparency about confidence/verification)
3. **Allows user decisions** (approve, reject, or edit flagged items)
4. **Provides context** (show source attribution and verification details)
5. **Respects user time** (efficient review process, not burdensome)

**Problem 1: Workflow Disruption**
- Current: User submits job → generates bullets → immediately sees results
- With flagging: Need to interrupt workflow for review without frustrating users
- Challenge: Balance quality control with user experience

**Problem 2: Information Overload**
- Users need enough info to make informed decisions
- But too much technical detail (verification JSON, confidence scores) overwhelms
- Need right level of abstraction for non-technical users

**Problem 3: Trust Calibration**
- Users must understand WHY content was flagged
- But also trust that most content is accurate (not paranoid about all bullets)
- Confidence indicators should inform, not alarm

**Current State:**
- No review workflow exists
- All content presented equally (no confidence indicators)
- No mechanism for user feedback on flagged items

**Requirements from PRD v1.4.0:**
- User acceptance rate ≥80% for flagged items
- Review workflow integrated into generation wizard
- Clear confidence indicators (visual + textual)
- Source attribution viewable by users

## Decision

Implement a **non-blocking review workflow** with visual confidence indicators and optional detailed view:

### UX Flow

```
Step 1: Generation Completes
┌────────────────────────────────────┐
│  Bullets generated successfully!  │
│  ✓ All bullets passed verification│  ← HIGH CONFIDENCE (≥0.85)
│  [View bullets]                    │
└────────────────────────────────────┘

OR

┌────────────────────────────────────┐
│  Bullets generated successfully!  │
│  ⚠ 1 bullet needs your review     │  ← LOW CONFIDENCE (0.50-0.69)
│  [Review flagged content]          │
└────────────────────────────────────┘

Step 2: Bullet List (with Confidence Indicators)
┌────────────────────────────────────────────────────────────┐
│ Bullets for Artifact: "E-commerce Platform"                │
├────────────────────────────────────────────────────────────┤
│ ✓ "Led team of 5 engineers in developing..."               │  ← HIGH
│   High confidence • Verified against sources               │
│   [View details]                                            │
├────────────────────────────────────────────────────────────┤
│ • "Implemented REST API with PostgreSQL backend..."        │  ← MEDIUM
│   Good confidence • Minor uncertainties                    │
│   [View details]                                            │
├────────────────────────────────────────────────────────────┤
│ ⚠ "Improved system performance by approximately 40%"       │  ← LOW (FLAGGED)
│   Low confidence • Percentage inferred from source         │
│   [Review required] [View source]                          │
└────────────────────────────────────────────────────────────┘

Step 3: Review Modal (for flagged item)
┌────────────────────────────────────────────────────────────┐
│ Review Bullet Point                                    [×]  │
├────────────────────────────────────────────────────────────┤
│ Bullet: "Improved system performance by approximately 40%" │
│                                                             │
│ ⚠ Why flagged: Percentage not explicitly stated in source  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Source Evidence:                                        ││
│ │ "Optimized database queries, significantly reducing     ││
│ │  response time and improving system performance"        ││
│ │                                                          ││
│ │ Source: resume.pdf, page 2, Work Experience section    ││
│ │ Confidence: 0.62 (Low) • Type: Inferred               ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Your Decision:                                              │
│ [✓ Approve] [✗ Reject] [✎ Edit]                           │
└────────────────────────────────────────────────────────────┘

Step 4: Bulk Actions (if multiple flags)
┌────────────────────────────────────────────────────────────┐
│ 2 bullets need review                                       │
│                                                             │
│ ☐ Bullet 1: "Improved performance by 40%"                  │
│    Confidence: 0.62 • Percentage inferred                  │
│                                                             │
│ ☐ Bullet 2: "Managed team of engineers"                    │
│    Confidence: 0.55 • Team size unclear                    │
│                                                             │
│ [✓ Approve All] [✗ Reject All] [Review Individually]      │
└────────────────────────────────────────────────────────────┘
```

### Visual Design System

**Confidence Indicators (Color-Coded):**

```typescript
// HIGH Confidence (≥0.85)
{
  icon: '✓',
  color: 'green-600',
  background: 'green-50',
  border: 'green-200',
  label: 'High confidence',
  message: 'Verified against sources'
}

// MEDIUM Confidence (0.70-0.84)
{
  icon: '•',
  color: 'blue-600',
  background: 'blue-50',
  border: 'blue-200',
  label: 'Good confidence',
  message: 'Minor uncertainties'
}

// LOW Confidence (0.50-0.69) - FLAGGED
{
  icon: '⚠',
  color: 'amber-600',
  background: 'amber-50',
  border: 'amber-300',
  label: 'Low confidence',
  message: 'Please review before finalizing',
  requires_action: true
}

// CRITICAL Confidence (<0.50) - BLOCKED
{
  icon: '✗',
  color: 'red-600',
  background: 'red-50',
  border: 'red-300',
  label: 'Critical issues',
  message: 'Re-generation recommended',
  blocked: true
}
```

**Component Hierarchy:**

```typescript
// BulletCard (main component)
<BulletCard
  bullet={bullet}
  confidence={0.62}
  verificationStatus="INFERRED"
  requiresReview={true}
  onApprove={() => handleApprove(bullet.id)}
  onReject={() => handleReject(bullet.id)}
  onEdit={() => handleEdit(bullet.id)}
>
  {/* Bullet text */}
  <BulletText>{bullet.text}</BulletText>

  {/* Confidence indicator */}
  <ConfidenceIndicator
    level={getConfidenceTier(0.62)}
    showDetails={true}
  />

  {/* Source attribution (collapsed by default) */}
  <Collapsible trigger="View source">
    <SourceAttribution
      quote={bullet.sourceAttribution.exact_quote}
      location={bullet.sourceAttribution.source_location}
    />
  </Collapsible>

  {/* Actions (only if flagged) */}
  {requiresReview && (
    <ReviewActions
      onApprove={onApprove}
      onReject={onReject}
      onEdit={onEdit}
    />
  )}
</BulletCard>
```

### Review Modal (Detailed View)

**Purpose:** Provide full context for flagged item without cluttering main view.

**Content:**
1. **Bullet text** (prominent display)
2. **Flagging reason** (why low confidence)
3. **Source evidence** (quote + location)
4. **Verification details** (claim-by-claim breakdown, optional accordion)
5. **Confidence score** (numeric + tier)
6. **Action buttons** (approve/reject/edit)

**Design Principles:**
- **Scannable**: Key info visible without scrolling
- **Contextual**: Show relevant source quotes, not entire document
- **Actionable**: Clear next steps (approve/reject/edit)
- **Non-judgmental**: Frame as "needs your review" not "this is wrong"

### Generation Wizard Integration

**Checkpoint After Bullet Generation:**

```typescript
// Step 3: Bullet Generation (existing)
<WizardStep title="Generate Bullets">
  <BulletGenerationForm />
</WizardStep>

// NEW: Step 3.5: Review Flagged Content (conditional)
{hasFlaggedContent && (
  <WizardStep title="Review Flagged Content">
    <ReviewInterface
      flaggedBullets={getFlaggedBullets()}
      onReviewComplete={() => setReviewComplete(true)}
    />
  </WizardStep>
)}

// Step 4: Finalize (existing)
<WizardStep title="Finalize Application">
  <FinalizeForm />
</WizardStep>
```

**Behavior:**
- If NO flagged content: Skip review step, proceed directly to finalize
- If flagged content: Insert review step, user must complete before proceeding
- Allow "Approve All" for power users who trust the system
- Persist review decisions (approved/rejected bullets stored)

### API Integration

**Frontend consumes verification metadata from backend:**

```typescript
interface BulletWithVerification {
  id: string;
  text: string;
  bulletType: 'achievement' | 'technical' | 'impact';

  // Confidence data
  confidence: number;  // 0.0-1.0
  confidenceTier: 'high' | 'medium' | 'low' | 'critical';
  requiresReview: boolean;

  // Verification data (from ADR-042)
  verificationStatus: 'VERIFIED' | 'INFERRED' | 'UNSUPPORTED';
  verificationConfidence: number;
  hallucinationRisk: 'low' | 'medium' | 'high';

  // Source attribution (from ADR-041)
  sourceAttribution: {
    sourceType: string;
    sourceLocation: string;
    exactQuote: string | null;
    attributionType: 'direct' | 'inferred';
  };

  // Claim-level details (optional, for detailed view)
  claimResults?: Array<{
    claim: string;
    status: 'VERIFIED' | 'INFERRED' | 'UNSUPPORTED';
    evidenceQuote: string | null;
    confidence: number;
  }>;
}
```

**Review Actions API:**

```typescript
// Approve flagged bullet
POST /api/generation/{generationId}/bullets/{bulletId}/approve
Response: { status: 'approved', updatedBullet: {...} }

// Reject flagged bullet
POST /api/generation/{generationId}/bullets/{bulletId}/reject
Body: { reason?: string }  // Optional feedback
Response: { status: 'rejected' }

// Edit flagged bullet
PUT /api/generation/{generationId}/bullets/{bulletId}
Body: { text: string, manuallyEdited: true }
Response: { status: 'updated', updatedBullet: {...} }

// Bulk approve
POST /api/generation/{generationId}/bullets/bulk-approve
Body: { bulletIds: string[] }
Response: { approvedCount: number }
```

## Consequences

### Positive

**User Empowerment (+++):**
- Users make informed decisions about content quality
- Transparency builds trust in the system
- Ability to approve, reject, or edit gives users control
- Educational: Users learn what constitutes high-quality evidence

**Quality Improvement (++):**
- Human review catches edge cases automation misses
- User feedback improves future flagging accuracy
- Prevents hallucinations from reaching final documents
- Target: ≥80% user acceptance rate

**Workflow Integration (+):**
- Non-blocking: Doesn't prevent users from proceeding if they choose
- Conditional: Only appears when needed (no friction for high-confidence content)
- Efficient: Bulk actions for multiple flags
- Persistent: Review decisions saved, not re-prompted

**Data Collection (+):**
- Track which flags users approve vs. reject
- Measure time spent on review
- Identify patterns in false positives
- Use data to refine confidence thresholds (ADR-043)

### Negative

**Added Complexity (-):**
- New UI components to build and maintain
- More complex generation wizard flow
- Additional API endpoints for review actions
- Testing burden (multiple code paths based on flagging)

**User Friction (-):**
- Interrupts generation workflow for flagged content
- Requires user attention and decision-making
- Risk of user fatigue if too many items flagged
- Power users may find review step tedious

**Design Challenges (--):**
- Balancing detail vs. simplicity (information density)
- Making confidence scores understandable to non-technical users
- Avoiding user alarm ("low confidence" sounds scary)
- Mobile responsiveness for complex review interface

**Performance Risk (-):**
- Review modal loads verification details (additional API call)
- Source attribution rendering (potentially long quotes)
- May slow down on low-end devices
- Need efficient lazy-loading of detailed info

## Alternatives

### Alternative 1: Blocking Workflow (Rejected)

**Idea**: Force users to review all flagged content before proceeding (modal blocks wizard).

**Rejected because**:
- Too disruptive to user experience
- Removes user agency (can't skip review if they trust system)
- Slow workflow for users with multiple flags
- Would reduce user satisfaction

### Alternative 2: Sidebar Review Panel (Considered but Deferred)

**Idea**: Keep flagged items in persistent sidebar while user reviews.

**Pros**:
- Non-modal, doesn't block main workflow
- Always accessible without opening modal
- Could show aggregate stats (X of Y reviewed)

**Cons**:
- Reduces screen real estate
- Harder to focus on detailed review
- Complex layout on mobile

**Decision**: Defer to v2. Start with modal-based review for simplicity.

### Alternative 3: Email/Notification-Based Review (Rejected)

**Idea**: Email users when flagged content needs review, let them review later.

**Rejected because**:
- Breaks in-workflow experience
- Users may forget to review
- Increases latency (wait for email, return to app)
- Doesn't meet PRD requirement for integrated workflow

### Alternative 4: Auto-Fix Attempts (Rejected)

**Idea**: Automatically re-generate flagged bullets with stricter prompts.

**Rejected because**:
- May not improve quality (same source constraints)
- Adds latency (additional LLM calls)
- Doesn't leverage human judgment
- Risk of infinite retry loops

**Note**: Could be complementary feature (offer "regenerate" as option in review modal).

## Rollback Plan

**Phase 1: Feature Flag Disable**
```typescript
if (!featureFlags.isEnabled('content_review_workflow')) {
  // Skip review step, show all bullets as approved
  return <BulletList bullets={allBullets} reviewDisabled={true} />;
}
```

**Phase 2: Hide Confidence Indicators**
```typescript
// If users confused by confidence indicators
if (!featureFlags.isEnabled('confidence_indicators')) {
  // Show bullets without confidence tiers
  return <SimpleBulletCard bullet={bullet} />;
}
```

**Phase 3: Simplify Review UI**
```typescript
// If detailed review modal too complex
if (featureFlags.isEnabled('simple_review_mode')) {
  // Show only bullet text + approve/reject (no verification details)
  return <SimpleReviewModal bullet={bullet} />;
}
```

**Rollback Triggers:**
- User completion rate drops >15% after review step added
- Average review time >2 minutes per flagged item
- >20% of users abandon generation at review step
- User complaints about workflow disruption >10% of sessions

## Implementation Notes

### Component Library (Radix UI + Tailwind)

**Reusable Components:**
- `ConfidenceBadge`: Visual indicator for confidence tiers
- `SourceAttributionCard`: Display source quotes with styling
- `ReviewActionBar`: Approve/Reject/Edit buttons with keyboard shortcuts
- `VerificationDetailsAccordion`: Expandable claim-by-claim breakdown
- `BulletReviewModal`: Full-screen modal for detailed review

**Accessibility:**
- Keyboard navigation (Tab, Enter, Escape)
- ARIA labels for confidence indicators
- Screen reader announcements for flagging status
- Focus management (auto-focus on review modal open)

### Mobile-Responsive Design

**Breakpoints:**
- Desktop (≥1024px): Full review modal with side-by-side layout
- Tablet (768-1023px): Stacked layout, collapsible sections
- Mobile (< 768px): Bottom sheet modal, simplified view

**Touch Targets:**
- Minimum 44×44px for approve/reject buttons
- Swipe gestures for approve (right) / reject (left)
- Pull-to-dismiss review modal

### Performance Optimization

**Lazy Loading:**
```typescript
// Load verification details only when user opens modal
const VerificationDetails = lazy(() => import('./VerificationDetails'));

// Preload on hover (optimize for desktop)
onMouseEnter={() => preload(VerificationDetails)}
```

**Caching:**
```typescript
// Cache review decisions in React Query
const { mutate: approveBullet } = useMutation(
  approveBulletAPI,
  { onSuccess: () => queryClient.invalidateQueries('bullets') }
);
```

### Analytics & Monitoring

**Track User Behavior:**
- Time spent on review modal (per bullet)
- Approve vs. reject rate (by confidence tier)
- Edit frequency (how often users edit flagged content)
- Bulk action usage (approve all vs. individual review)
- Abandon rate at review step

**A/B Testing:**
- Test A: Show confidence scores (numeric: "0.62 confidence")
- Test B: Hide confidence scores (tier only: "Low confidence")
- Measure: User confidence in decisions, approval accuracy

## Success Criteria

After 4 weeks in production:

**User Acceptance:**
- ≥80% of flagged items approved by users
- <5% of users abandon generation at review step
- Average review time <90 seconds per flagged item
- User satisfaction score ≥4/5 for review experience

**Quality Metrics:**
- <3% of approved flagged items contain hallucinations (spot checks)
- ≥90% of rejected flagged items correctly identified as low-quality
- User edit rate <20% (most users approve/reject without editing)

**Technical Performance:**
- Review modal load time <1s (P95)
- Review action API response <500ms (P95)
- Zero frontend errors related to review workflow

## Links

**Related Documents:**
- **PRD**: `docs/prds/prd.md` v1.4.0 (review workflow requirements)
- **TECH-SPECS**:
  - `docs/specs/spec-frontend.md` v3.0.0 (planned - review UI components)
  - `docs/specs/spec-api.md` v5.0.0 (planned - review endpoints)
- **FEATURE**: `docs/features/ft-030-anti-hallucination-improvements.md` (planned)
- **RELATED ADRs**:
  - `adr-041-source-attribution-schema.md` (source data displayed in review)
  - `adr-042-verification-architecture.md` (verification results displayed)
  - `adr-043-confidence-thresholds.md` (determines when review is required)

**Design References:**
- GitHub PR review interface (approve/reject/request changes pattern)
- Grammarly suggestions UI (inline + detailed view)
- Google Docs suggestion mode (accept/reject with context)
- Stripe Dashboard alert patterns (severity-based coloring)

**Design Principles Reference:**
- `rules/design-principles.md` (S-Tier SaaS design standards)
