# Tech Spec — API

**Version:** v4.9.1
**File:** docs/specs/spec-api.md
**Status:** Current
**PRD:** `prd.md` v1.5.0
**Contract Versions:** API v4.9 • Schema v4.1 • Queue v1.0 • Evidence Review v1.1
**Git Tags:** `spec-api-v1.0.0`, `spec-api-v2.0.0`, `spec-api-v3.0.0`, `spec-api-v4.0.0`, `spec-api-v4.1.0`, `spec-api-v4.2.0`, `spec-api-v4.3.0`, `spec-api-v4.4.0`, `spec-api-v4.5.0`, `spec-api-v4.6.0`, `spec-api-v4.7.0`, `spec-api-v4.8.0`, `spec-api-v4.9.0`, `spec-api-v4.9.1`

## Table of Contents

- [Overview & Goals](#overview--goals)
- [Architecture (Detailed)](#architecture-detailed)
  - [Topology (frameworks)](#topology-frameworks)
  - [Component Inventory](#component-inventory)
- [Interfaces & Data Contracts](#interfaces--data-contracts)
  - [Authentication Endpoints](#authentication-endpoints)
    - [Core Authentication](#core-authentication)
    - [Password Management](#password-management)
    - [OAuth Integration](#oauth-integration)
    - [User Profile Management](#user-profile-management)
  - [Artifact Management Endpoints](#artifact-management-endpoints)
    - [Evidence Types](#evidence-types)
    - [Artifact CRUD Operations](#artifact-crud-operations)
    - [Artifact Selection & Ranking](#artifact-selection--ranking)
    - [Artifact Enrichment](#artifact-enrichment)
    - [Evidence Management](#evidence-management)
  - [Generation Endpoints](#generation-endpoints)
    - [Two-Phase CV Generation Workflow](#two-phase-cv-generation-workflow-ft-009)
    - [Cover Letter Generation](#cover-letter-generation)
    - [Generation Management](#generation-management)
    - [Quality Control](#quality-control)
    - [Generation Analytics](#generation-analytics)
  - [Export Endpoints](#export-endpoints)
    - [Export Operations](#export-operations)
    - [Export Configuration](#export-configuration)
    - [Export Analytics](#export-analytics)
  - [Error Response Format](#error-response-format)
- [Data & Storage](#data--storage)
  - [Database Schema](#database-schema)
- [Security & Privacy](#security--privacy)
  - [Network Security & Transport Layer](#network-security--transport-layer)
  - [CSRF Protection](#csrf-protection)
  - [JWT Token Security](#jwt-token-security)
  - [Password Validation](#password-validation)
- [Reliability & SLIs/SLOs](#reliability--slisslos)
  - [Service Level Indicators](#service-level-indicators)
  - [Service Level Objectives](#service-level-objectives)
  - [Reliability Mechanisms](#reliability-mechanisms)
- [Evaluation Plan](#evaluation-plan)

## Overview & Goals

Build a robust REST API backend using Django DRF that handles comprehensive user authentication, artifact management, job description parsing, CV/cover letter generation, and document export. Target P95 ≤30s for CV generation, ≥99.5% availability, and support for 10,000 concurrent users with proper rate limiting and caching.

Links to latest PRD: `docs/prds/prd.md`

**API Base URLs:**
- **Production**: `https://api.<YOUR_DOMAIN>` (ALB with ACM certificate, TLS 1.2+)
- **Development**: `http://localhost:8000` (Django dev server, HTTP only)

**Note**: All endpoint examples below use relative paths (e.g., `/api/v1/auth/login/`). Prepend the appropriate base URL based on environment.

## Architecture (Detailed)

### Topology (frameworks)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      API Layer (Django DRF + JWT)                      │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐  │
│  │  Auth & Users   │   Artifacts     │   Generation    │   Export    │  │
│  │   ViewSets      │    ViewSets     │    ViewSets     │  ViewSets   │  │
│  │   + JWT Auth    │                 │                 │             │  │
│  └─────────────────┼─────────────────┼─────────────────┼─────────────┘  │
└──────────────────┬─┼─────────────────┼─────────────────┼─────────────────┘
                   │ │                 │                 │
                   │ │                 │                 │
┌──────────────────▼─▼─────────────────▼─────────────────▼─────────────────┐
│                    Django Business Logic Layer                          │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐  │
│  │  User Service   │ Artifact Service│ Matching Service│Export Service│  │
│  │  + Profile Mgmt │                 │                 │             │  │
│  └─────────────────┼─────────────────┼─────────────────┼─────────────┘  │
└──────────────────┬─┼─────────────────┼─────────────────┼─────────────────┘
                   │ │                 │                 │
       ┌───────────▼─▼─────────────────▼─────────────────▼───────────┐
       │                    Redis (Cache + Broker + JWT Blacklist)  │
       │  ┌─────────────┬─────────────┬─────────────────────────────┐ │
       │  │   Session   │    Cache    │        Celery Queues        │ │
       │  │   Store +   │    Layer    │    (artifact, generation)   │ │
       │  │ JWT Blacklist│            │                             │ │
       │  └─────────────┴─────────────┴─────────────────────────────┘ │
       └─────────────────────┬───────────────────────────────────────┘
                             │
       ┌─────────────────────▼───────────────────────────────────────┐
       │                Celery Workers                               │
       │  ┌──────────────┬──────────────┬────────────────────────┐   │
       │  │   Artifact   │   Evidence   │     Generation         │   │
       │  │  Processor   │  Validator   │      Worker            │   │
       │  └──────────────┼──────────────┼────────────────────────┘   │
       └─────────────────┼──────────────┼────────────────────────────┘
                         │              │
┌────────────────────────▼──────────────▼────────────────────────────────┐
│                    PostgreSQL Database                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────────────┐ │
│  │ auth_user   │ artifacts   │ evidence    │ generated_documents     │ │
│  │ (extended)  │ labels      │ links       │ export_logs             │ │
│  │ sessions    │ skills      │ validations │ job_descriptions        │ │
│  │ jwt_tokens  │             │             │ token_blacklist         │ │
│  └─────────────┴─────────────┴─────────────┴─────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

### Component Inventory

| Component | Framework/Runtime | Purpose | Interfaces (in/out) | Depends On | Scale/HA | Owner |
|-----------|------------------|---------|-------------------|------------|----------|-------|
| API Gateway | Django + Gunicorn + uv | HTTP request routing, middleware | In: HTTP/HTTPS; Out: DB, Redis, Celery | Redis, PostgreSQL | 5+ replicas behind LB | Backend |
| JWT Auth System | Django-Rest-Framework-SimpleJWT | Token-based authentication, user management | In: Auth requests; Out: JWT tokens, Redis blacklist | Redis, PostgreSQL | Stateless, auto-scale | Backend |
| Auth ViewSets | Django DRF + Custom User Model | Registration, login, logout, profile management | In: Auth requests; Out: JWT tokens, user data | Redis, PostgreSQL | Stateless, auto-scale | Backend |
| Artifact ViewSets | Django DRF | CRUD for artifacts and evidence | In: REST API calls; Out: DB queries, Celery tasks | PostgreSQL, Redis, Celery | Stateless, auto-scale | Backend |
| Generation ViewSets | Django DRF | CV/cover letter generation orchestration | In: Generation requests; Out: Celery tasks, cached results | Redis, Celery, PostgreSQL | Stateless, async processing | Backend |
| Export ViewSets | Django DRF | Document format export (PDF/Docx) | In: Export requests; Out: Binary file streams | PostgreSQL, Redis | CPU-intensive, separate scaling | Backend |
| Business Logic | Django Services | Core domain logic, validation | In: ViewSet calls; Out: Model operations | PostgreSQL, Redis | Embedded in API processes | Backend |
| JWT Token Blacklist | SimpleJWT + Redis | Secure logout and token revocation | In: Token blacklist operations; Out: Token validation status | Redis | High availability, persistent | Backend |
| Custom User Model | Django AbstractUser | Extended user profiles with preferences | In: User operations; Out: User data with profile fields | PostgreSQL | Embedded in Django processes | Backend |
| Redis Cache | Redis 7 | API response caching, session storage, JWT blacklist | In: Cache operations; Out: Cached data | - | Primary + replica, persistent | DevOps |
| Redis Broker | Redis 7 | Celery task queue management | In: Task submissions; Out: Task delivery | - | Same instance as cache | DevOps |
| Celery Workers | Celery + Python + uv | Async task processing | In: Queue messages; Out: DB updates, external API calls | Redis, PostgreSQL, LLM APIs | Auto-scale by queue depth | Backend |
| PostgreSQL | PostgreSQL 15 | Primary data persistence | In: SQL queries; Out: ACID-compliant results | - | Primary + read replicas | DevOps |

## Interfaces & Data Contracts

### Authentication Endpoints

#### Core Authentication

**User Registration**
```
POST /api/v1/auth/register/
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  // Note: username is auto-generated from email (cannot be customized during registration)
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}

Response: 201 Created
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user@example.com",  // Auto-generated from email
    "first_name": "John",
    "last_name": "Doe",
    // ... plus optional profile fields: profile_image, phone, linkedin_url, github_url,
    // website_url, bio, location, preferred_cv_template, email_notifications
    "created_at": "2025-09-23T10:00:00Z",
    "updated_at": "2025-09-23T10:00:00Z"
  },
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Error Response: 400 Bad Request
{
  "email": ["A user with this email already exists."],
  "password": ["This password is too short. It must contain at least 8 characters."],
  "password_confirm": ["Passwords don't match."]
}
```

**User Login**
```
POST /api/v1/auth/login/
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response: 200 OK
{
  "user": {...},
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Error Response: 400 Bad Request
{
  "error": "Invalid credentials"
}
```

**Token Refresh**
```
POST /api/v1/auth/token/refresh/
Content-Type: application/json

Request Body:
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response: 200 OK
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**User Logout**
```
POST /api/v1/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

Request Body:
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response: 200 OK
{
  "message": "Successfully logged out"
}
```

#### Password Management

**Change Password**
```
POST /api/v1/auth/change-password/
Authorization: Bearer <access_token>
Content-Type: application/json

Request Body:
{
  "old_password": "currentpassword123",
  "new_password": "newpassword456",
  "new_password_confirm": "newpassword456"
}

Response: 200 OK
{
  "message": "Password changed successfully"
}

Error Response: 400 Bad Request
{
  "old_password": ["Current password is incorrect"],
  "new_password": ["This password is too short. It must contain at least 8 characters."]
}
```

**Password Reset Request**
```
POST /api/v1/auth/password-reset/
Content-Type: application/json

Request Body:
{
  "email": "user@example.com"
}

Response: 200 OK
{
  "message": "Password reset email sent if account exists"
}

// Note: Returns success even if email doesn't exist (security best practice)
```

#### OAuth Integration

**Google OAuth Login**
```
POST /api/v1/auth/google/
Content-Type: application/json

Request Body:
{
  "access_token": "ya29.a0AfH6SMB...",  // Google OAuth access token
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE..."  // Google ID token
}

Response: 200 OK
{
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "username": "user@gmail.com",
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": "https://lh3.googleusercontent.com/..."
  },
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "is_new_user": false
}

Error Response: 400 Bad Request
{
  "error": "Invalid Google token"
}
```

**Link Google Account**
```
POST /api/v1/auth/google/link/
Authorization: Bearer <access_token>
Content-Type: application/json

Request Body:
{
  "access_token": "ya29.a0AfH6SMB...",
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE..."
}

Response: 200 OK
{
  "message": "Google account linked successfully",
  "google_email": "user@gmail.com"
}

Error Response: 400 Bad Request
{
  "error": "Google account already linked to another user"
}
```

**Unlink Google Account**
```
POST /api/v1/auth/google/unlink/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "message": "Google account unlinked successfully"
}

Error Response: 400 Bad Request
{
  "error": "No Google account linked to this user"
}
```

#### User Profile Management

**Get User Profile**
```
GET /api/v1/auth/profile/
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": 1,
  "email": "user@example.com",
  "username": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "profile_image": "https://...",
  "phone": "+1234567890",
  "linkedin_url": "https://linkedin.com/in/...",
  "github_url": "https://github.com/...",
  "website_url": "https://...",
  "bio": "Software engineer with 5 years experience...",
  "location": "San Francisco, CA",
  "preferred_cv_template": "modern",
  "email_notifications": true,
  "created_at": "2025-09-23T10:00:00Z",
  "updated_at": "2025-10-15T14:30:00Z"
}
```

### Artifact Management Endpoints

#### Evidence Types (Simplified in v4.0.0)
Starting in API v4.0.0, only two evidence types are supported for focused artifact verification:
- **`github`**: GitHub Repository links (for code projects and contributions)
- **`document`**: Uploaded PDF files (for project documentation, publications, certifications)

**Deprecated evidence types** (removed in v4.0.0):
- `live_app`, `video`, `audio`, `website`, `portfolio`, `other`

**Rationale**: Narrowing to two core evidence types (code repositories and documents) simplifies the user experience, reduces processing complexity, and focuses on the most valuable proof sources for technical portfolios.

#### Artifact CRUD Operations
```
POST /api/v1/artifacts/
Headers: Authorization: Bearer <token>
Body: {
  title: string,
  description: string,
  user_context: string?,                    // NEW (v4.1.0): Optional user-provided enrichment context
  start_date: date,
  end_date: date?,
  technologies: string[],
  collaborators: string[],
  evidence_links: [{
    url: string,
    evidence_type: enum('github' | 'document'),
    description: string
  }]
}
Response: 202 {artifact_id, status: "processing", task_id}

GET /api/v1/artifacts/
Headers: Authorization: Bearer <token>
Query: ?page=1&limit=20&label=<label_id>&tech=<tech_name>
Response: 200 {artifacts: [...], pagination: {...}}
// Each artifact now includes user_context field (v4.1.0)

PUT /api/v1/artifacts/{artifact_id}/
PATCH /api/v1/artifacts/{artifact_id}/
// Both accept user_context for editing (v4.1.0)
Body: {
  title: string?,
  description: string?,
  user_context: string?,                    // NEW (v4.1.0): Editable by user
  // ... other fields
}

DELETE /api/v1/artifacts/{artifact_id}/
```

#### Artifact Selection & Ranking

**Feature Reference:** ADR-028 (Keyword-Based Ranking)

**Get Artifact Suggestions**
```
GET /api/v1/artifacts/suggestions/
Authorization: Bearer <token>
Query: ?keywords=<comma-separated>&limit=<int>
Response: 200 {
  artifacts: [
    {
      artifact_id: int,
      title: string,
      relevance_score: float,  // 0.0-1.0 based on keyword matching
      matched_keywords: string[],
      technologies: string[]
    }
  ],
  total_results: int
}

// Returns keyword-ranked artifacts based on manual user selection
// Does NOT auto-select artifacts (ADR-028)
```

**Get Job-Specific Suggestions**
```
GET /api/v1/artifacts/suggest-for-job/
Authorization: Bearer <token>
Query: ?job_description=<text>&limit=<int>
Response: 200 {
  artifacts: [
    {
      artifact_id: int,
      title: string,
      relevance_score: float,
      matched_skills: string[],
      recommendation_reason: string
    }
  ],
  extracted_keywords: string[],
  total_results: int
}

// Parses job description and ranks artifacts by keyword relevance
// User still manually selects which artifacts to use (ADR-028)
```

#### Artifact Enrichment

**Feature References:** ft-005 (Evidence-Based Enrichment), ft-018 (User Context Preservation)

**Trigger Enrichment** (ft-005)
```
POST /api/v1/artifacts/{artifact_id}/enrich/
Authorization: Bearer <token>
Response: 202 {
  artifact_id: int,
  status: "processing",
  task_id: string,
  message: "Enrichment started for artifact"
}

// Triggers async enrichment process that:
// 1. Extracts content from evidence links (GitHub repos, PDFs)
// 2. Generates unified_description via LLM
// 3. Extracts enriched_achievements with metrics
// 4. Preserves user_context (immutable during enrichment, ft-018)
```

**Check Enrichment Status**
```
GET /api/v1/artifacts/{artifact_id}/enrichment-status/
Authorization: Bearer <token>
Response: 200 {
  artifact_id: int,
  enrichment_status: "not_started" | "processing" | "completed" | "failed" | "partial",
  progress_percentage: int,
  started_at: timestamp?,
  completed_at: timestamp?,
  error_message: string?,
  evidence_processed: int,
  evidence_total: int
}
```

**Edit AI-Enriched Content** (ft-018)
```
PUT /api/v1/artifacts/{artifact_id}/enriched-content/
Authorization: Bearer <token>
Body: {
  unified_description: string?,      // Edit AI-generated description
  enriched_achievements: string[]?   // Edit AI-extracted achievements
}
Response: 200 {
  artifact_id: int,
  unified_description: string,
  enriched_achievements: string[],
  last_edited_at: timestamp,
  message: "Enriched content updated successfully"
}

// Note: user_context field is edited separately via PATCH /api/v1/artifacts/{artifact_id}/
// and is preserved during enrichment (immutable by AI)
```

**Debug Enrichment Data**
```
GET /api/v1/artifacts/{artifact_id}/enrichment-debug/
Authorization: Bearer <token>
Response: 200 {
  artifact_id: int,
  user_context: string,              // User-provided (immutable)
  unified_description: string,       // AI-generated from evidence
  enriched_achievements: string[],   // AI-extracted metrics
  description: string,               // Original description
  evidence_summary: {
    total_evidence_links: int,
    github_repos: int,
    documents: int,
    validated: int,
    failed: int
  },
  enrichment_metadata: {
    model_used: string,
    tokens_consumed: int,
    processing_time_ms: int
  }
}
```

#### Evidence Management

**Add Evidence Link**
```
POST /api/v1/artifacts/{artifact_id}/evidence-links/
Authorization: Bearer <token>
Body: {
  url: string,
  evidence_type: "github" | "document",
  description: string?
}
Response: 201 {
  id: int,
  artifact_id: int,
  url: string,
  evidence_type: string,
  description: string,
  validation_status: "pending" | "valid" | "invalid",
  created_at: timestamp
}
```

**Update Evidence Link**
```
PUT /api/v1/artifacts/evidence-links/{link_id}/
Authorization: Bearer <token>
Body: {
  url: string?,
  description: string?
}
Response: 200 {
  id: int,
  artifact_id: int,
  url: string,
  description: string,
  updated_at: timestamp
}
```

**Delete Evidence Link**
```
DELETE /api/v1/artifacts/evidence-links/{link_id}/
Authorization: Bearer <token>
Response: 204 No Content
```

**Validate Evidence Links** (Batch validation)
```
POST /api/v1/artifacts/validate-evidence-links/
Authorization: Bearer <token>
Body: {
  links: [
    {
      url: string,
      evidence_type: "github" | "document"
    }
  ]
}
Response: 200 {
  results: [
    {
      url: string,
      is_valid: boolean,
      validation_message: string,
      evidence_type: string,
      metadata: {
        repo_name: string?,      // For GitHub repos
        stars: int?,             // For GitHub repos
        file_type: string?,      // For documents
        file_size_bytes: int?    // For documents
      }
    }
  ]
}
```

**Upload Artifact File** (PDF/Document evidence)
```
POST /api/v1/artifacts/upload-file/
Authorization: Bearer <token>
Content-Type: multipart/form-data
Body: {
  file: <binary>,
  artifact_id: int?,  // Optional: attach to existing artifact
  description: string?
}
Response: 201 {
  file_id: int,
  artifact_id: int?,
  file_name: string,
  file_size_bytes: int,
  file_type: string,
  upload_url: string,
  created_at: timestamp
}
```

**Delete Uploaded File**
```
DELETE /api/v1/artifacts/files/{file_id}/
Authorization: Bearer <access_token>
Response: 204 No Content
```

#### Evidence Review & Acceptance (ft-045)

**Feature Reference:** ft-045 (Evidence Review Workflow), ADR-045 (Blocking Wizard Review)

**Finalize Evidence Review** (Re-unify artifact from accepted evidence)
```
POST /api/v1/artifacts/{artifact_id}/finalize-evidence-review/
Authorization: Bearer <token>
Response: 200 {
  artifact_id: int,
  unified_description: string,      // Re-generated from accepted evidence
  enriched_technologies: string[],  // Re-unified from accepted evidence
  enriched_achievements: string[],  // Re-unified from accepted evidence
  processing_confidence: float,     // Overall confidence (0.0-1.0)
  evidence_acceptance_summary: {
    total_evidence: int,
    accepted: int,
    rejected: int,
    pending: int
  },
  message: "Artifact content re-unified from accepted evidence"
}

Error Responses:
- 400: Not all evidence accepted (returns list of unaccepted evidence IDs)
- 500: LLM re-unification failed (circuit breaker open, API error)

// Triggers re-unification of artifact content using user-edited and accepted EnhancedEvidence
// Uses reunify_from_accepted_evidence() service method
// Requires ALL evidence to be accepted (accepted=True) before proceeding
// Generates new unified_description using GPT-5 LLM unification
```

**Edit Evidence Content**
```
PATCH /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/content/
Authorization: Bearer <token>
Body: {
  processed_content: {
    summary: string?,              // Edit AI-extracted summary
    technologies: string[]?,       // Add/remove technologies
    achievements: string[]?        // Edit/remove achievements
  }
}
Response: 200 {
  evidence_id: int,
  artifact_id: int,
  processed_content: {
    summary: string,
    technologies: string[],
    achievements: string[],
    metrics: object[]
  },
  processing_confidence: float,
  last_edited_at: timestamp,
  message: "Evidence content updated successfully"
}

// Allows inline editing of AI-extracted evidence content
// Changes are used during re-unification (finalize-evidence-review)
```

**Accept Evidence**
```
POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/accept/
Authorization: Bearer <token>
Body: {
  review_notes: string?  // Optional user comments about review
}
Response: 200 {
  evidence_id: int,
  artifact_id: int,
  accepted: true,
  accepted_at: timestamp,
  accepted_by: int,  // User ID
  review_notes: string?,
  message: "Evidence accepted"
}

// Marks evidence as accepted after user review
// Required before finalize-evidence-review
```

**Reject Evidence**
```
POST /api/v1/artifacts/{artifact_id}/evidence/{evidence_id}/reject/
Authorization: Bearer <token>
Body: {
  review_notes: string?  // Optional reason for rejection
}
Response: 200 {
  evidence_id: int,
  artifact_id: int,
  rejected: true,
  rejected_at: timestamp,
  review_notes: string?,
  message: "Evidence rejected"
}

// Marks evidence as rejected (will not be used in unification)
// Constraint: Cannot be both accepted AND rejected
```

**Get Evidence Acceptance Status**
```
GET /api/v1/artifacts/{artifact_id}/evidence-acceptance-status/
Authorization: Bearer <token>
Response: 200 {
  artifact_id: int,
  can_finalize: boolean,          // True if all evidence accepted
  acceptance_summary: {
    total_evidence: int,
    accepted: int,
    rejected: int,
    pending: int
  },
  evidence_details: [
    {
      evidence_id: int,
      evidence_type: string,
      url: string,
      accepted: boolean,
      rejected: boolean,
      processing_confidence: float,
      accepted_at: timestamp?,
      review_notes: string?
    }
  ]
}

// Returns acceptance status for all evidence in artifact
// Used by frontend to enable/disable finalization button
```

**Accept Final Artifact** (ft-046 - Step 6 Phase 2 of 6-step wizard)
```
POST /api/v1/artifacts/{artifact_id}/accept-artifact/
Authorization: Bearer <token>
Response: 200 {
  message: "Artifact accepted successfully",
  artifactId: int,
  status: "complete"
}

Error Responses:
- 400: Artifact not in review_finalized state (returns current status)
- 404: Artifact not found

// Final artifact acceptance after reunification (Step 6 Phase 2 of 6-step wizard)
// Preconditions:
//   - Artifact must have status='review_finalized' (Phase 2 reunification complete)
//   - Artifact must belong to the requesting user
// Actions:
//   - Sets artifact.status='complete'
//   - Sets artifact.wizard_completed_at=now()
//   - Sets artifact.last_wizard_step=6 (wizard complete)
// This is the final step in the evidence review workflow
```

**See also:** Evidence link management for URL-based evidence (GitHub repos, online documents)

### Generation Endpoints

#### Two-Phase CV Generation Workflow (ft-009)

**Phase 1: Bullet Preparation**
```
POST /api/v1/generations/create/
Body: {
  job_description: string,
  company_name: string,
  role_title: string,
  label_ids: int[],
  template_id: int?,
  custom_sections: object?
}
Response: 202 {
  generation_id: uuid,
  status: "pending",
  workflow: "two_phase",
  next_step: "Review bullets at GET /api/v1/generations/{generation_id}/bullets/",
  estimated_bullet_completion: timestamp,
  job_description_hash: string
}
```

**Phase 1 Result: Review Generated Bullets**
```
GET /api/v1/generations/{generation_id}/bullets/
Query: ?artifact_id=<int>  // Optional: filter bullets by specific artifact (ADR-038)
Response: 200 {
  generation_id: uuid,
  status: "bullets_ready",
  bullets_by_artifact: [
    {
      artifact_id: int,
      artifact_title: string,
      bullets: [
        {
          id: int,
          text: string,
          position: int,
          bullet_type: "achievement" | "technical" | "impact",
          quality_score: float,  // 0.0-1.0 validation score from bullet_validation_service (ft-030)
          user_edited: boolean,
          user_approved: boolean
        }
      ]
    }
  ],
  total_bullets: int,
  next_step: "Edit bullets or approve with POST /api/v1/generations/{generation_id}/bullets/approve/"
}
```

**Edit Individual Bullet**
```
PATCH /api/v1/generations/{generation_id}/bullets/{bullet_id}/
Body: {
  text: string  // 60-150 characters
}
Response: 200 {
  id: int,
  text: string,
  user_edited: true,
  original_text: string
}
```

**Approve Bullets (ft-024: Supports individual actions)**
```
POST /api/v1/generations/{generation_id}/bullets/approve/
Body: {
  bullet_actions: [  // NEW (v4.3.0): Per-bullet actions
    {
      bullet_id: int,
      action: "approve" | "reject" | "edit",
      edited_text: string?  // Required if action == "edit"
    }
  ]
}
Response: 200 {
  generation_id: uuid,
  status: "bullets_approved",
  bullets_approved: int,
  bullets_edited: int,
  bullets_rejected: int,
  next_step: "Assemble generation with POST /api/v1/generations/{generation_id}/assemble/"
}
```

**Phase 2: Document Assembly**
```
POST /api/v1/generations/{generation_id}/assemble/
Precondition: status == "bullets_approved"
Response: 202 {
  generation_id: uuid,
  status: "assembling",
  message: "Document assembly started"
}
```

**Check Generation Status (Unified Status Endpoint)**
```
GET /api/v1/generations/{generation_id}/generation-status/
Response: 200 {
  generation_id: uuid,
  status: "pending" | "processing" | "bullets_ready" | "bullets_approved" | "assembling" | "completed" | "failed",
  progress_percentage: int,
  error_message: string?,
  created_at: timestamp,
  completed_at: timestamp?,

  // Phase tracking (two-phase workflow)
  current_phase: "bullet_generation" | "bullet_review" | "assembly" | "completed",
  phase_details: {
    bullet_generation: {
      status: "pending" | "in_progress" | "completed" | "partial",
      artifacts_total: int,
      artifacts_processed: int,
      bullets_generated: int,
      started_at: timestamp?,
      completed_at: timestamp?
    },
    assembly: {
      status: "not_started" | "in_progress" | "completed" | "failed",
      started_at: timestamp?,
      completed_at: timestamp?
    }
  },

  // Sub-job aggregation (bullet generation jobs)
  bullet_generation_jobs: [
    {
      job_id: uuid,
      artifact_id: int,
      artifact_title: string,
      status: "pending" | "processing" | "completed" | "failed" | "needs_review",
      bullets_generated: int,
      processing_duration_ms: int?,
      error_message: string?
    }
  ],

  // Processing metrics (if completed or in-progress)
  processing_metrics: {
    total_duration_ms: int?,
    total_cost_usd: float?,
    total_tokens_used: int?,
    model_version: string?
  },

  // Quality metrics (if bullets_ready or later)
  quality_metrics: {
    average_bullet_quality: float?,
    average_keyword_relevance: float?,
    bullets_approved: int?,
    bullets_rejected: int?,
    bullets_edited: int?
  }
}

// NOTE: This endpoint provides comprehensive status for all generation-related
// operations including GeneratedDocument status, BulletGenerationJob statuses,
// and aggregated metrics. Frontend should poll this endpoint during generation
// instead of GET /api/v1/generations/{generation_id}/
```

**Get Full Generation Document**
```
GET /api/v1/generations/{generation_id}/
Response: 200 {
  id: uuid,
  status: "pending" | "processing" | "bullets_ready" | "bullets_approved" | "assembling" | "completed" | "failed",
  content: object?,  // null until status == "completed"
  artifacts_used: int[],
  created_at: timestamp,
  completed_at: timestamp?,
  job_description_hash: string,
  progress_percentage: int
}

// NOTE: Use this endpoint to retrieve complete CV content after generation is
// complete. For status polling during generation, use /generation-status/ instead.
```

**Multi-Source Content Assembly** (ft-024)

Bullet generation uses a hybrid approach combining multiple artifact data sources:
- `user_context` - User-provided context (ft-018, immutable during enrichment)
- `unified_description` - AI-enhanced description from evidence sources (ft-005)
- `enriched_achievements` - Extracted achievements with metrics (ft-005)
- Fallback to `description` if enriched data unavailable

This multi-source assembly provides richer context to the LLM, resulting in higher-quality bullets. Applied automatically to both initial generation (Phase 1) and regeneration.

**Regenerate Bullets with Refinement Prompt**
```
POST /api/v1/generations/{generation_id}/bullets/regenerate/
Authorization: Bearer {access_token}
Body: {
  refinement_prompt: string?,  // Optional temporary hint (NOT persisted, ADR-036)
  bullet_ids_to_regenerate: int[]?  // Optional: regenerate specific bullets only, or all if omitted
  artifact_ids: int[]?  // Optional: regenerate bullets for specific artifacts only
}
Response: 202 {
  generation_id: uuid,
  status: "processing",
  bullets_to_regenerate: int,  // Count of bullets being regenerated
  message: "Bullet regeneration started",
  estimated_completion: timestamp
}

// Refinement Prompt Examples:
// - "Focus more on leadership and team management"
// - "Add specific metrics and quantifiable achievements"
// - "Emphasize technical depth over business impact"
// - "Use more action verbs and reduce generic language"
```

#### Cover Letter Generation

**Generate Cover Letter**
```
POST /api/v1/generations/cover-letter/
Authorization: Bearer <access_token>
Body: {
  job_description: string,
  company_name: string,
  role_title: string,
  hiring_manager_name: string?,
  custom_introduction: string?,
  artifact_ids: int[]
}
Response: 202 {
  cover_letter_id: uuid,
  status: "processing",
  message: "Cover letter generation started",
  estimated_completion: timestamp
}
```

**See also:** Two-Phase CV Generation Workflow for similar async generation process

#### Generation Management

**List All Generations**
```
GET /api/v1/generations/
Authorization: Bearer <access_token>
Query: ?page=1&limit=20&status=<status>&sort=<field>
Response: 200 {
  generations: [
    {
      id: uuid,
      company_name: string,
      role_title: string,
      status: string,
      created_at: timestamp,
      completed_at: timestamp?,
      artifacts_count: int
    }
  ],
  pagination: {
    page: int,
    limit: int,
    total: int,
    total_pages: int
  }
}
```

**Get Generation Templates**
```
GET /api/v1/generations/templates/
Authorization: Bearer <access_token>
Response: 200 {
  templates: [
    {
      id: int,
      name: string,
      description: string,
      preview_url: string,
      category: "modern" | "classic" | "professional" | "creative",
      is_premium: boolean
    }
  ]
}
```

#### Quality Control

**Rate Generation Quality**
```
POST /api/v1/generations/{generation_id}/rate/
Authorization: Bearer <access_token>
Body: {
  rating: int,  // 1-5 stars
  feedback: string?,
  categories: {
    content_quality: int?,  // 1-5
    relevance: int?,        // 1-5
    formatting: int?        // 1-5
  }
}
Response: 200 {
  generation_id: uuid,
  rating: int,
  message: "Rating submitted successfully"
}
```

**Validate Bullet Points** (Standalone validation)
```
POST /api/v1/generations/bullets/validate/
Authorization: Bearer <access_token>
Body: {
  bullets: [
    {
      text: string,
      bullet_type: "achievement" | "technical" | "impact"
    }
  ],
  job_keywords: string[]?  // Optional: for keyword relevance scoring
}
Response: 200 {
  validation_results: [
    {
      text: string,
      is_valid: boolean,
      quality_score: float,
      issues: string[],
      suggestions: string[]
    }
  ],
  overall_quality: float
}
```

**See also:** Two-Phase CV Generation Workflow for bullet generation and review process

#### Generation Analytics

**Get Generation Analytics**
```
GET /api/v1/generations/analytics/
Authorization: Bearer <access_token>
Query: ?start_date=<date>&end_date=<date>
Response: 200 {
  total_generations: int,
  successful_generations: int,
  failed_generations: int,
  average_processing_time_seconds: float,
  total_tokens_used: int,
  total_cost_usd: float,
  generations_by_status: {
    completed: int,
    processing: int,
    failed: int,
    bullets_ready: int
  },
  most_used_artifacts: [
    {
      artifact_id: int,
      artifact_title: string,
      usage_count: int
    }
  ]
}
```

### Export Endpoints

#### Export Operations

**Create Export**
```
POST /api/v1/export/create/{generation_id}/
Authorization: Bearer <access_token>
Body: {
  format: "pdf" | "docx",
  include_evidence: boolean,
  qr_codes: boolean
}
Response: 202 {
  export_id: uuid,
  status: "processing"
}
```

**Get Export Details**
```
GET /api/v1/export/{export_id}/
Authorization: Bearer <access_token>
Response: 200 {
  id: uuid,
  format: "pdf" | "docx",
  status: "processing" | "completed" | "failed",
  created_at: timestamp,
  completed_at: timestamp?,
  file_path: string?,
  download_url: string?  // Available when status == "completed"
}
```

**Get Export Status**
```
GET /api/v1/export/{export_id}/status/
Authorization: Bearer <access_token>
Response: 200 {
  export_id: uuid,
  status: "processing" | "completed" | "failed",
  progress_percentage: int,
  estimated_completion: timestamp?
}
```

**Download Export**
```
GET /api/v1/export/{export_id}/download/
Authorization: Bearer <access_token>
Response: 200 {
  Content-Type: application/pdf | application/vnd.openxmlformats-officedocument.wordprocessingml.document,
  Content-Disposition: attachment; filename="cv_generated.pdf"
}
```

**List All Exports**
```
GET /api/v1/export/
Authorization: Bearer <access_token>
Query: ?page=1&limit=20&format=<format>&status=<status>
Response: 200 {
  exports: [
    {
      id: uuid,
      generation_id: uuid,
      format: "pdf" | "docx",
      status: "processing" | "completed" | "failed",
      created_at: timestamp,
      completed_at: timestamp?,
      file_size_bytes: int?,
      download_url: string?
    }
  ],
  pagination: {
    page: int,
    limit: int,
    total: int,
    total_pages: int
  }
}
```

#### Export Configuration

**Get Export Templates**
```
GET /api/v1/export/templates/
Authorization: Bearer <access_token>
Response: 200 {
  templates: [
    {
      id: int,
      name: string,
      description: string,
      format: "pdf" | "docx",
      preview_url: string,
      supports_evidence: boolean,
      supports_qr_codes: boolean
    }
  ]
}
```

#### Export Analytics

**Get Export Analytics**
```
GET /api/v1/export/analytics/
Authorization: Bearer <access_token>
Query: ?start_date=<date>&end_date=<date>
Response: 200 {
  total_exports: int,
  successful_exports: int,
  failed_exports: int,
  exports_by_format: {
    pdf: int,
    docx: int
  },
  average_processing_time_seconds: float,
  total_file_size_mb: float
}
```

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "field_errors": {
        "email": ["This field is required"],
        "evidence_links": ["URL validation failed for: https://invalid-url"]
      }
    },
    "request_id": "req_123456789"
  }
}
```

## Data & Storage

### Database Schema

**See complete schema documentation:** [`docs/specs/spec-database-schema.md`](spec-database-schema.md)

The API uses PostgreSQL 15+ with Django ORM for data persistence. Key tables supporting API functionality:

- **accounts_user**: Extended user model with profile fields, authentication data
- **token_blacklist_***: JWT token management and blacklist for secure logout
- **artifacts_artifact**: Work artifacts with metadata and enrichment fields
- **evidence**: Evidence links (GitHub repos, PDF uploads) with validation status
- **generation_generateddocument**: Generated CVs and cover letters
- **generation_bullet_point**: Individual bullet points with quality metrics
- **export_exportjob**: Document export jobs with progress tracking

For complete table definitions, relationships, field-level details, constraints, and indexes, refer to [`spec-database-schema.md`](spec-database-schema.md) which serves as the authoritative source of truth.

## Security & Privacy

### Network Security & Transport Layer

**Production Environment:**
- **HTTPS Enforcement:** TLS 1.2+ required for all API requests
- **Custom Domain:** `https://api.<YOUR_DOMAIN>`
- **Certificate:** AWS Certificate Manager (ACM) with automatic renewal
- **Load Balancer:** Application Load Balancer (ALB) with health checks and SSL termination
- **CORS Configuration:** Strict origin whitelisting in Django settings
  ```python
  CORS_ALLOWED_ORIGINS = [
      'https://<YOUR_DOMAIN>',
      'https://www.<YOUR_DOMAIN>',
      'https://<YOUR_CLOUDFRONT_DOMAIN>',  # CloudFront fallback
  ]
  CORS_ALLOW_CREDENTIALS = True
  ```

**Development Environment:**
- **HTTP Only:** `http://localhost:8000` (Django dev server)
- **CORS:** Wildcard allowed for local development

### CSRF Protection

Django CSRF protection enabled for all state-changing requests (POST, PUT, PATCH, DELETE). Frontend reads `csrftoken` cookie and includes it in `X-CSRFToken` header. GET and OPTIONS requests exempt.

**See implementation:** `frontend/src/services/apiClient.ts` for cookie reading and header injection logic.

### JWT Token Security
- **Access token lifetime**: 60 minutes (configurable via `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']`)
- **Refresh token lifetime**: 7 days (configurable via `SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']`)
- **Automatic token rotation**: On refresh, both access and refresh tokens renewed
- **Token blacklisting**: On logout, refresh tokens blacklisted via Redis
- **Automatic cleanup**: Expired tokens cleaned up by Celery periodic task

### Password Validation
- Minimum length: 8 characters
- User attribute similarity validation
- Common password validation (against top 20,000 passwords)
- Numeric password validation

## Reliability & SLIs/SLOs

### Service Level Indicators
- **Authentication Availability:** Percentage of successful auth endpoint responses (non-5xx)
- **Token Validation Latency:** P50, P95, P99 for JWT token validation
- **Registration Success Rate:** Percentage of successful user registrations
- **Login Success Rate:** Percentage of successful user logins (excluding invalid credentials)

### Service Level Objectives
- **Authentication Availability:** ≥99.9% for auth endpoints (login, register, token refresh)
- **Authentication Latency Targets:**
  - User registration: P95 ≤1s
  - User login: P95 ≤500ms
  - Token refresh: P95 ≤200ms
  - Profile operations: P95 ≤300ms
- **Token Security:** 100% token blacklist effectiveness for logged out sessions
- **Data Consistency:** ≥99.9% user profile integrity

### Reliability Mechanisms

- **Rate Limiting**: Authentication endpoints protected by `django-ratelimit` (5/min for login, 3/min for registration)
- **Circuit Breaker**: Token validation uses circuit breaker pattern (failure threshold: 10, timeout: 30s)
- **Token Cleanup**: Expired tokens automatically cleaned by Celery periodic tasks
- **Health Checks**: ALB health checks on `/api/health/` endpoint

**See implementation:** `backend/accounts/views.py` and `llm_services/services/reliability/circuit_breaker.py`

## Evaluation Plan

### Authentication Testing Strategy
- Complete auth flow tests: registration → login → profile access → logout
- Token blacklist verification
- Load testing with 10,000 concurrent users
- Security testing: brute force, injection, session fixation
