# CV-Tailor Testing Documentation

## Quick Navigation

**New to testing in CV-Tailor?** Start here:

1. **[TDD Policy](../../rules/06-tdd/policy.md)** - Understand mandatory TDD workflow (framework-agnostic)
2. **[Test Decorators](./test-decorators.md)** - Learn Django `@tag` syntax
3. **[TDD Workflow Guide](../../rules/06-tdd/guide.md)** - Conceptual TDD guidance
4. **[Test Execution](./test-execution.md)** - Run tests with Docker + uv
5. **[Test Benchmarks](./test-benchmarks.md)** - Actual performance baselines (includes mocking compliance audit)

## Document Purposes

| Document | Purpose | Audience | Type |
|----------|---------|----------|------|
| **[rules/06-tdd/policy.md](../../rules/06-tdd/policy.md)** | Mandatory TDD requirements and quality gates | All developers | Policy (Framework-Agnostic) |
| **[rules/06-tdd/guide.md](../../rules/06-tdd/guide.md)** | Conceptual TDD workflow and decision-making | New developers | Guide (Framework-Agnostic) |
| **[docs/testing/test-decorators.md](./test-decorators.md)** | Django `@tag` decorator usage rules | Test writers | Standard (Django-Specific) |
| **[docs/testing/test-execution.md](./test-execution.md)** | Docker + uv commands, mocking patterns | Daily development | Guide (Django-Specific) |
| **[docs/testing/test-benchmarks.md](./test-benchmarks.md)** | Actual test performance baselines, mocking audit | All developers | Reference (Django-Specific) |

## Documentation Architecture

```
Testing Documentation Hierarchy:

Level 1 - POLICY (Framework-Agnostic)
├─ rules/06-tdd/policy.md
│  └─ Defines: TDD mandate, quality gates, exit criteria
│  └─ References: Project docs/testing/ for implementation

Level 2 - STANDARDS (Project-Specific)
├─ docs/testing/test-decorators.md
│  └─ Defines: Django @tag syntax, tag categories
│  └─ Implements: Categorization requirements from policy.md

Level 3 - IMPLEMENTATION GUIDES (Project-Specific)
├─ rules/06-tdd/guide.md
│  └─ Defines: TDD workflow concepts (framework-agnostic)
│  └─ References: Project docs/testing/ for code examples
│
└─ docs/testing/test-execution.md
   └─ Defines: Docker commands, mocking patterns, execution strategy
   └─ Implements: Execution strategy from guide.md
```

## Quick Commands

### Fast Unit Tests (Pre-commit)
```bash
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb
```

### Integration Tests
```bash
docker-compose exec backend uv run python manage.py test --tag=medium --tag=integration --keepdb
```

### CI/CD Tests (Exclude Slow)
```bash
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb
```

### Full Test Suite
```bash
docker-compose exec backend uv run python manage.py test --keepdb
```

## Document Status

| File | Last Updated | Status | Notes |
|------|--------------|--------|-------|
| `rules/06-tdd/policy.md` | 2025-11-13 | ✅ Current | Framework-agnostic principles |
| `rules/06-tdd/guide.md` | 2025-11-13 | ✅ Current | Framework-agnostic concepts |
| `docs/testing/test-decorators.md` | 2025-11-13 | ✅ Current | Django-specific implementation |
| `docs/testing/test-execution.md` | 2025-11-13 | ✅ Current | Django-specific implementation |
| `docs/testing/test-benchmarks.md` | 2025-11-13 | ✅ Current | Actual performance baselines & mocking audit |

## Key Principles

### Single Source of Truth (SSOT)

| Concept | SSOT Document |
|---------|---------------|
| TDD workflow mandate | `rules/06-tdd/policy.md` |
| TDD workflow concepts | `rules/06-tdd/guide.md` |
| Django decorator syntax | `docs/testing/test-decorators.md` |
| Test execution commands | `docs/testing/test-execution.md` |
| Test performance baselines | `docs/testing/test-benchmarks.md` |

### When to Consult Which Document

**"What is required for TDD?"** → `rules/06-tdd/policy.md`
**"How do I approach TDD conceptually?"** → `rules/06-tdd/guide.md`
**"How do I tag my Django tests?"** → `docs/testing/test-decorators.md`
**"How do I run tests with Docker?"** → `docs/testing/test-execution.md`
**"How fast should my tests run?"** → `docs/testing/test-benchmarks.md`

## Maintenance Protocol

When updating testing documentation:

1. **Policy Changes** (TDD requirements):
   - Update `rules/06-tdd/policy.md` first
   - Verify changes don't require project-specific updates
   - If project changes needed, update `docs/testing/` files

2. **Decorator Changes** (tagging syntax):
   - Update `docs/testing/test-decorators.md` first
   - Update code examples in `docs/testing/test-execution.md`
   - Verify alignment with `rules/06-tdd/policy.md` principles

3. **Execution Changes** (commands, tools):
   - Update `docs/testing/test-execution.md` first
   - Verify alignment with `rules/06-tdd/guide.md` concepts

4. **Propagation Checklist**:
   - [ ] Update primary SSOT document
   - [ ] Update dependent documents
   - [ ] Update cross-references
   - [ ] Update CLAUDE.md if needed
   - [ ] Update this README.md status table

## External Resources

- **Django Documentation:**
  - [Django Testing Tools](https://docs.djangoproject.com/en/4.2/topics/testing/tools/)
  - [Django Test Tags](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#tagging-tests)
- **Python Testing:**
  - [unittest Documentation](https://docs.python.org/3/library/unittest.html)
  - [AsyncIO Testing](https://docs.python.org/3/library/asyncio-dev.html#testing)
- **Test Coverage:**
  - [Coverage.py](https://coverage.readthedocs.io/)
