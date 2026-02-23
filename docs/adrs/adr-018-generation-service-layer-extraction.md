# ADR — Service Layer Extraction for Generation Module

**Status:** Accepted
**Date:** 2025-10-01
**Deciders:** Engineering Team
**Technical Story:** Implement ft-006 three-bullets-per-artifact feature with clean architecture

## Context and Problem Statement

The `generation/` module currently follows traditional Django patterns with business logic embedded in views (277 lines in views.py). In contrast, the `llm_services/` module demonstrates best practices with a well-architected service layer (base → core → infrastructure → reliability).

To implement ft-006 (three-bullets-per-artifact) cleanly and maintainably, we need to decide whether to:
1. Continue embedding logic in views/serializers
2. Extract service layer following `llm_services/` pattern
3. Use a hybrid approach

**Current Pain Points:**
- Business logic mixed with presentation layer (views.py:20-277)
- Difficult to test business logic in isolation
- Cannot reuse generation logic outside HTTP context
- Hard to maintain as feature complexity grows
- Inconsistent architecture across backend modules

## Decision Drivers

- **Maintainability:** Need clean separation of concerns for growing feature set
- **Testability:** Bullet generation requires extensive unit testing
- **Reusability:** Generation logic needed in views, tasks, and CLI tools
- **Consistency:** Align with proven `llm_services/` architecture
- **Team Velocity:** Clear patterns enable faster feature development
- **Code Quality:** ARCHITECTURE.md identifies service extraction as "HIGH PRIORITY"

## Considered Options

### Option A: Keep Logic in Views (Status Quo)
- **Approach:** Continue mixing business logic with HTTP handling
- **Pros:** No refactoring needed, familiar Django pattern, quick for simple CRUD
- **Cons:** Poor testability, tight coupling, code duplication, doesn't scale with complexity

### Option B: Full Service Layer Extraction (Recommended)
- **Approach:** Create `generation/services/` following `llm_services/` pattern
- **Pros:** Clean architecture, testable, reusable, consistent with best practices
- **Cons:** Requires refactoring existing code, more files to manage

### Option C: Hybrid - Services Only for New Features
- **Approach:** Keep existing views, add services for ft-006 only
- **Pros:** Less initial refactoring, gradual migration
- **Cons:** Inconsistent architecture, confusing for team, technical debt remains

## Decision Outcome

**Chosen Option: Option B - Full Service Layer Extraction**

### Rationale

1. **Proven Pattern:** `llm_services/` demonstrates this works well for complex LLM operations
2. **Strategic Alignment:** ARCHITECTURE.md line 193 identifies this as HIGH PRIORITY consolidation
3. **Feature Requirements:** ft-006 bullet generation requires:
   - Complex validation logic (quality scoring, semantic similarity)
   - LLM interaction orchestration
   - Multi-step workflows (generate → validate → approve)
   - Extensive unit testing
4. **Long-term Value:** Prepares codebase for future features (cover letters, skill extraction, etc.)
5. **Team Consensus:** Engineering team agrees this is the right time to refactor

### Implementation Strategy

```
generation/
├── services/
│   ├── __init__.py
│   ├── bullet_generation_service.py    # NEW - Core bullet logic
│   ├── bullet_validation_service.py    # NEW - Quality validation
│   └── cv_generation_service.py        # EXTRACTED from views.py
├── validators/
│   ├── __init__.py
│   ├── bullet_validator.py             # NEW - Validation rules
│   └── quality_scorer.py               # NEW - Content scoring
├── views.py                             # REFACTORED - Thin HTTP layer only
├── tasks.py                             # UPDATED - Uses services
└── serializers.py                       # UNCHANGED - Data validation only
```

### Service Responsibilities

#### CVGenerationService
**Purpose:** Orchestrate CV generation workflow
**Methods:**
- `generate_cv_for_job(user_id, job_description, artifact_ids, preferences)` → CVDocument
- `get_generation_status(generation_id)` → GenerationStatus
- `regenerate_section(generation_id, section_name)` → UpdatedSection

**Dependencies:** TailoredContentService, ArtifactRankingService, BulletGenerationService

#### BulletGenerationService
**Purpose:** Generate exactly 3 bullets per artifact
**Methods:**
- `generate_bullets(artifact_id, job_context, regenerate=False)` → List[BulletPoint]
- `regenerate_bullet(bullet_id, refinement_prompt)` → BulletPoint

**Dependencies:** TailoredContentService, BulletValidationService, EmbeddingService

#### BulletValidationService
**Purpose:** Validate bullet quality and structure
**Methods:**
- `validate_three_bullet_structure(bullets)` → ValidationResult
- `validate_content_quality(bullet)` → float  # 0-1 score
- `check_semantic_similarity(bullets)` → List[SimilarityPair]
- `detect_generic_content(bullet)` → bool

**Dependencies:** EmbeddingService (for similarity), quality scoring algorithms

### Migration Path

**Phase 1: Create Service Stubs (Week 1, Day 1-2)**
1. Create directory structure
2. Create service classes with method stubs using `NotImplementedError`
3. Define interfaces and type hints
4. Write comprehensive docstrings

**Phase 2: Extract CV Generation (Week 1, Day 3-4)**
1. Move `generate_cv()` logic from views.py to `CVGenerationService`
2. Update views to call service methods
3. Verify existing tests still pass
4. Add service-level unit tests

**Phase 3: Implement New Services (Week 1, Day 5 - Week 2)**
1. Implement `BulletGenerationService` with TDD
2. Implement `BulletValidationService` with TDD
3. Wire services together
4. Update views to use new services

**Phase 4: Update Celery Tasks (Week 2, Day 3-4)**
1. Refactor `generate_cv_task` to use services
2. Add task-level integration tests
3. Verify async workflows

## Positive Consequences

- **Clean Architecture:** Clear separation: views (HTTP) → services (logic) → models (data)
- **Testability:** Services can be unit tested without Django test client
- **Reusability:** Same services used in views, tasks, management commands
- **Consistency:** Matches proven `llm_services/` architecture pattern
- **Team Velocity:** New features easier to add with clear patterns
- **Code Quality:** Reduces views.py from 277 to ~100 lines
- **Documentation:** Service docstrings provide clear API contracts

## Negative Consequences

- **Initial Velocity:** 2-3 days refactoring before new feature work
- **More Files:** Increased file count (services/, validators/ directories)
- **Learning Curve:** Team needs to understand service layer pattern
- **Coordination:** Need to update all code that calls generation logic

## Mitigation Strategies

### Velocity Impact
- **Parallel Work:** UI team can work on frontend while backend refactors
- **Incremental:** Extract services incrementally, maintain backward compatibility
- **Testing:** Automated tests catch regressions during refactoring

### File Management
- **Clear Structure:** Follow established `llm_services/` patterns
- **Documentation:** README in services/ explaining architecture
- **IDE Support:** Type hints enable autocomplete and navigation

### Team Adoption
- **Code Reviews:** All team members review service architecture
- **Documentation:** Update ARCHITECTURE.md with new patterns
- **Examples:** Reference `llm_services/` as working example

## Compliance and Standards

- **Follows:** ARCHITECTURE.md Phase 1 consolidation plan (lines 237-245)
- **Aligns With:** Django best practices for service-oriented architecture
- **Matches:** `llm_services/` proven architecture (SPEC-20250930)
- **Supports:** TDD workflow (rules/05-tdd.md) with testable services

## Monitoring and Success Metrics

- **Code Quality:** views.py reduced from 277 to <100 lines
- **Test Coverage:** Service layer achieves 80%+ unit test coverage
- **Team Velocity:** Feature development accelerates after refactoring
- **Bug Rate:** Separation of concerns reduces logic bugs
- **Code Reuse:** Same services used in 3+ different contexts (views, tasks, CLI)

## References

- **ARCHITECTURE.md:** Lines 193-196 identify service extraction as HIGH PRIORITY
- **llm_services Architecture:** Proven service layer pattern (lines 94-127)
- **Django Service Layer:** Two Scoops of Django, Ch. 12 - Business Logic in Services
- **SPEC-20250930:** LLM services refactoring specification

## Related ADRs

- [ADR-016-three-bullets-per-artifact](adr-016-three-bullets-per-artifact.md) - Feature requiring services
- [ADR-015-multi-source-artifact-preprocessing](adr-015-multi-source-artifact-preprocessing.md) - Preprocessing architecture

