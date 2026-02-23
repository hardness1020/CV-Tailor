# Tech Spec — Frontend

**Version:** v3.0.0
**File:** docs/specs/spec-frontend.md
**Status:** Current
**PRD:** `prd.md` v1.5.0
**Contract Versions:** Frontend v3.0.0 • API Client v2.7 • Component Library v2.7 • Evidence Review v1.0
**Git Tags:** `spec-frontend-v1.0.0`, `spec-frontend-v2.0.0`, `spec-frontend-v2.1.0`, `spec-frontend-v2.1.1`, `spec-frontend-v2.2.0`, `spec-frontend-v2.3.0`, `spec-frontend-v2.4.0`, `spec-frontend-v2.5.0`, `spec-frontend-v2.5.1`, `spec-frontend-v2.6.0`, `spec-frontend-v2.7.0`, `spec-frontend-v2.8.0`, `spec-frontend-v2.9.0`, `spec-frontend-v3.0.0`

## Table of Contents
- [Overview & Goals](#overview--goals)
- [Architecture (Detailed)](#architecture-detailed)
  - [Topology (frameworks)](#topology-frameworks)
  - [Component Inventory](#component-inventory)
  - [Routing Structure](#routing-structure-v251)
- [Authentication Integration](#authentication-integration)
  - [Authentication State Management](#authentication-state-management)
  - [Dashboard-First Navigation Design](#dashboard-first-navigation-design)
  - [Route Protection System](#route-protection-system)
  - [API Client with Authentication](#api-client-with-authentication)
- [User Interface Components](#user-interface-components)
  - [Artifact Upload Flow](#artifact-upload-flow-simplified-in-v210)
- [Multi-Step Wizard Component System](#multi-step-wizard-component-system-v240)
- [Evidence Review & Acceptance Workflow](#evidence-review--acceptance-workflow-v300)
  - [Blocking Wizard Pattern](#blocking-wizard-pattern)
  - [Step 5: Evidence Processing](#step-5-evidence-processing)
  - [Step 6: Evidence Review & Acceptance](#step-6-evidence-review--acceptance)
  - [Evidence Review Components](#evidence-review-components)
  - [Evidence Review API Integration](#evidence-review-api-integration)
- [Performance & Optimization](#performance--optimization)
  - [Authentication Performance](#authentication-performance)
  - [Bundle Optimization](#bundle-optimization)
- [Security Implementation](#security-implementation)
  - [Client-Side Security](#client-side-security)
- [Artifact Detail Page Enhancements](#artifact-detail-page-enhancements)
  - [Tabbed Interface Architecture](#tabbed-interface-architecture)
  - [Enrichment Processing Feedback](#enrichment-processing-feedback)
  - [Evidence Content Display](#evidence-content-display)
  - [PDF/Document Download Links](#pdfdocument-download-links)
- [Generation Status Polling](#generation-status-polling-v280)
  - [Unified Status Endpoint Architecture](#unified-status-endpoint-architecture)
  - [useGenerationStatus Hook](#usegenerationstatus-hook)

## Overview & Goals

Build a modern, responsive React SPA frontend with comprehensive JWT authentication that provides an intuitive interface for user registration, login, profile management, artifact upload, job description input, CV/cover letter generation, and document export. Target sub-200ms UI interactions, mobile-responsive design, and accessibility compliance (WCAG AA).

Links to latest PRD: `docs/prds/prd.md`

**Application URLs:**
- **Production**: `https://<YOUR_DOMAIN>` (CloudFront CDN with ACM certificate, TLS 1.2+)
- **Development**: `http://localhost:3000` (Vite dev server, HTTP only)

## Architecture (Detailed)

### Topology (frameworks)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Browser Environment                               │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐  │
│  │   Service       │   State         │    UI Layer     │   Routing   │  │
│  │   Worker        │   Management    │   (React)       │  (React     │  │
│  │   (PWA)         │   (Zustand)     │                 │   Router)   │  │
│  │                 │   + Auth Store  │                 │ + Protected │  │
│  └─────────────────┼─────────────────┼─────────────────┼─────────────┘  │
└──────────────────┬─┼─────────────────┼─────────────────┼─────────────────┘
                   │ │                 │                 │
┌──────────────────▼─▼─────────────────▼─────────────────▼─────────────────┐
│                      React Application                                  │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐  │
│  │     Pages       │   Components    │    Hooks        │   Utils     │  │
│  │  ┌───────────┐  │  ┌───────────┐  │  ┌───────────┐  │             │  │
│  │  │Login      │  │  │AuthGuard  │  │  │useAuth    │  │             │  │
│  │  │Register   │  │  │ArtifactCard│  │  │useGenerate│  │             │  │
│  │  │Dashboard  │  │  │CVPreview  │  │  │useUpload  │  │             │  │
│  │  │Profile    │  │  │ExportBtn  │  │  │useProfile │  │             │  │
│  │  │Artifacts  │  │  │UserMenu   │  │  │...        │  │             │  │
│  │  │CVs        │  │  │...        │  │  │           │  │             │  │
│  │  │CVGenerate │  │  │           │  │  │           │  │             │  │
│  │  └───────────┘  │  └───────────┘  │  └───────────┘  │             │  │
│  └─────────────────┴─────────────────┴─────────────────┴─────────────┘  │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │ HTTP REST API + JWT Tokens
┌──────────────────▼─────────────────────────────────────────────────────┐
│                    API Client Layer                                    │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐ │
│  │   Axios         │    JWT Auth     │    Cache        │   Error     │ │
│  │   Client        │   Interceptor   │   Manager       │  Handler    │ │
│  │                 │ + Token Refresh │                 │ + Auth Retry│ │
│  └─────────────────┴─────────────────┴─────────────────┴─────────────┘ │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                           Build System                                   │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐  │
│  │     Vite        │   TypeScript    │      ESLint     │  Prettier   │  │
│  │   (Dev Server   │   (Type Safety  │   (Code Quality │  (Code      │  │
│  │   + HMR)        │   + Validation) │   + Standards)  │   Format)   │  │
│  └─────────────────┴─────────────────┴─────────────────┴─────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

### Component Inventory

| Component | Framework/Runtime | Purpose | Interfaces (in/out) | Depends On | Scale/HA | Owner |
|-----------|------------------|---------|-------------------|------------|----------|-------|
| React App | React 18 + Vite | Main application shell | In: User interactions; Out: API calls, DOM updates | State stores, Router | Client-side, stateless | Frontend |
| Authentication System | React + Zustand + JWT | User auth state management | In: Login/logout events; Out: API auth headers | Auth API, Local storage | Client-side, persistent | Frontend |
| Routing System | React Router v6 | SPA navigation with auth guards | In: URL changes; Out: Component rendering | Auth store, Route guards | Client-side, stateless | Frontend |
| State Management | Zustand | Global app state (auth, user, app data) | In: Actions; Out: State updates | React context, Persist middleware | Client-side, persistent | Frontend |
| API Client | Axios + Interceptors | HTTP client with auto auth | In: API calls; Out: HTTP requests with JWT headers | Auth store, Error handling | Client-side, stateless | Frontend |
| Form System | React Hook Form + Zod | Form validation and submission | In: User input; Out: Validated data, Error states | Validation schemas | Client-side, stateless | Frontend |
| UI Components | Custom React + Tailwind + Radix UI | Reusable interface elements | In: Props; Out: Rendered components | Design system, Icons | Client-side, stateless | Frontend |
| Tabs Component | @radix-ui/react-tabs | Accessible tabbed interfaces | In: Tab definitions; Out: Tabbed content areas | Radix UI, React | Client-side, stateless | Frontend |
| LoadingOverlay | Custom React Modal | Non-dismissible processing indicator | In: Loading state, message; Out: Blocking overlay with spinner | Modal component | Client-side, stateless | Frontend |
| EvidenceContentViewer | Custom React + Tabs | Enhanced evidence content display | In: Evidence ID; Out: Raw/processed content tabs | API Client, Tabs | Client-side, stateful | Frontend |
| WizardFlow | Custom React + Tailwind | Reusable multi-step wizard container | In: Steps, current step, theme; Out: Full-page wizard layout | WizardStepIndicator | Client-side, stateless | Frontend |
| WizardStepIndicator | Custom React | Visual progress indicator with step navigation | In: Steps, current step, colorScheme; Out: Interactive step pills | Lucide icons | Client-side, stateless | Frontend |
| CancelConfirmationDialog | Custom React Modal | Smart exit confirmation for unsaved changes | In: isOpen, progress, handlers; Out: Confirmation dialog | useWizardProgress | Client-side, stateless | Frontend |
| useWizardProgress | Custom React Hook | Progress tracking and change detection | In: Form state, total steps; Out: Progress state, completion % | React Hook Form | Client-side, stateful | Frontend |
| EvidenceReviewStep | Custom React + Tailwind | Blocking evidence review wizard step | In: Artifact ID, evidence list; Out: Evidence acceptance events | EvidenceCard, ConfidenceBadge, API Client | Client-side, stateful | Frontend |
| EvidenceCard | Custom React + Tailwind | Individual evidence review/edit interface | In: Evidence data, accept/reject handlers; Out: User actions, edited content | ConfidenceBadge, Inline editors | Client-side, stateful | Frontend |
| ConfidenceBadge | Custom React | Color-coded confidence score indicator | In: Confidence score (0-1); Out: Badge with color (red/yellow/green) | Tailwind variants | Client-side, stateless | Frontend |
| useEvidenceReview | Custom React Hook | Evidence acceptance state management | In: Artifact ID; Out: Evidence list, accept/reject/edit methods | API Client | Client-side, stateful | Frontend |
| Auth Guards | React HOC/Components | Route protection and redirects | In: User auth state; Out: Conditional rendering | Auth store, Router | Client-side, stateless | Frontend |
| Error Boundaries | React Error Boundary | Error handling and recovery | In: Component errors; Out: Error UI, Logging | Error reporting service | Client-side, stateless | Frontend |
| PWA Service Worker | Service Worker API | Offline support and caching | In: Network requests; Out: Cache responses | Browser APIs, Cache API | Client-side, persistent | Frontend |

### Routing Structure (v2.5.1)

**URL Pattern:** `/{resource}` (list), `/{resource}/{action}` (action), `/{resource}/:id` (detail)

| Route | Component | Purpose | Type |
|-------|-----------|---------|------|
| `/` | DashboardPage | Landing/overview | Root |
| `/login` | LoginPage | User authentication | Public |
| `/register` | RegisterPage | User registration | Public |
| `/dashboard` | DashboardPage | Main dashboard | Protected |
| `/profile` | ProfilePage | User profile management | Protected |
| `/artifacts` | ArtifactsPage | Artifact list view | Protected (list) |
| `/artifacts/upload` | ArtifactUpload | Artifact upload form | Protected (action) |
| `/artifacts/:id` | ArtifactDetailPage | Artifact detail view | Protected (detail) |
| `/generations` | GenerationsPage | Generation list view | Protected (list) |
| `/generations/create` | GenerationCreatePage | Generation wizard | Protected (action) |
| `/generations/:id` | GenerationDetailPage | Generation detail with bullet review | Protected (detail) |

**Rationale:** Consistent REST-style URLs across artifacts/generations for improved discoverability. See ADR-XXX for detailed analysis.

## Authentication Integration

### Auth Store Interface

```typescript
interface AuthState {
  // State
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  googleLinked: boolean

  // Actions (method signatures only)
  setUser: (user: User) => void
  setTokens: (access: string, refresh: string) => void
  clearAuth: () => void
  setLoading: (loading: boolean) => void
  setGoogleLinked: (linked: boolean) => void
}
```

### Authentication Hook

```typescript
interface UseAuthReturn {
  login: (email: string, password: string) => Promise<void>
  register: (userData: RegisterData) => Promise<void>
  logout: () => Promise<void>
  isLoading: boolean
}

export const useAuth: () => UseAuthReturn
```

**Note:** `user` and `isAuthenticated` state come from `useAuthStore` directly, not from the `useAuth` hook.

### Route Protection

```typescript
interface ProtectedRouteProps {
  children: React.ReactNode
}
```

**Routes:**
- Public: `/login`, `/register`
- Protected: `/dashboard`, `/profile`, `/artifacts`, `/generations`

### API Client

```typescript
class ApiClient {
  private client: AxiosInstance  // baseURL: '/api', timeout: 30000ms

  // Authentication Methods
  login(email: string, password: string): Promise<AuthResponse>
  register(userData: RegisterData): Promise<AuthResponse>
  refreshToken(): Promise<{ access: string; refresh: string }>
  logout(): Promise<void>
  getCurrentUser(): Promise<User>
  updateProfile(data: Partial<User>): Promise<User>
  changePassword(data: PasswordChangeData): Promise<void>
  requestPasswordReset(email: string): Promise<void>
}
```

**Authentication Flow:** JWT Bearer tokens with automatic refresh on 401. See feature specs for interceptor implementation.

## User Interface Components

### Artifact Upload Flow (v2.1.0)

**Evidence Types:**
1. **GitHub Repository** - Code projects and technical contributions
2. **Document (PDF)** - Project documentation, publications, certifications

**Artifact Form Schema:**
```typescript
interface ArtifactFormData {
  title: string
  description?: string  // Optional
  userContext?: string  // Optional, max 1000 chars (v2.2.0)
  startDate: string  // ISO date string
  endDate?: string
  technologies: string[]
  githubLinks: Array<{ url: string; description?: string }>
  labelIds: number[]
}
```

**Wizard Structure (v3.1.0):** 6-step flow (Basic Info → Your Context → Evidence → Confirm Details → Evidence Review → Final Review)

**Implementation Details:** See ft-018 (user_context field), ft-011 (evidence type simplification)

## Multi-Step Wizard Component System (v2.4.0)

**Purpose:** Unified wizard interface for artifact upload and CV generation workflows with WCAG 2.1 AA compliance.

**Component Interfaces:**

```typescript
// WizardFlow Props
interface WizardFlowProps {
  title: string
  steps: WizardStep[]
  currentStep: number
  onStepChange: (step: number) => void
  onCancel: () => void
  gradientTheme?: 'purple' | 'blue' | 'custom'
  children: ReactNode
}

// WizardStepIndicator Props
interface WizardStepIndicatorProps {
  steps: WizardStep[]
  currentStep: number
  onStepClick?: (step: number) => void
  colorScheme?: 'purple' | 'blue'  // v2.5.0
}

// useWizardProgress Hook
interface UseWizardProgressReturn {
  progress: WizardProgressState
  isFormTouched: boolean
  completionPercentage: number
  markStepTouched: (step: number) => void
  markStepCompleted: (step: number) => void
  updateFormData: (stepData: Record<string, any>) => void
  reset: () => void
}

// CancelConfirmationDialog Props
interface CancelConfirmationDialogProps {
  isOpen: boolean
  progress: WizardProgressState
  onConfirm: () => void
  onCancel: () => void
}
```

**Application Flows:**
- **ArtifactUploadFlow**: 5 steps, purple theme
- **CVGenerationFlow**: 5 steps, blue theme

**Implementation Details:** See ft-NEXT-unified-wizard-pattern.md, ADR-NEXT-wizard-ui-pattern.md

## Evidence Review & Acceptance Workflow (v3.0.0)

**Purpose:** Mandatory review and acceptance of AI-extracted evidence content before artifact finalization and bullet generation. Ensures content accuracy, allows user corrections, and prevents hallucinations in downstream CV/cover letter generation.

**Contract Version:** Evidence Review v1.0 (aligns with spec-api v4.9.0, spec-llm v4.3.0)

**Related PRD:** prd.md v1.5.0 (Evidence Review & Acceptance workflow requirements)
**Related Discovery:** disco-001-evidence-review-workflow.md (comprehensive workflow analysis)

### Blocking Wizard Pattern

The artifact upload wizard implements a **two-phase blocking pattern** to ensure evidence quality:

**Phase 1: Evidence Processing (Step 5, blocking)**
- Wizard automatically submits artifact and evidence to backend
- Backend processes asynchronously via Celery (evidence extraction from GitHub/PDFs)
- Frontend displays blocking spinner with progress message
- Step unblocks when all evidence processing completes (~30 seconds)
- User cannot proceed until extraction completes

**Phase 2: Evidence Review (Step 6, blocking)**
- User reviews ALL extracted evidence content (summary, technologies, achievements)
- User can edit content inline (fix errors, add missing items, remove incorrect items)
- User marks each evidence as accepted or rejected
- Step unblocks when ALL evidence is accepted (100% acceptance required)
- User cannot proceed to artifact finalization until all evidence accepted

**Design Rationale:**
- **Prevents hallucinations:** User verifies all AI-extracted content before use
- **User-paced blocking:** Step 6 blocks on user action (not time), reduces frustration
- **Clear progress indicators:** Users understand what's blocking and why
- **Mandatory review:** No "quick accept" shortcuts to ensure serious review

### Step 5: Evidence Processing

**Purpose:** Wait for backend evidence extraction to complete before showing review UI.

**Component:** `ProcessingStep` (new component)

**UI Pattern:**
```tsx
interface ProcessingStepProps {
  artifactId: string
  onProcessingComplete: () => void
  onError: (error: string) => void
}
```

**Behavior:**
1. Automatically triggered after Step 4 (Evidence) submission
2. Displays blocking LoadingOverlay with message: "Extracting content from your evidence sources..."
3. Polls `/api/v1/artifacts/{id}/` every 3 seconds to check `enrichment_status`
4. Unblocks when `enrichment_status === 'completed'`
5. Automatically advances to Step 6 (Evidence Review)
6. Shows error message if `enrichment_status === 'failed'`

**Performance SLO:** Unblock within 30 seconds for 95% of artifacts (3 evidence sources)

### Step 6: Evidence Review & Acceptance

**Purpose:** User reviews and accepts all AI-extracted evidence content with inline editing capabilities.

**Component:** `EvidenceReviewStep` (new component)

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Review Your Evidence Content                                │
│ Please review the content we extracted from your sources.   │
│ You can edit summaries, add/remove technologies, and fix    │
│ achievements before accepting.                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Evidence 1: my-awesome-project (GitHub)              │    │
│ │ Confidence: ████████░░ 85% [GREEN BADGE]             │    │
│ │                                                       │    │
│ │ Summary: [Editable textarea]                          │    │
│ │ Technologies: [Tag list with add/remove]              │    │
│ │ Achievements: [Editable list items]                   │    │
│ │                                                       │    │
│ │ [Edit] [✓ Accept] [✗ Reject]                         │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Evidence 2: research-paper.pdf (PDF)                 │    │
│ │ Confidence: ██████░░░░ 62% [YELLOW BADGE]            │    │
│ │ ... (same layout)                                     │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                              │
│ Progress: 1/3 accepted                                       │
│                                                              │
│ [← Back]                    [Finalize (disabled) →]          │
└─────────────────────────────────────────────────────────────┘
```

**Finalize Button State:**
- **Disabled:** When any evidence is pending (not accepted)
- **Enabled:** When ALL evidence accepted (100% acceptance rate)
- **Action:** Calls `POST /api/v1/artifacts/{id}/finalize-evidence-review/` to trigger LLM re-unification

**Validation Rules:**
- User must interact with EVERY evidence item (accept or reject)
- Rejection prevents artifact finalization (must accept all)
- Edits are auto-saved on blur (PATCH `/evidence/{id}/content/`)
- Backend validates edited content structure on save

### Evidence Review Components

**EvidenceReviewStep Component:**

```typescript
interface EvidenceReviewStepProps {
  artifactId: string
  onFinalize: () => void
  onBack: () => void
}

interface EvidenceReviewStepState {
  evidence: EnhancedEvidenceResponse[]
  acceptanceStatus: AcceptanceStatus
  isLoading: boolean
  error: string | null
}
```

**EvidenceCard Component:**

```typescript
interface EvidenceCardProps {
  evidence: EnhancedEvidenceResponse
  onAccept: (evidenceId: number, reviewNotes?: string) => Promise<void>
  onReject: (evidenceId: number) => Promise<void>
  onEdit: (evidenceId: number, content: ProcessedContent) => Promise<void>
  isEditing: boolean
  onToggleEdit: () => void
}

interface ProcessedContent {
  summary?: string
  technologies?: string[]
  achievements?: string[]
}
```

**ConfidenceBadge Component (existing, reuse):**

```typescript
interface ConfidenceBadgeProps {
  confidence: number  // 0.0 - 1.0
  size?: 'sm' | 'md' | 'lg'
}

// Color mapping:
// Red (<50%): "This content may need significant review"
// Yellow (50-80%): "This content may need minor corrections"
// Green (≥80%): "This content appears accurate"
```

**useEvidenceReview Hook:**

```typescript
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

interface AcceptanceStatus {
  canFinalize: boolean
  totalEvidence: number
  accepted: number
  rejected: number
  pending: number
  evidenceDetails: Array<{
    id: number
    title: string
    accepted: boolean
    acceptedAt: string | null
  }>
}
```

### Evidence Review API Integration

**API Endpoints Used (from spec-api v4.9.0):**

1. **Get Evidence Acceptance Status**
   ```
   GET /api/v1/artifacts/{artifact_id}/evidence-acceptance-status/
   → Returns: AcceptanceStatus
   ```

2. **Accept Evidence**
   ```
   POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/accept/
   Body: { review_notes?: string }
   → Returns: { accepted: true, accepted_at: timestamp }
   ```

3. **Reject Evidence**
   ```
   POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/reject/
   ```

4. **Edit Evidence Content**
   ```
   PATCH /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/content/
   Body: {
     processed_content: {
       summary?: string
       technologies?: string[]
       achievements?: string[]
     }
   }
   → Returns: Updated EnhancedEvidenceResponse
   ```

5. **Finalize Evidence Review**
   ```
   POST /api/v1/artifacts/{artifact_id}/finalize-evidence-review/
   → Returns: {
     artifact_id: number
     unified_description: string      // Re-generated from accepted evidence
     enriched_technologies: string[]  // Re-unified from accepted evidence
     enriched_achievements: string[]  // Re-unified from accepted evidence
     processing_confidence: number
     evidence_acceptance_summary: AcceptanceStatus
   }
   ```

**Error Handling:**
- **403 Forbidden:** If not all evidence accepted → Show toast: "Please accept all evidence before finalizing"
- **400 Bad Request:** If edited content invalid → Show inline error on field
- **500 Server Error:** If LLM re-unification fails → Show retry option with error message

**Performance Requirements:**
- Evidence content edit auto-save: ≤2 seconds
- Evidence accept/reject action: ≤1 second
- Finalize evidence review (LLM re-unification): ≤5 seconds

## Performance & Optimization

### Authentication Performance
- **Token Storage**: Secure storage in memory + httpOnly cookies for refresh tokens
- **Automatic Refresh**: Background token refresh without user interruption
- **Route-Based Code Splitting**: Lazy load authenticated vs public components
- **State Persistence**: Zustand persist middleware for authentication state
- **Optimistic Updates**: Immediate UI feedback for authentication actions

### Bundle Optimization
- **Lazy Loading**: Dynamic imports for authentication pages (LoginPage, RegisterPage, DashboardPage)
- **Route-Based Code Splitting**: Separate bundles for public vs protected routes
- **Suspense Fallback**: LoadingSpinner displayed during chunk loading

## Security Implementation

### Authentication & Token Management
- JWT access/refresh tokens with automatic refresh
- CSRF protection via Django CSRF tokens
- Client-side rate limiting with exponential backoff

### Application Security
- Input validation with Zod schemas
- XSS prevention via React auto-escaping
- Route guards with server validation
- Security score: 8.9/10

**Comprehensive Security Documentation:**
- Frontend security: `docs/security/frontend-security.md`
- CloudFront headers: `docs/deployment/cloudfront-security-headers.md`

## Artifact Detail Page Components

### LoadingOverlay

```typescript
interface LoadingOverlayProps {
  isOpen: boolean
  message: string
  progress?: number  // 0-100
}
```

### Evidence Content Display

```typescript
interface EnhancedEvidenceResponse {
  id: string
  evidenceId: number
  evidence: number
  title: string
  contentType: 'pdf' | 'github' | 'linkedin' | 'web_profile' | 'markdown' | 'text'
  rawContent: string
  processedContent: {
    technologies?: string[] | AttributedTechnology[]
    achievements?: string[] | AttributedAchievement[]
    skills?: string[]
    metrics?: any[]
    summary?: string
    description?: string
  }
  processingConfidence: number
  createdAt: string
}
```

**Implementation:** Tabbed interface (Overview/Evidence tabs), EvidenceContentViewer component with three-tab structure, toast notifications, PDF download handling. See ft-XXX for details.

## Generation Status Polling (v2.8.0)

**Status Endpoint:** Poll `/api/v1/generations/{id}/generation-status/` during generation (lightweight)

### GenerationStatus Type

```typescript
interface GenerationStatus {
  generation_id: string
  status: 'pending' | 'processing' | 'bullets_ready' | 'bullets_approved' | 'assembling' | 'completed' | 'failed'
  progress_percentage: number
  error_message?: string
  current_phase: 'bullet_generation' | 'bullet_review' | 'assembly' | 'completed'

  // See full type definition in spec-api.md
}
```

### useGenerationStatus Hook

```typescript
interface UseGenerationStatusOptions {
  generationId: string
  enabled?: boolean
  pollingInterval?: number  // Default: 10000ms
  onComplete?: (status: GenerationStatus) => void
  onError?: (error: string) => void
}

interface UseGenerationStatusReturn {
  status: GenerationStatus | null
  isPolling: boolean
  error: string | null
  refetch: () => Promise<void>
}
```

**Features:** Auto-polling with race condition prevention, terminal state detection. See ft-XXX for implementation details.

### API Client

```typescript
getGenerationStatus(generationId: string): Promise<GenerationStatus>
getGeneration(generationId: string): Promise<GeneratedDocument>
```

**Migration:** useGeneration hook continues to work. useGenerationStatus recommended for new workflows.
