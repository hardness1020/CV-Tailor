# Feature: Manual Artifact Selection with Keyword Suggestions (ft-007)

**Status:** In Development
**Created:** 2025-10-16
**Last Updated:** 2025-10-16
**Related Documents:**
- SPEC: `docs/specs/spec-artifact-selection.md` (v1.0.0)
- ADR: `docs/adrs/adr-028-remove-embeddings-manual-selection.md`

---

## Summary

Remove embedding/semantic similarity infrastructure and implement manual artifact selection with keyword-based ranking suggestions. Users will explicitly choose which artifacts to include in their CV generation, guided by keyword match scores.

---

## Stage B: Codebase Discovery Findings

### Reusable UI Components Found

✅ **Select.tsx** (`frontend/src/components/ui/Select.tsx`)
- Dropdown selector with label, error, helperText
- Can be used for sort/filter options in ArtifactSelector

✅ **Modal.tsx** (`frontend/src/components/ui/Modal.tsx`)
- Backdrop + centered modal with sizes (sm, md, lg, xl)
- Can be used for artifact preview modal in ArtifactSelector

✅ **LoadingOverlay.tsx** (`frontend/src/components/ui/LoadingOverlay.tsx`)
- Fixed overlay with spinner, message, optional progress bar
- Can be used while fetching artifact suggestions

✅ **EnrichmentStatusBadge.tsx** (`frontend/src/components/EnrichmentStatusBadge.tsx`)
- Badge component pattern with gradient backgrounds, icons, status colors
- **Reusable pattern** for relevance score badges:
  - `bg-gradient-to-r from-purple-100 to-pink-100` (processing)
  - `bg-green-100` (high relevance)
  - `bg-gray-100` (low relevance)
  - Icon + text layout

### Existing UI Patterns Found

✅ **Multi-select with Checkboxes** (`frontend/src/pages/ArtifactsPage.tsx`, lines 376-394)
- Checkbox component pattern:
  ```tsx
  <div className={cn(
    'w-5 h-5 rounded border-2 flex items-center justify-center',
    isSelected ? 'bg-purple-600 border-purple-600 text-white' : 'border-gray-300'
  )}>
    {isSelected && <CheckIcon />}
  </div>
  ```
- Selection state management via Zustand:
  ```tsx
  const { selectedArtifacts, toggleSelection, clearSelection } = useArtifactStore()
  ```

✅ **Drag-and-Drop** (`frontend/src/components/ArtifactUpload.tsx`, line 2)
- Uses `react-dropzone` library (already in dependencies)
- Pattern: `const { getRootProps, getInputProps, isDragActive } = useDropzone({...})`
- **NOTE:** For drag-to-reorder, we'll need `@dnd-kit/core` or `react-beautiful-dnd` (check if already in package.json)

✅ **Multi-Step Workflow** (`frontend/src/components/ArtifactUpload.tsx`, lines 63-1229)
- State management: `const [currentStep, setCurrentStep] = useState(1)`
- Step validation: `const handleNext = async () => { const isValid = await trigger(...) }`
- Step indicator component: `<StepIndicator currentStep={currentStep} />` (lines 1144-1229)
- **Reusable for CV Generation Workflow**

✅ **React Hook Form + Zod Validation** (`frontend/src/components/ArtifactUpload.tsx`, lines 83-99)
```tsx
const { register, control, handleSubmit, watch, setValue, formState: { errors }, trigger } = useForm<Form>({
  resolver: zodResolver(schema),
  mode: 'onChange'
})
```
- Can be used for artifact selection validation (min 1 artifact selected)

### Existing Backend Patterns Found

✅ **@action Decorator for Custom Endpoints** (Django REST Framework)
- Example: Search for similar pattern in artifacts/views.py or generation/views.py
- Pattern:
  ```python
  @action(detail=False, methods=['post'])
  def suggest_for_job(self, request):
      # Custom endpoint logic
  ```

✅ **Keyword Ranking Implementation** (`backend/llm_services/services/core/artifact_ranking_service.py`, lines 120-172)
- Already has `_rank_by_keyword_overlap()` method
- Scoring algorithm:
  - Exact matches: 1.0 weight
  - Partial matches: 0.5 weight
  - Normalized to 0.0-1.0 range
- Returns artifacts with `relevance_score`, `exact_matches`, `partial_matches`
- **Can be enhanced with fuzzy matching and recency weighting**

✅ **Migration Pattern for DROP TABLE** (`backend/llm_services/migrations/0009_drop_orphaned_tables.py`)
```python
migrations.RunSQL(
    sql="""
        DROP TABLE IF EXISTS table1 CASCADE;
        DROP TABLE IF EXISTS table2 CASCADE;
    """,
    reverse_sql=migrations.RunSQL.noop,
)
```

### Missing Components (Need to Create)

❌ **Drag-to-Reorder Library**
- Check if `@dnd-kit/core` or `react-beautiful-dnd` in package.json
- If not, need to install: `npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`

❌ **Fuzzy String Matching Library**
- For enhanced keyword matching (typos, abbreviations)
- Consider: `fuzzywuzzy` (Python), `difflib` (Python stdlib), or `rapidfuzz` (faster)
- **Decision:** Use `difflib` (stdlib, no dependencies) for v1.0.0

❌ **ArtifactSelector Component**
- Main component for this feature (needs to be created)

❌ **Relevance Score Badge Component**
- Variant of EnrichmentStatusBadge for showing keyword match %
- Can reuse badge pattern from EnrichmentStatusBadge

### Architecture Insights

✅ **State Management:** Zustand (used in `useArtifactStore`)
- File: `frontend/src/stores/artifactStore.ts`
- Pattern: `create<State>((set, get) => ({ ... }))`
- Can add `selectedArtifactsForCV: number[]` to store

✅ **API Client Pattern** (`frontend/src/services/apiClient.ts`)
- Axios-based client with methods like:
  ```typescript
  async createArtifact(data: ArtifactData): Promise<Artifact>
  async getLLMJobEmbeddings(): Promise<JobDescriptionEmbedding[]>
  ```
- **Will add:**
  ```typescript
  async suggestArtifactsForJob(jobDescription: string): Promise<ArtifactSuggestion[]>
  ```

✅ **Service Layer Pattern** (`backend/llm_services/services/`)
- Base class: `BaseLLMService` (common functionality)
- Separation: core/ (business logic) vs infrastructure/ (supporting)
- **ArtifactRankingService already exists** - will simplify, not recreate

---

## Goals

### Primary Goals

1. **Remove Complexity:**
   - Delete ~1500 lines of embedding-related code
   - Remove pgvector infrastructure dependency
   - Simplify ArtifactRankingService to keyword-only

2. **Empower Users:**
   - Add UI for manual artifact selection
   - Show transparent relevance scores (keyword match %)
   - Allow drag-to-reorder artifacts by importance

3. **Reduce Costs:**
   - Eliminate embedding API costs ($0.01-0.05 per CV)
   - Reduce database storage (~1.5KB per artifact)

### Secondary Goals

4. **Maintain Quality:**
   - Keyword ranking quality ≥ current hybrid ranking
   - Provide helpful suggestions (not just empty list)

5. **Improve Performance:**
   - Keyword ranking: < 200ms for 100 artifacts
   - Artifact suggestion API: < 500ms

---

## Non-Goals

- ❌ Re-implement semantic search (may consider in future if proven necessary)
- ❌ ML-based ranking model (out of scope for v1.0.0)
- ❌ Artifact recommendation engine (collaborative filtering)
- ❌ Automatic selection (removing user control)

---

## User Stories

### Story 1: Manual Artifact Selection

**As a** job seeker
**I want to** manually select which artifacts to include in my CV
**So that** I can control what experiences are highlighted for each job

**Acceptance Criteria:**
- [ ] Artifact selection step appears after job description input
- [ ] All my artifacts are displayed with relevance scores
- [ ] I can select/deselect artifacts via checkboxes
- [ ] I can reorder selected artifacts by dragging
- [ ] I can see why each artifact is relevant (matched keywords highlighted)
- [ ] I can search/filter artifacts by title or technology
- [ ] Selection persists if I navigate back to edit job description

### Story 2: Keyword-Based Suggestions

**As a** job seeker
**I want to** see suggested artifacts ranked by keyword match
**So that** I can quickly identify relevant experiences without manual analysis

**Acceptance Criteria:**
- [ ] Artifacts are ranked by relevance score (0-100%)
- [ ] Relevance score is displayed as a badge on each artifact
- [ ] Matched keywords are highlighted or listed
- [ ] Exact matches are weighted higher than partial matches
- [ ] Recent artifacts are weighted slightly higher (recency bias)
- [ ] I can sort by relevance, date, or title

### Story 3: Quick Selection Actions

**As a** job seeker with many artifacts
**I want** quick action buttons for common selections
**So that** I don't have to manually check 10+ boxes every time

**Acceptance Criteria:**
- [ ] "Use all suggested" button selects top N artifacts
- [ ] "Clear selection" button deselects all
- [ ] "Select all" button selects all artifacts
- [ ] Default selection: top 5 by relevance

### Story 4: Backward Compatibility

**As a** developer
**I want** the CV generation API to work without artifact_ids
**So that** existing integrations/tests don't break

**Acceptance Criteria:**
- [ ] `POST /v1/generation/cv/` works without `artifact_ids` parameter
- [ ] When `artifact_ids` not provided, uses keyword ranking (top 5)
- [ ] All existing CV generation tests pass without modification

---

## Technical Implementation Plan

### Phase 1: Database Cleanup (2-3 hours)

**Tasks:**
1. Create migration to drop tables and columns
2. Test migration on local database
3. Verify artifact data preserved

**Files:**
- `backend/generation/migrations/000X_remove_embedding_infrastructure.py`

**Discovered Pattern Used:**
- DROP TABLE migration pattern from `0009_drop_orphaned_tables.py`

---

### Phase 2: Backend Simplification (3-4 hours)

**Task 2.1: Simplify ArtifactRankingService**

**File:** `backend/llm_services/services/core/artifact_ranking_service.py`

**Changes:**
- Remove methods:
  - `_rank_by_semantic_similarity()` (lines 80-118)
  - `_get_chunk_based_similarity()` (lines 301-338)
  - `find_similar_artifacts()` (lines 223-260)
  - `_similarity_search_sync()` (lines 262-299)

- Simplify method signature:
  ```python
  # BEFORE:
  async def rank_artifacts_by_relevance(
      self, artifacts, job_requirements, job_embedding=None, user_id=None, strategy='hybrid'
  )

  # AFTER:
  def rank_artifacts_by_relevance(
      self, artifacts, job_requirements, user_id=None
  )
  # Note: Make sync (no async needed without embedding API calls)
  ```

- Enhance `_rank_by_keyword_overlap()`:
  ```python
  def _rank_by_keyword_overlap(self, artifacts, job_requirements):
      # Existing logic (lines 120-172)
      # + ADD: Fuzzy matching using difflib.SequenceMatcher
      # + ADD: Recency weighting (newer artifacts +5-10% boost)
      # + ADD: Return matched_keywords list per artifact
  ```

**Task 2.2: Remove Embedding Service**

**Files to DELETE (Embedding-Only Code):**
- `backend/llm_services/services/core/embedding_service.py` (complete file deletion)
- JobDescriptionEmbedding model from `backend/llm_services/models.py`
- ArtifactChunk model from `backend/llm_services/models.py`
- Embedding-specific ViewSets from `backend/llm_services/views.py`
- Embedding-specific serializers from `backend/llm_services/serializers.py`
- Embedding routes from `backend/llm_services/urls.py`
- Embedding admin from `backend/llm_services/admin.py`

**Models to KEEP (Enrichment, NOT Embeddings):**
- `EnhancedEvidence` - stores enriched content from evidence sources (ft-005)
  - NOTE: Contains NO embedding fields, only processed_content
- `ExtractedContent` - per-source extraction results (ft-005)
- `GitHubRepositoryAnalysis` - GitHub agent analysis metadata (ft-013)
- Infrastructure models: `ModelPerformanceMetric`, `CircuitBreakerState`, `ModelCostTracking`

**File to UPDATE:**
- `backend/llm_services/services/core/__init__.py` - Remove EmbeddingService export only

**Task 2.3: Add Suggest Artifacts Endpoint**

**File:** `backend/artifacts/views.py`

**Changes:**
```python
from rest_framework.decorators import action
from llm_services.services.core.artifact_ranking_service import ArtifactRankingService

class ArtifactViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=False, methods=['post'])
    def suggest_for_job(self, request):
        """
        Suggest artifacts for a job description using keyword ranking.

        POST /v1/artifacts/suggest-for-job/
        Body: { "job_description": "...", "limit": 10 }
        Returns: { "artifacts": [...], "total_artifacts": 25, "returned_count": 10 }
        """
        job_description = request.data.get('job_description', '')
        limit = request.data.get('limit', 10)

        # Validate input
        if not job_description or len(job_description) < 10:
            return Response(
                {"error": "job_description must be at least 10 characters"},
                status=400
            )

        # Extract job requirements (keywords)
        job_requirements = self._extract_keywords(job_description)

        # Fetch all user artifacts
        artifacts = Artifact.objects.filter(user=request.user).values(...)

        # Rank artifacts
        ranking_service = ArtifactRankingService()
        ranked = ranking_service.rank_artifacts_by_relevance(
            list(artifacts), job_requirements
        )

        # Limit results
        suggested = ranked[:limit]

        return Response({
            "artifacts": suggested,
            "total_artifacts": len(artifacts),
            "returned_count": len(suggested)
        })
```

**Discovered Pattern Used:**
- `@action` decorator (Django REST Framework pattern)

**Task 2.4: Update CV Generation Service**

**File:** `backend/generation/services/cv_generation_service.py`

**Changes:**
```python
async def generate_cv_for_job(
    self,
    user_id: int,
    job_description: str,
    artifact_ids: Optional[List[int]] = None  # NEW PARAMETER
) -> Dict[str, Any]:
    if artifact_ids:
        # Manual selection: fetch selected artifacts
        artifacts = await self._fetch_selected_artifacts(user_id, artifact_ids)
    else:
        # Automatic selection: use keyword ranking (backward compatibility)
        all_artifacts = await self._fetch_user_artifacts(user_id)
        ranked = self.ranking_service.rank_artifacts_by_relevance(...)
        artifacts = ranked[:5]

    # Continue with CV generation...
```

---

### Phase 3: Frontend Implementation (4-5 hours)

**Task 3.1: Create ArtifactSelector Component**

**File:** `frontend/src/components/ArtifactSelector.tsx`

**Reusable Components:**
- ✅ Modal (for artifact preview)
- ✅ LoadingOverlay (while fetching suggestions)
- ✅ Badge pattern from EnrichmentStatusBadge (for relevance scores)
- ✅ Checkbox pattern from ArtifactsPage (for multi-select)

**New Dependencies (if needed):**
```bash
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

**Component Structure:**
```tsx
import { useEffect, useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { LoadingOverlay } from '@/components/ui/LoadingOverlay'
import { apiClient } from '@/services/apiClient'
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface ArtifactSelectorProps {
  jobDescription: string;
  onSelectionChange: (artifactIds: number[]) => void;
  initialSelection?: number[];
  className?: string;
}

export function ArtifactSelector({ jobDescription, onSelectionChange, initialSelection, className }: ArtifactSelectorProps) {
  const [suggestions, setSuggestions] = useState<ArtifactSuggestion[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>(initialSelection || [])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'title'>('relevance')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // Fetch suggestions on mount
    fetchSuggestions()
  }, [jobDescription])

  const fetchSuggestions = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.suggestArtifactsForJob(jobDescription)
      setSuggestions(response.artifacts)
      // Auto-select top 5
      const topFive = response.artifacts.slice(0, 5).map(a => a.id)
      setSelectedIds(topFive)
      onSelectionChange(topFive)
    } catch (err) {
      setError('Failed to fetch artifact suggestions')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSelection = (id: number) => {
    const newSelection = selectedIds.includes(id)
      ? selectedIds.filter(sid => sid !== id)
      : [...selectedIds, id]
    setSelectedIds(newSelection)
    onSelectionChange(newSelection)
  }

  const handleDragEnd = (event) => {
    // Handle drag-to-reorder
    const { active, over } = event
    if (active.id !== over.id) {
      const oldIndex = selectedIds.indexOf(active.id)
      const newIndex = selectedIds.indexOf(over.id)
      const reordered = arrayMove(selectedIds, oldIndex, newIndex)
      setSelectedIds(reordered)
      onSelectionChange(reordered)
    }
  }

  // ... render logic
}
```

**Task 3.2: Update CV Generation Workflow**

**File:** `frontend/src/pages/CVGenerationWorkflow.tsx` (or similar)

**Reusable Pattern:**
- ✅ Multi-step workflow from ArtifactUpload.tsx

**Changes:**
```tsx
interface CVGenerationState {
  jobDescription: string;
  selectedArtifactIds: number[];  // NEW
  generatedCV: CVDocument | null;
  currentStep: 1 | 2 | 3;  // 1: Job Desc, 2: Artifacts, 3: Review
}

// Step 2: Artifact Selection
{currentStep === 2 && (
  <ArtifactSelector
    jobDescription={state.jobDescription}
    onSelectionChange={(ids) => setState({...state, selectedArtifactIds: ids})}
  />
)}

// When generating CV:
const cv = await apiClient.generateCV(state.jobDescription, state.selectedArtifactIds)
```

**Task 3.3: Update API Client**

**File:** `frontend/src/services/apiClient.ts`

**Changes:**
```typescript
// ADD:
async suggestArtifactsForJob(jobDescription: string, limit = 10): Promise<{
  artifacts: ArtifactSuggestion[];
  total_artifacts: number;
  returned_count: number;
}> {
  const response = await this.client.post('/v1/artifacts/suggest-for-job/', {
    job_description: jobDescription,
    limit
  })
  return response.data
}

// UPDATE:
async generateCV(jobDescription: string, artifactIds?: number[]): Promise<CVResponse> {
  const response = await this.client.post('/v1/generation/cv/', {
    job_description: jobDescription,
    artifact_ids: artifactIds  // OPTIONAL
  })
  return response.data
}

// REMOVE:
async getLLMJobEmbeddings(): Promise<JobDescriptionEmbedding[]>
async getLLMEnhancedArtifacts(): Promise<EnhancedArtifact[]>
async getEnhancedEvidence(): Promise<EnhancedEvidenceResponse>
```

**Task 3.4: Update TypeScript Types**

**File:** `frontend/src/types/index.ts`

**Changes:**
```typescript
// ADD:
export interface ArtifactSuggestion {
  id: number;
  title: string;
  description: string;
  relevance_score: number;  // 0.0 to 1.0
  exact_matches: number;
  partial_matches: number;
  matched_keywords: string[];
  technologies: string[];
  start_date: string;
  end_date?: string;
}

// REMOVE:
export interface JobDescriptionEmbedding { ... }
export interface EnhancedArtifact { ... }
export interface EnhancedEvidenceResponse { ... }
```

---

## Testing Strategy

### Unit Tests

**Backend:**
1. `test_artifact_ranking_service.py`:
   - `test_keyword_ranking_with_exact_matches()`
   - `test_keyword_ranking_with_partial_matches()`
   - `test_fuzzy_matching_for_typos()`
   - `test_recency_weighting()`
   - `test_ranking_returns_scores_between_0_and_1()`

2. `test_suggest_artifacts_endpoint.py`:
   - `test_suggest_artifacts_returns_top_n()`
   - `test_suggest_artifacts_validates_ownership()`
   - `test_suggest_artifacts_handles_empty_job_description()`
   - `test_suggest_artifacts_handles_no_artifacts()`

3. `test_cv_generation_with_selected_artifacts.py`:
   - `test_generate_cv_with_artifact_ids()`
   - `test_validate_artifact_ownership()`
   - `test_invalid_artifact_id_handling()`
   - `test_backward_compatibility_without_artifact_ids()`

**Frontend:**
1. `ArtifactSelector.test.tsx`:
   - Renders artifact list with relevance scores
   - Handles selection/deselection
   - Handles drag-and-drop reordering
   - Shows empty state when no artifacts
   - Calls API on mount
   - Handles API errors gracefully

2. `CVGenerationWorkflow.test.tsx`:
   - Artifact selection step appears after job description
   - Selection persists across navigation
   - Workflow continues with selected artifacts

### Integration Tests

1. **E2E Test: Complete CV Generation Flow**
   - Enter job description
   - See artifact suggestions
   - Select 3 artifacts
   - Reorder artifacts
   - Generate CV
   - Verify CV contains selected artifacts only

---

## UI/UX Design

### ArtifactSelector Component Layout

```
┌─────────────────────────────────────────────────────────┐
│  Artifact Selection                            [X Close] │
├─────────────────────────────────────────────────────────┤
│  Select artifacts to include in your CV:                │
│                                                          │
│  [Search: ___________]  Sort: [Relevance ▾]             │
│                                                          │
│  ┌───────────────────────────────────────────────┐      │
│  │ [✓] E-commerce Platform          [85%] ●●●●○  │      │
│  │     Built scalable marketplace...             │      │
│  │     📌 React, Node.js, PostgreSQL             │      │
│  │     ▦ Drag to reorder                         │      │
│  ├───────────────────────────────────────────────┤      │
│  │ [ ] API Gateway Service          [72%] ●●●○○  │      │
│  │     RESTful API with OAuth...                 │      │
│  │     📌 Python, FastAPI, Redis                 │      │
│  ├───────────────────────────────────────────────┤      │
│  │ [✓] Mobile App for Healthcare    [68%] ●●●○○  │      │
│  │     Cross-platform mobile...                  │      │
│  │     📌 React Native, TypeScript               │      │
│  └───────────────────────────────────────────────┘      │
│                                                          │
│  [Select All] [Clear] [Use Top 5]                       │
│                                                          │
│  3 artifacts selected                   [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

### Relevance Score Badge

```
High Match (80-100%):  [95%] ●●●●●  (green gradient)
Good Match (60-79%):   [72%] ●●●●○  (blue gradient)
Fair Match (40-59%):   [55%] ●●●○○  (yellow)
Low Match (0-39%):     [25%] ●●○○○  (gray)
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CV generation completion rate | ≥ 85% | Analytics funnel |
| Artifact selection drop-off | < 15% | Step navigation tracking |
| Keyword ranking latency (p95) | < 200ms | Performance monitoring |
| User satisfaction (suggestion quality) | ≥ 4.0/5.0 | Post-generation survey |
| Codebase simplification | ~1500 lines removed | Git diff |
| Database storage savings | ~1.5KB/artifact | Database size monitoring |

---

## Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Keyword matching insufficient | Medium | Medium | Add fuzzy matching, recency weighting, manual search |
| User friction from manual selection | Low | High | "Use top 5" quick action, save preferences |
| Re-enablement cost higher than estimated | Low | Medium | Document architecture, keep code in git history |

---

## Timeline

- **Stage B (Discovery):** 1-2 hours ✅
- **Stage C (SPEC):** 1 hour ✅
- **Stage D (ADR):** 30 min ✅
- **Stage E (FEATURE):** 1 hour ✅ (this document)
- **Stage F (Tests):** 2-3 hours ⏳
- **Stage G (Implementation):** 4-5 hours
- **Stage H (Refactor):** 2-3 hours

**Total:** 12-16 hours

---

## Dependencies

### Frontend
- ✅ `react-dropzone` (already installed)
- ❓ `@dnd-kit/core` + `@dnd-kit/sortable` (check package.json, install if needed)
- ✅ `react-hook-form` + `zod` (already installed)
- ✅ `zustand` (already installed)

### Backend
- ✅ `difflib` (Python stdlib - no install needed)
- ❌ pgvector (will be removed)

---

## Rollout Plan

1. **Staging Deployment:**
   - Deploy to staging environment
   - Run full test suite
   - Manual QA testing

2. **Production Deployment:**
   - Database backup
   - Run migration (2-5 min downtime)
   - Deploy code
   - Monitor for 1 hour

3. **Monitoring (30 days):**
   - Track completion rates
   - Monitor keyword ranking latency
   - Collect user feedback
   - Watch for errors

4. **Evaluation:**
   - Review success metrics
   - Decide: keep, iterate, or rollback

---

## Appendix: Discovered Reusable Code

### A1: Checkbox Component Pattern
```tsx
// Source: frontend/src/pages/ArtifactsPage.tsx:376-394
<div
  className={cn(
    'w-5 h-5 rounded border-2 flex items-center justify-center transition-all cursor-pointer',
    isSelected
      ? 'bg-purple-600 border-purple-600 text-white'
      : 'border-gray-300 hover:border-purple-500'
  )}
  onClick={() => toggleSelection(id)}
>
  {isSelected && (
    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  )}
</div>
```

### A2: Badge Gradient Pattern
```tsx
// Source: frontend/src/components/EnrichmentStatusBadge.tsx:31
className={cn(
  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold',
  score >= 0.8 && 'bg-green-100 text-green-700 border border-green-200',
  score >= 0.6 && score < 0.8 && 'bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 border border-purple-200',
  score < 0.6 && 'bg-gray-100 text-gray-600 border border-gray-200'
)}
```

### A3: Multi-Step Workflow State
```tsx
// Source: frontend/src/components/ArtifactUpload.tsx:66
const [currentStep, setCurrentStep] = useState(1)

const handleNext = async () => {
  const isValid = await trigger([...fieldNames])
  if (isValid) {
    setCurrentStep(prev => Math.min(prev + 1, TOTAL_STEPS))
  }
}

const handleBack = () => {
  setCurrentStep(prev => Math.max(prev - 1, 1))
}
```

---

**Feature Owner:** Product Team
**Implementation Owner:** Backend + Frontend Teams
**Reviewer:** Technical Lead
