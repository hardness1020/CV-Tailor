# Tech Specs Index

## Current Specifications

### System Architecture
- **Current**: [spec-system.md](spec-system.md) - v1.4.0 (Current)
  - Comprehensive system architecture for CV & Cover-Letter Auto-Tailor
  - Component topology with Django, React, Redis, PostgreSQL, and Celery
  - Infrastructure design supporting 10,000 concurrent users
  - **[v1.4.0]** Production deployment with CloudFront CDN, ALB, ECS Fargate, RDS, ElastiCache
  - **[v1.2.0]** AWS production deployment with CloudFront, ALB, ECS, RDS, ElastiCache
  - **[v1.1.0]** Evidence type simplification (github + document only)
  - Git tag: `spec-system-v1.4.0`

### Data & Storage
- **Current**: [spec-database-schema.md](spec-database-schema.md) - v1.2.1 (Current)
  - Complete database schema for CV Tailor with all table definitions
  - Entity relationships, field-level details, and constraints
  - **[v1.2.1]** Content reorganization with improved architectural sections (NON-BREAKING)
  - **[v1.2.0]** Codebase alignment with github_repository_analysis table (NON-BREAKING)
  - PostgreSQL 15+ with pgvector extension for vector similarity search
  - Django ORM with authoritative model files and migrations
  - Extracted from spec-system.md v1.2.0 for improved maintainability
  - Git tag: `spec-database-schema-v1.2.1`

### API Design
- **Current**: [spec-api.md](spec-api.md) - v4.8.0 (Current)
  - REST API specification using Django DRF with comprehensive JWT authentication
  - **[v4.8.0]** Latest API updates and enhancements
  - **[v4.2.0]** Production HTTPS URLs, CSRF protection, enhanced security (deployment updates)
  - **[v4.0.0]** BREAKING: Simplified evidence types to github and document only (ft-011)
  - **[v3.0.0]** Two-phase CV generation workflow with bullet review/approval endpoints (ft-009)
  - Updated authentication contracts with user profiles and token blacklisting
  - Enhanced security, password management, and error handling
  - Git tag: `spec-api-v4.8.0`

### Frontend Application
- **Current**: [spec-frontend.md](spec-frontend.md) - v2.9.0 (Current)
  - React SPA with TypeScript and Vite
  - Complete JWT authentication system with dashboard-first UX
  - **[v2.9.0]** Latest frontend updates and enhancements
  - **[v2.3.0]** CSRF protection, rate limiting, production deployment (https://<YOUR_DOMAIN>)
  - **[v2.1.0]** Simplified artifact upload UI with 2 evidence types (ft-011)
  - State management, component architecture, and PWA features
  - Git tag: `spec-frontend-v2.9.0`

### Artifact Processing
- **Current**: [spec-artifact-upload-enrichment-flow.md](spec-artifact-upload-enrichment-flow.md) - v1.6.1 (Current)
  - Artifact upload and enrichment system with automatic LLM-powered content enrichment
  - Multi-source evidence processing (files, GitHub repositories, URLs)
  - **[v1.6.1]** Latest artifact processing updates
  - **[v1.3.0]** GitHub Repository Agent with GPT-5 and hybrid file analyzer
  - Asynchronous processing with Celery, Redis queue, and status polling
  - Quality validation framework and enrichment SLOs (P95 ≤300s)
  - Features: ft-001, ft-005, ft-007, ft-012, ft-013, ft-018
  - Git tag: `spec-artifact-upload-v1.6.1`

### LLM Integration
- **Current**: [spec-llm.md](spec-llm.md) - v4.2.0 (Current)
  - Large Language Model integration architecture with **anti-hallucination system**
  - **[v4.2.0]** Latest LLM integration updates
  - **[v4.0.0]** Source attribution, verification service, enhanced prompts (2025-11-04)
  - **[v4.0.0]** BulletVerificationService for fact-checking, hallucination rate ≤5%
  - **[v3.3.0]** Embedding-free keyword ranking (ADR-028)
  - Prompt management, quality evaluation, and A/B testing
  - Multi-provider support with failover and circuit breakers
  - Git tag: `spec-llm-v4.2.0`

### CV Generation System
- **Current**: [spec-cv-generation.md](spec-cv-generation.md) - v2.5.0 (Current)
  - CV generation system with 3 bullet points per artifact
  - **[v2.5.0]** Latest generation system updates
  - Intelligent artifact selection using semantic similarity (6-8 most relevant)
  - Artifact selection, bullet point generation, and role optimization
  - Multi-source artifact preprocessing (GitHub, PDF, web, media)
  - Quality validation framework and ATS compatibility
  - Git tag: `spec-generation-v2.5.0`

## Specification Status Legend
- **Draft**: Under development, not yet approved
- **Accepted**: Approved and ready for implementation
- **Current**: Active specification being used
- **Superseded**: Replaced by newer version 

## Related Documentation
- **PRD**: [prd.md](../prds/prd.md) - Product requirements
- **Features**: [features/](../features/) - Feature specifications
- **ADRs**: [adrs/](../adrs/) - Architecture decision records
- **OP-NOTEs**: [op-notes/](../op-notes/) - Operational procedures

## Change Control
All specifications follow the versioning policy defined in [workflow rules](../../rules/00-workflow.md):
- **Minor editorial fixes**: update current file  (no version bump)
- **Material changes** (contracts/SLOs/framework/topology):
  - Increment version number (e.g., v1.3.0 → v2.0.0 for breaking changes)
    - Create Git tag: `git tag spec-<spec>-v2.0.0`
  - **Git provides history**: Use `git log`, `git blame`, `git diff` for change tracking

## Pending Spec Updates (ft-030 Anti-Hallucination)

The following specs require updates for the anti-hallucination improvements (ft-030):

**Priority 1 - Completed:**
- ✅ **spec-llm.md** → v4.2.0 (2025-11-04, updated to v4.2.0 on 2025-11-06)
  - Added source attribution schema and verification service
  - Enhanced extraction prompts with anti-inference rules
  - New SLOs for hallucination rate, verification pass rate

**Priority 2 - Pending:**
- ⏳ **spec-api.md** → v5.0.0 (planned)
  - Current: v4.8.0
  - Add review workflow endpoints (approve/reject low-confidence content)
  - Update bullet generation response schema with verification data
  - Add verification status fields to bullet point responses

- ⏳ **spec-cv-generation.md** → v3.0.0 (planned)
  - Current: v2.5.0
  - Integrate BulletVerificationService into generation workflow
  - Update bullet generation flow with verification step
  - Add user review workflow for flagged content

- ⏳ **spec-frontend.md** → v3.0.0 (planned)
  - Current: v2.9.0
  - Add confidence indicator components
  - Create review interface for flagged content
  - Update generation wizard to handle verification results
  - Add source attribution viewer component

**Note:** These updates will be completed in subsequent stages of ft-030 implementation (see ADRs 031-034 and feature spec).

## Migration Notes
- **New format**: Single living documents per scope with semantic versioning
- **Dated files**: Legacy specs (spec-YYYYMMDD-*.md) are being migrated to new format
- **Git tags**: Version history tracked via Git tags instead of file proliferation