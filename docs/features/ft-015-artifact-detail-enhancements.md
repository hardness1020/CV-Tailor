# Feature — 015 Artifact Detail Page Enhancements

**File:** docs/features/ft-015-artifact-detail-enhancements.md
**Owner:** Development Team
**TECH-SPECs:** `spec-frontend.md` (v2.1.1), `spec-api.md` (v4.0)
**Scope:** Medium (Multi-component UI changes, no new services)
**Status:** In Progress

## Existing Implementation Analysis

**Similar Features:**
- `frontend/src/pages/ProfilePage.tsx` - Existing page-level tab implementation (custom pattern)
- `frontend/src/components/EnrichedContentViewer.tsx` - Existing content-level tabs (custom pattern)
- `frontend/src/components/ArtifactEnrichmentStatus.tsx` - Existing loading states with `Loader2` + `animate-spin`
- `backend/llm_services/models.py` - `EnhancedEvidence` model with rich content fields

**Reusable Components:**
- `@radix-ui/react-tabs` - Already installed, should create wrapper component
- `frontend/src/components/ui/Modal.tsx` - Existing modal, extend for loading overlay
- `frontend/src/components/EvidenceLinkManager.tsx` - Base evidence display, extend with content viewer
- `backend/artifacts/serializers.py` - Extend `EvidenceSerializer` to include `enhanced_version`

**Patterns to Follow:**
- S-Tier SaaS design from `rules/design-principles.md`:
  - Consistent spacing (8px base unit)
  - Purposeful micro-interactions (150-300ms animations, ease-in-out)
  - Clear visual hierarchy
  - Purple/pink gradient for enrichment features (existing pattern)
- Tab pattern: Border-bottom active indicator
- Loading pattern: `Loader2` with `animate-spin` class

**Code to Refactor:**
- Consolidate tab implementations (ProfilePage, EnrichedContentViewer) into reusable Tabs component

**Dependencies:**
- `@radix-ui/react-tabs` (already installed)
- `lucide-react` icons (already installed)
- Backend: `EnhancedEvidence` model (already exists)
- Backend: `Evidence.enhanced_version` relationship (already exists)

## Architecture Conformance

**Layer Assignment:**
- **UI Components Layer:** New Tabs wrapper (`frontend/src/components/ui/Tabs.tsx`)
- **UI Components Layer:** LoadingOverlay component (`frontend/src/components/ui/LoadingOverlay.tsx`)
- **Feature Components Layer:** EvidenceContentViewer component (`frontend/src/components/EvidenceContentViewer.tsx`)
- **Page Layer:** Update ArtifactDetailPage with tabbed layout (`frontend/src/pages/ArtifactDetailPage.tsx`)
- **Serializers Layer:** Extend EvidenceSerializer (`backend/artifacts/serializers.py`)
- **API Client Layer:** Add getEnhancedEvidence method (`frontend/src/services/apiClient.ts`)

**Pattern Compliance:**
- Follows existing component structure (ui/ for primitives, components/ for features, pages/ for routes) ✓
- Uses established design tokens (purple/pink gradients, consistent spacing) ✓
- Implements accessibility standards (keyboard navigation, ARIA labels) ✓
- Follows Radix UI composition patterns ✓

**Dependencies:**
- `@radix-ui/react-tabs` for accessible tabs
- Existing `Modal` component as base for LoadingOverlay
- Existing `EvidenceLinkManager` component to extend
- Backend `EnhancedEvidence` model via API

## Acceptance Criteria

### 1. Processing Feedback (Issue 1)
- [ ] When user clicks "Enrich with AI", a non-dismissible loading overlay appears
- [ ] Loading overlay shows animated spinner (Loader2 with animate-spin)
- [ ] Loading overlay displays "AI Enrichment in Progress..." message
- [ ] Loading overlay shows progress percentage if available (0-100%)
- [ ] Overlay automatically dismisses on enrichment completion
- [ ] Success toast appears for 5 seconds with enrichment summary (technologies/achievements count)
- [ ] Failure toast appears with error message and retry button
- [ ] Toast messages have clear visual distinction (green for success, red for failure)

### 2. Tabbed Page Layout (Issue 2)
- [ ] Artifact detail page has page-level tabs: "Overview" and "Evidence"
- [ ] Overview tab displays: artifact description, technologies, dates, enriched content viewer, metadata
- [ ] Evidence tab displays: all evidence sources with EvidenceLinkManager
- [ ] Evidence count badge shows in Evidence tab label (e.g., "Evidence (3)")
- [ ] Tabs use Radix UI for accessibility (keyboard navigation, ARIA labels)
- [ ] Tab switching is instant with no loading delays
- [ ] Active tab has visual indicator (border-bottom, color change)
- [ ] Tab state persists during page interactions (not reset on state updates)

### 3. Evidence Content Display (Issue 2)
- [ ] Each evidence item in Evidence tab is an expandable card
- [ ] Evidence card shows: type icon, URL/filename, description, accessibility status
- [ ] Clicking evidence card expands to show sub-tabs: Overview, Content, Processed
- [ ] Overview sub-tab shows: URL, type, description, file size (if document), accessibility status
- [ ] Content sub-tab shows: raw extracted text from PDF/GitHub (scrollable)
- [ ] Processed sub-tab shows: technologies (tags), achievements (list), processing confidence
- [ ] Loading state while fetching enhanced evidence content
- [ ] Error handling if enhanced evidence not available
- [ ] Collapse/expand animation is smooth (150-300ms)

### 4. PDF Download Links (Issue 3)
- [ ] PDF links in Evidence tab are clickable and download correctly
- [ ] Document URLs prefixed with backend API base URL (http://localhost:8000)
- [ ] Download button shows file icon + filename
- [ ] File size displayed next to download link (if available)
- [ ] Broken/inaccessible documents show warning badge
- [ ] MIME type validation ensures only supported formats

### 5. Design Compliance (S-Tier Principles)
- [ ] Follows 8px spacing scale throughout
- [ ] Animations use ease-in-out timing (150-300ms)
- [ ] Purple/pink gradient for enrichment features
- [ ] Consistent typography and font weights
- [ ] WCAG AA color contrast compliance
- [ ] Keyboard navigation works for all interactive elements
- [ ] Mobile responsive (tabs stack vertically on small screens)
- [ ] Loading states prevent layout shift

## Design Changes

### UI Components

**New Tabs Component:**
```typescript
// frontend/src/components/ui/Tabs.tsx
import * as RadixTabs from '@radix-ui/react-tabs'

interface TabsProps {
  defaultValue: string
  children: React.ReactNode
}

export const Tabs = {
  Root: RadixTabs.Root,
  List: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <RadixTabs.List className={cn("border-b border-gray-200 bg-gray-50 flex", className)}>
      {children}
    </RadixTabs.List>
  ),
  Trigger: ({ value, children, count }: { value: string; children: React.ReactNode; count?: number }) => (
    <RadixTabs.Trigger
      value={value}
      className={cn(
        "px-6 py-3 text-sm font-medium transition-colors border-b-2",
        "data-[state=active]:border-purple-600 data-[state=active]:text-purple-700 data-[state=active]:bg-white",
        "data-[state=inactive]:border-transparent data-[state=inactive]:text-gray-600 hover:text-gray-900"
      )}
    >
      {children}
      {count !== undefined && (
        <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
          {count}
        </span>
      )}
    </RadixTabs.Trigger>
  ),
  Content: RadixTabs.Content
}
```

**LoadingOverlay Component:**
```typescript
// frontend/src/components/ui/LoadingOverlay.tsx
interface LoadingOverlayProps {
  isOpen: boolean
  message: string
  progress?: number
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ isOpen, message, progress }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl p-8 shadow-2xl flex flex-col items-center gap-4 max-w-md">
        <div className="relative">
          <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
          <div className="absolute inset-0 h-12 w-12 border-4 border-purple-200 rounded-full animate-ping opacity-75" />
        </div>
        <p className="text-lg font-medium text-gray-900">{message}</p>
        {progress !== undefined && (
          <div className="w-full">
            <div className="flex justify-between text-xs text-gray-600 mb-2">
              <span>Processing...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-pink-600 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

**EvidenceContentViewer Component:**
```typescript
// frontend/src/components/EvidenceContentViewer.tsx
interface EvidenceContentViewerProps {
  evidence: Evidence
  enhancedEvidence?: EnhancedEvidenceResponse
  isLoading: boolean
  onFetch: () => void
}

export const EvidenceContentViewer: React.FC<EvidenceContentViewerProps> = ({
  evidence,
  enhancedEvidence,
  isLoading,
  onFetch
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <Card className="overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={() => {
          setIsExpanded(!isExpanded)
          if (!isExpanded && !enhancedEvidence) {
            onFetch()
          }
        }}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <EvidenceTypeIcon type={evidence.evidence_type} />
          <div className="text-left">
            <p className="font-medium text-gray-900">{evidence.description || evidence.url}</p>
            <p className="text-sm text-gray-500">{evidence.evidence_type}</p>
          </div>
        </div>
        <ChevronDown className={cn("h-5 w-5 transition-transform", isExpanded && "rotate-180")} />
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div className="border-t border-gray-200">
          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
            </div>
          ) : enhancedEvidence ? (
            <Tabs.Root defaultValue="overview">
              <Tabs.List>
                <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
                <Tabs.Trigger value="content">Content</Tabs.Trigger>
                <Tabs.Trigger value="processed">Processed</Tabs.Trigger>
              </Tabs.List>

              <Tabs.Content value="overview" className="p-6">
                {/* Basic info */}
              </Tabs.Content>

              <Tabs.Content value="content" className="p-6">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 max-h-96 overflow-y-auto">
                  {enhancedEvidence.raw_content}
                </pre>
              </Tabs.Content>

              <Tabs.Content value="processed" className="p-6">
                {/* Technologies, achievements, confidence */}
              </Tabs.Content>
            </Tabs.Root>
          ) : (
            <div className="p-6 text-center text-gray-500">
              No enhanced content available
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
```

### API Changes

**Backend Serializer Extension:**
```python
# backend/artifacts/serializers.py
class EvidenceSerializer(serializers.ModelSerializer):
    enhanced_version = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = ('id', 'url', 'evidence_type', 'description', 'file_path', 'file_size',
                 'mime_type', 'is_accessible', 'enhanced_version', 'created_at', 'updated_at')

    def get_enhanced_version(self, obj):
        try:
            enhanced = obj.enhanced_version
            return {
                'id': enhanced.id,
                'title': enhanced.title,
                'content_type': enhanced.content_type,
                'raw_content': enhanced.raw_content[:1000],  # Preview only
                'processed_content': enhanced.processed_content,
                'processing_confidence': enhanced.processing_confidence,
            }
        except:
            return None
```

**API Client Method:**
```typescript
// frontend/src/services/apiClient.ts
async getEnhancedEvidence(evidenceId: number): Promise<EnhancedEvidenceResponse> {
  const response = await this.client.get(`/v1/evidence/${evidenceId}/enhanced/`)
  return response.data
}
```

## Test & Eval Plan

### Unit Tests
- **Tabs Component:**
  - Renders all tabs correctly
  - Active tab has correct styling
  - Tab switching updates activeTab state
  - Keyboard navigation works (Arrow keys, Tab, Enter)

- **LoadingOverlay:**
  - Shows/hides based on isOpen prop
  - Displays message correctly
  - Progress bar animates to correct percentage
  - Overlay is non-dismissible (clicking backdrop doesn't close)

- **EvidenceContentViewer:**
  - Collapses/expands on click
  - Fetches enhanced evidence on first expand
  - Shows loading state while fetching
  - Displays content in correct tabs
  - Handles missing enhanced evidence gracefully

### Integration Tests
- **ArtifactDetailPage:**
  - Page loads with both tabs rendered
  - Switching between Overview and Evidence tabs works
  - Evidence count badge shows correct number
  - Enrichment triggers loading overlay
  - Loading overlay dismisses on completion
  - Success/failure toasts appear with correct duration
  - Evidence items load enhanced content on expand

### End-to-End Tests
- **Enrichment Flow:**
  1. Navigate to artifact detail page
  2. Click "Enrich with AI" button
  3. Verify loading overlay appears
  4. Wait for enrichment to complete
  5. Verify overlay dismisses
  6. Verify success toast appears for 5 seconds
  7. Verify enriched content updates in Overview tab

- **Evidence Content Flow:**
  1. Navigate to artifact detail page
  2. Click Evidence tab
  3. Click on an evidence item to expand
  4. Verify sub-tabs appear (Overview, Content, Processed)
  5. Switch between sub-tabs
  6. Verify content loads correctly in each tab

### Accessibility Tests
- Keyboard navigation through all tabs
- Screen reader announces tab changes
- ARIA labels present and correct
- Color contrast meets WCAG AA standards
- Focus indicators visible

## Telemetry & Metrics

**Metrics to Track:**
- Evidence tab engagement rate (% of users who click Evidence tab)
- Evidence expansion rate (% of evidence items clicked)
- Enhanced content fetch success rate
- PDF download success rate
- Enrichment modal display duration (avg time)
- Toast notification interaction rate

**Dashboards:**
- User engagement with Evidence tab
- Evidence content loading performance (p95 latency)
- Enrichment success/failure rates

**Alerts:**
- Evidence content API errors > 5%
- PDF download failures > 10%
- Enhanced evidence fetch timeout > 2%

## Edge Cases & Risks

**Edge Cases:**
1. **No Enhanced Evidence:** Evidence exists but no enhanced_version → Show "No content available" message
2. **Large Content:** Raw content > 10KB → Truncate with "Show more" button
3. **Slow API:** Enhanced evidence fetch > 5s → Show timeout message with retry
4. **Network Failure:** API call fails → Show error with retry button
5. **No Evidence:** Artifact has zero evidence links → Evidence tab shows empty state
6. **PDF Not Found:** Document file_path doesn't exist → Show broken link warning
7. **Mobile View:** Tabs stack vertically, evidence cards are full-width

**Risks:**
1. **Performance:** Loading all enhanced evidence at once may be slow
   - **Mitigation:** Lazy load content on expand, cache fetched data
2. **State Management:** Multiple nested tabs may cause state bugs
   - **Mitigation:** Use Radix UI's controlled state, comprehensive testing
3. **PDF CORS:** Direct PDF links may fail due to CORS
   - **Mitigation:** Use download attribute, proxy through backend if needed
4. **Layout Shift:** Loading content causes layout jump
   - **Mitigation:** Reserve fixed height for loading states, smooth animations

## Rollout Plan

1. **Phase 1:** Create Tabs and LoadingOverlay components (Stage F-G)
2. **Phase 2:** Implement page-level tabs in ArtifactDetailPage (Stage G)
3. **Phase 3:** Add EvidenceContentViewer with enhanced content fetch (Stage G)
4. **Phase 4:** Fix PDF links with backend URL prefix (Stage G)
5. **Phase 5:** Refactor and accessibility audit (Stage H)
6. **Phase 6:** Deploy to staging, run smoke tests (Stage I-J)
7. **Phase 7:** Production deployment with feature flag (Stage K)

## Related Documents

- **PRD:** `docs/prds/prd.md`
- **TECH-SPEC:** `docs/specs/spec-frontend.md` (v2.1.1)
- **Stage B Discovery:** Documented in this file (Existing Implementation Analysis section)
- **Design Principles:** `rules/design-principles.md`
