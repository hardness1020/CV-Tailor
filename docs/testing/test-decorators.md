# CV-Tailor Test Decorator Standards (Django-Specific)

**Last Updated:** 2025-11-13

## Overview

This document defines the standardized approach for test decorators in the CV-Tailor backend. All tests use Django's native `@tag()` decorator for categorization and filtering.

**This is CV-Tailor's implementation** of the TDD principles defined in `rules/06-tdd/policy.md`. For framework-agnostic TDD concepts, see `rules/06-tdd/`.

## Standards

### Use Django `@tag` for Test Categorization

The codebase has been consolidated to use Django's native `@tag()` decorator exclusively. Pytest markers for categorization (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.tag`) have been removed to eliminate confusion and maintain consistency.

### Correct Usage

**✅ Django TestCase with @tag**
```python
from django.test import TestCase, tag

@tag('fast', 'unit', 'llm_services')
class MyServiceTests(TestCase):
    """Test MyService methods"""

    def test_method_returns_correct_value(self):
        result = MyService().method()
        self.assertEqual(result, expected_value)
```

**✅ Async Django TestCase with @tag**
```python
from common.test_base import AsyncTestCase
from django.test import tag

@tag('medium', 'integration', 'generation')
class MyAsyncTests(AsyncTestCase):
    """Test async service operations"""

    async def test_async_method(self):
        result = await MyService().async_method()
        self.assertEqual(result.status, 'success')
```

### Deprecated Patterns

**❌ Pytest markers for categorization (removed)**
```python
# DO NOT USE - These have been removed from the codebase
@pytest.mark.unit  # ❌ Deprecated
@pytest.mark.integration  # ❌ Deprecated
@pytest.mark.slow  # ❌ Deprecated
@pytest.mark.tag('unit', 'fast')  # ❌ Custom marker deprecated
@pytest.mark.skip  # ❌ Use @unittest.skip instead
```

### Allowed Exceptions

Some decorators are still required for specific functionality:

**✅ Required for async tests**
```python
@pytest.mark.asyncio
async def test_async_operation(self):
    pass
```

**✅ Required for pytest fixtures**
```python
@pytest.fixture
def my_fixture():
    return SomeObject()
```

**✅ Skipping tests**
```python
import unittest

@unittest.skip("Reason for skipping")
def test_something(self):
    pass
```

**✅ Custom real API decorators**
```python
from llm_services.tests.integration.test_real_api_config import (
    skip_unless_forced,
    require_real_api_key,
    with_budget_control
)

@skip_unless_forced
@require_real_api_key('openai')
@with_budget_control()
@tag('slow', 'real_api', 'llm_services')
def test_real_api_call(self):
    pass
```

## Tag Categories

### Speed/Complexity Tags

| Tag | Description | Expected Time | Use Case |
|-----|-------------|---------------|----------|
| `'fast'` | Fast unit tests | <1s per test | Mocked dependencies, no I/O |
| `'medium'` | Integration tests | 0.2-2s per test | Database operations, mocked APIs |
| `'slow'` | Slow end-to-end tests | >2s per test | Complete workflows, real task queues |
| `'real_api'` | Real API tests | 2-30s per test | Actual LLM API calls (costs money) |

### Test Type Tags

| Tag | Description | Use Case |
|-----|-------------|----------|
| `'unit'` | Unit tests | Test individual functions/methods in isolation |
| `'integration'` | Integration tests | Test service interactions with database/APIs |
| `'e2e'` | End-to-end tests | Test complete user workflows |

### Module Tags

| Tag | Description |
|-----|-------------|
| `'accounts'` | Authentication and user management tests |
| `'artifacts'` | Work artifact management tests |
| `'generation'` | CV/cover letter generation tests |
| `'llm_services'` | LLM integration and services tests |
| `'export'` | Document export tests |

### Feature Tags

| Tag | Description |
|-----|-------------|
| `'enrichment'` | Artifact enrichment tests |
| `'cv_generation'` | CV generation workflow tests |
| `'bullet_generation'` | Bullet point generation tests |
| `'ranking'` | Artifact ranking tests |
| `'api'` | API endpoint tests |
| `'tasks'` | Celery task tests |
| `'auth'` | Authentication tests |

## Tag Combinations

### Recommended Patterns

**Fast unit test:**
```python
@tag('fast', 'unit', 'generation')
class QuickTests(TestCase):
    pass
```

**Integration test with database:**
```python
@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactAPITests(APITestCase):
    pass
```

**Slow end-to-end workflow:**
```python
@tag('slow', 'e2e', 'generation', 'cv_generation')
class CVGenerationWorkflowTests(TransactionTestCase):
    pass
```

**Real API test (protected):**
```python
@skip_unless_forced
@require_real_api_key('openai')
@tag('slow', 'real_api', 'llm_services')
class RealOpenAITests(TestCase):
    pass
```

## Migration from Pytest Markers

If you encounter old pytest markers during code review, convert them to Django @tag:

**Before (deprecated):**
```python
@pytest.mark.unit
@pytest.mark.integration
class OldTests(TestCase):
    pass
```

**After (correct):**
```python
@tag('medium', 'integration', 'module_name')
class NewTests(TestCase):
    pass
```

## Rationale

### Why Django @tag?

1. **Native Django Support:** `@tag` is the official Django approach for test categorization
2. **Better Integration:** Works seamlessly with Django's test runner
3. **Consistent Filtering:** Single tagging system eliminates confusion
4. **Documentation:** Well-documented in Django's official docs
5. **Simplicity:** One decorator to learn instead of two parallel systems

### Why Remove Pytest Markers?

The codebase previously used both Django `@tag` and pytest `@pytest.mark.*` decorators simultaneously, leading to:
- **Confusion:** Developers unsure which system to use
- **Inconsistency:** Some tests tagged one way, others another way
- **Maintenance Burden:** Two systems to maintain and document
- **Filtering Issues:** Different commands for Django tags (`--tag=unit`) vs pytest markers (`-m unit`)

## Test Execution with Tags

### Run by Speed

```bash
# Fast tests only
docker-compose exec backend uv run python manage.py test --tag=fast --keepdb

# Exclude slow tests
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --keepdb
```

### Run by Type

```bash
# Unit tests only
docker-compose exec backend uv run python manage.py test --tag=unit --keepdb

# Integration tests only
docker-compose exec backend uv run python manage.py test --tag=integration --keepdb
```

### Run by Module

```bash
# All llm_services tests
docker-compose exec backend uv run python manage.py test --tag=llm_services --keepdb

# All generation tests
docker-compose exec backend uv run python manage.py test --tag=generation --keepdb
```

### Combined Filters

```bash
# Fast unit tests in generation module
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --tag=generation --keepdb

# All non-slow, non-real_api tests (CI/CD)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb
```

## See Also

- **CV-Tailor Testing:**
  - [Test Execution Guide](./test-execution.md) - Commands and mocking patterns
  - [TDD Principles](../../rules/06-tdd/policy.md) - Framework-agnostic TDD policy
  - [TDD Workflow](../../rules/06-tdd/guide.md) - Conceptual TDD guidance
- **Django Documentation:**
  - [Django Test Tags Documentation](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#tagging-tests)
