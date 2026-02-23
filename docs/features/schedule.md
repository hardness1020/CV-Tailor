# Feature Development Schedule

## Active Features

| ID | Title | Status | Owner | Priority | Target Date | Dependencies |
|----|-------|--------|-------|----------|-------------|--------------|
| ft-000 | User Authentication & Profile Management | **Done** | Backend Team | P0 | 2025-09-23 | None |
| ft-001 | Artifact Upload System | Draft | Backend Team | P0 | TBD | ft-000 |
| ft-002 | CV Generation System | Draft | ML/Backend Team | P0 | TBD | ft-001, LLM Integration |
| ft-003 | Document Export System | Draft | Backend Team | P0 | TBD | ft-002 |
| ft-005 | Multi-Source Artifact Preprocessing | Draft | ML/Backend Team | P1 | TBD | ft-001 |
| ft-006 | Three Bullets Per Artifact Constraint | Draft | ML/Backend Team | P1 | TBD | ft-005, ft-008 |
| ft-007 | Artifact Selection Algorithm | Draft | ML/Backend Team | P1 | TBD | ft-005 |
| ft-008 | LLM Prompt Design Strategy | Draft | ML/Backend Team | P1 | TBD | ft-005 |
| ft-010 | Artifact Enrichment Validation & Quality Gates | Approved | Backend Team | P0 | 2025-10-10 | ft-005 |
| ft-012 | GPT-5 Model Migration & Registry Simplification | Draft | Backend Team | P1 | 2025-10-12 | ft-llm-003 |
| **ft-013** | **GitHub Agent-Style Traversal & Hybrid Analysis** | **In Development** | **ML/Backend Team** | **P0** | **2025-10-20** | **ft-005, ft-012** |
| **ft-015** | **Artifact Detail Page Enhancements** | **In Progress** | **Frontend Team** | **P1** | **2025-10-15** | **ft-005** |
| **ft-021** | **Collapsible Sidebar Navigation** | **In Progress** | **Frontend Team** | **P2** | **2025-10-24** | **None** |
| **ft-022** | **Unified Wizard Pattern for Multi-Step Workflows** | **In Progress** | **Frontend Team** | **P1** | **2025-10-27** | **None** |
| **ft-023** | **Celery Task Idempotency Fix** | **Implemented** | **Backend Team** | **P0** | **2025-10-27** | **ft-010** |

## Feature Status Definitions

- **Draft**: Feature specification created, not yet approved for development
- **Approved**: Feature approved and ready for development
- **In Progress**: Active development underway
- **Testing**: Feature complete, undergoing QA testing
- **Done**: Feature completed and deployed to production
- **Blocked**: Development blocked by dependencies or issues
- **Cancelled**: Feature cancelled or deprioritized

## Priority Levels

- **P0**: Critical for MVP launch
- **P1**: Important for launch but can be delayed if necessary
- **P2**: Post-launch features for immediate roadmap
- **P3**: Future features for consideration

## Milestone Planning

### MVP Launch (Phase 1)
**Target**: TBD
**Critical Features**: ft-000 ✅, ft-001, ft-002, ft-003
**Requirements**:
- ✅ User authentication and profile management
- Complete artifact upload workflow
- Basic CV generation functionality
- PDF export capability

### Enhanced Features (Phase 2)
**Target**: TBD
**Features**: Cover letter generation, advanced templates, evidence integration

### Scale and Optimization (Phase 3)
**Target**: TBD
**Features**: Performance optimization, advanced AI features, enterprise features

## Notes

- All features must complete Stages A-D (PRD, SPEC, ADR, FEATURE) before development
- Feature dependencies must be resolved before starting development
- Target dates will be set after team capacity planning
- Priority levels may be adjusted based on user feedback and business requirements

## Change Log

- 2025-10-27: Added ft-023 (Celery Task Idempotency Fix) - P0 critical bug fix for duplicate artifact enrichment tasks causing $200/month API waste
- 2025-10-24: Added ft-022 (Unified Wizard Pattern for Multi-Step Workflows) - P1 UX refactor to create reusable wizard infrastructure and unify artifact upload + CV generation flows with full-page pattern and smart cancellation
- 2025-10-24: Added ft-021 (Collapsible Sidebar Navigation) - P2 UI enhancement for desktop sidebar collapse/expand with state persistence
- 2025-10-07: Added ft-015 (Artifact Detail Page Enhancements) - P1 UI improvements for enrichment feedback, evidence content display, and PDF downloads
- 2025-10-06: Added ft-013 (GitHub Agent-Style Traversal & Hybrid Analysis) - P0 BREAKING CHANGE replacing legacy GitHub extraction with intelligent agent-based analysis
- 2025-10-05: Added ft-012 (GPT-5 Model Migration & Registry Simplification) - P1 upgrade to latest OpenAI models
- 2025-10-03: Added ft-010 (Artifact Enrichment Validation & Quality Gates) - P0 critical fix for enrichment quality issues
- 2025-09-29: Added ft-005 through ft-008 (Multi-Source Artifact Preprocessing, Three Bullets Per Artifact, Artifact Selection Algorithm, LLM Prompt Design Strategy) based on ADR decisions
- 2025-09-29: Updated feature dependencies to reflect preprocessing pipeline requirements
- 2025-09-23: Added ft-000 (User Authentication) as completed foundation feature
- 2025-09-23: Updated dependencies - ft-001 now depends on ft-000 instead of "Auth System"
- 2025-09-23: Updated MVP requirements to include completed authentication system
- 2025-09-23: Initial feature schedule created with ft-001, ft-002, ft-003
- Features created following Stage D of workflow documentation