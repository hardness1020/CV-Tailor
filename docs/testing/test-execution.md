# CV-Tailor Test Execution Guide (Django-Specific)

## Overview

This guide provides a step-by-step approach to running tests in the CV-Tailor backend, organized from fastest to slowest to ensure systematic validation of all functionality. All tests use Django's `@tag()` decorator for granular control over test execution.

**This is CV-Tailor's implementation** of the TDD execution strategy defined in `rules/06-tdd/guide.md`. For framework-agnostic TDD concepts, see `rules/06-tdd/`.

**📊 For actual test performance benchmarks and timing baselines, see [Test Benchmarks](./test-benchmarks.md).**

## Quick Start - Recommended Test Order

**For Development (Pre-commit)**:
```bash
# 1. Fast unit tests first (140 tests in ~0.3s)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# 2. Medium integration tests (565 tests in ~4.4s)
docker-compose exec backend uv run python manage.py test --tag=medium --tag=integration --keepdb
```

**For CI/CD Pipeline**:
```bash
# Exclude slow real API tests (649 tests in ~4.9s)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb
```

**Before Deployment**:
```bash
# Run all tests including slow end-to-end tests
docker-compose exec backend uv run python manage.py test --keepdb
```

**Manual Validation with Real APIs** (optional):
```bash
# Requires API keys and costs money
docker-compose exec -e FORCE_REAL_API_TESTS=true backend uv run python manage.py test --tag=real_api --keepdb -v 2
```

> **💡 Performance Note:** Timings based on 2025-11-13 benchmarks with proper mocking. See [Test Benchmarks](./test-benchmarks.md) for detailed performance analysis.

## Test Organization Using Django Tags

All tests are organized using Django's `@tag()` decorator for granular control over test execution.

### Tag Categories

```python
from django.test import tag

# Speed/Complexity tags
@tag('fast', 'unit')           # Fast unit tests (~2.3ms per test avg)
@tag('medium', 'integration')  # Integration tests (~7.7ms per test avg)
@tag('slow', 'e2e')            # End-to-end tests (>100ms per test)
@tag('slow', 'real_api')       # Real API tests (2-30s per test)

# Module tags
@tag('accounts')
@tag('artifacts')
@tag('generation')
@tag('llm_services')
@tag('export')

# Feature tags
@tag('enrichment')
@tag('cv_generation')
@tag('bullet_generation')
@tag('ranking')
@tag('api')
@tag('tasks')
@tag('auth')
```

## Critical: Proper Mocking for Unit Tests

**⚠️ UNIT TESTS MUST NEVER MAKE EXTERNAL API CALLS**

All tests tagged as `fast` and `unit` MUST use mocks for external dependencies. Making real API calls in unit tests causes:
- **Slow test execution** (30+ minutes instead of <1 minute)
- **Flaky tests** (network issues, rate limits, quota errors)
- **Cost** (real money spent on API calls)
- **Environmental pollution** (tests should not have side effects)

### Using common.test_mocks Utilities

The project provides reusable mock utilities in `backend/common/test_mocks.py`:

```python
from unittest.mock import patch
from common.test_mocks import (
    mock_llm_bullet_response,
    setup_mocked_llm_service,
    mock_validation_result
)

@tag('fast', 'unit', 'generation')
class MyServiceTests(AsyncTestCase):
    def setUp(self):
        super().setUp()

        # Mock TailoredContentService to avoid real API calls
        self.patcher = patch('generation.services.bullet_generation_service.TailoredContentService')
        mock_tailored_service_class = self.patcher.start()

        # Configure mocked LLM service with realistic responses
        self.mock_llm_service = setup_mocked_llm_service()
        mock_tailored_service_class.return_value = self.mock_llm_service

        # Create service - now uses mocked LLM
        self.service = BulletGenerationService()

    def tearDown(self):
        super().tearDown()
        self.patcher.stop()

    async def test_generate_bullets(self):
        # This test now runs in <1s instead of 30+ seconds!
        result = await self.service.generate_bullets(...)
        self.assertEqual(len(result.bullets), 3)
```

### Available Mock Utilities

#### 1. LLM Response Mocks

```python
# Mock complete bullet generation response
response = mock_llm_bullet_response(
    num_bullets=3,
    quality_score=0.85,
    cost_usd=0.0025,
    generation_time_ms=1200,
    model_used="gpt-5"
)

# Mock single bullet regeneration
response = mock_llm_single_bullet_response(
    bullet_text="Led development of...",
    bullet_type='achievement',
    quality_score=0.85
)
```

#### 2. Validation Result Mocks

```python
# Mock passing validation
validation = mock_validation_result(
    is_valid=True,
    overall_quality_score=0.85,
    bullet_scores=[0.85, 0.87, 0.83]
)

# Mock failing validation (for retry logic tests)
validation = mock_validation_result_invalid(
    reason="Quality below threshold",
    overall_quality_score=0.45
)
```

#### 3. Quick Setup Helper

```python
# Easiest way to mock LLM service
mock_llm = setup_mocked_llm_service()
with patch.object(service, 'tailored_content_service', mock_llm):
    result = await service.generate_bullets(...)
```

### Common Mocking Patterns

#### Pattern 1: Mock at Class Level (Recommended)

```python
@tag('fast', 'unit', 'generation')
class BulletGenerationServiceTests(AsyncTestCase):
    def setUp(self):
        super().setUp()

        # Start patcher in setUp
        self.patcher = patch('generation.services.bullet_generation_service.TailoredContentService')
        mock_class = self.patcher.start()
        mock_class.return_value = setup_mocked_llm_service()

        self.service = BulletGenerationService()

    def tearDown(self):
        super().tearDown()
        self.patcher.stop()
```

#### Pattern 2: Mock at Method Level

```python
@tag('fast', 'unit', 'generation')
class MyTests(AsyncTestCase):
    async def test_with_specific_mock(self):
        with patch('path.to.Service') as mock_service:
            mock_service.return_value.method = AsyncMock(
                return_value=mock_llm_bullet_response()
            )
            result = await function_under_test()
            self.assertEqual(result.status, 'success')
```

#### Pattern 3: Mock Multiple Dependencies

```python
@tag('fast', 'unit', 'generation')
class ComplexServiceTests(AsyncTestCase):
    def setUp(self):
        super().setUp()

        # Mock LLM service
        self.llm_patcher = patch('module.TailoredContentService')
        self.llm_patcher.start().return_value = setup_mocked_llm_service()

        # Mock validation service
        self.validation_patcher = patch('module.BulletValidationService')
        mock_validation = self.validation_patcher.start()
        mock_validation.return_value.validate_bullet_set = AsyncMock(
            return_value=mock_validation_result(is_valid=True)
        )

    def tearDown(self):
        super().tearDown()
        self.llm_patcher.stop()
        self.validation_patcher.stop()
```

### Common Pitfalls to Avoid

**❌ DON'T: Create service without mocking**
```python
def setUp(self):
    self.service = BulletGenerationService()  # Will use real API!
```

**✅ DO: Mock before creating service**
```python
def setUp(self):
    self.patcher = patch('module.TailoredContentService')
    self.patcher.start().return_value = setup_mocked_llm_service()
    self.service = BulletGenerationService()  # Now uses mock
```

**❌ DON'T: Tag tests as 'fast' if they make API calls**
```python
@tag('fast', 'unit')  # WRONG - this test makes real API calls!
class SlowTests(AsyncTestCase):
    async def test_real_api(self):
        service = RealService()  # Makes real API calls
        result = await service.call_api()
```

**✅ DO: Use correct tags or add mocking**
```python
@tag('medium', 'integration', 'real_api')  # Correct tagging
class RealAPITests(AsyncTestCase):
    # OR add mocking to make it truly 'fast'
```

**❌ DON'T: Forget to stop patchers**
```python
def setUp(self):
    self.patcher = patch('module.Service')
    self.patcher.start()
    # Missing tearDown() to stop patcher!
```

**✅ DO: Always stop patchers in tearDown**
```python
def tearDown(self):
    super().tearDown()
    self.patcher.stop()
```

### Performance Impact

Real example from our test suite:

| Test Category | Before Mocking | After Mocking | Speedup |
|---------------|----------------|---------------|---------|
| Single test | 30+ seconds | 0.5 seconds | **60x faster** |
| 17 tests | 8+ minutes | 8 seconds | **60x faster** |
| 158 tests | 30+ minutes | 63 seconds | **30x faster** |

**Key Takeaway**: Proper mocking makes tests run **30-60x faster** while maintaining accuracy!

## Step-by-Step Test Execution

### Step 1: Fast Unit Tests (Always Run First)

**Goal**: Verify core logic without external dependencies
**Expected Time**: ~0.4 seconds per test, typically 60-90 seconds total for 158 tests
**Tags**: `fast`, `unit`

```bash
# Run all fast unit tests
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb
```

**Expected Outcome**:
```
Found 158 tests
Creating test database for alias 'default'...
...............................................................................
...............................................................................
----------------------------------------------------------------------
Ran 158 tests in 63.551s

OK (errors=2)  # 2 errors are throttling config issues, unrelated to core functionality
```

**Performance Benchmarks** (verified October 2025):
- **Before mocking**: 30+ minutes (with real API calls and retries)
- **After mocking**: 63.551 seconds for 158 tests (~0.4s per test)
- **Speedup**: 30x faster with proper mocking!

**Key Stats**:
- Accounts models: 8 tests in 1.088s (~0.14s per test)
- Generation services: 17 tests in 8.176s (~0.48s per test)
- All fast unit tests: 158 tests in 63.551s (~0.40s per test)

**What Gets Tested**:
- Model methods (without database writes)
- Serializer validation logic
- Utility functions (calculate_skill_match_score, find_missing_skills)
- Business logic helpers
- Exception classes

**Example Tests**:
```python
from django.test import TestCase, tag

@tag('fast', 'unit', 'generation')
class BulletValidationServiceTests(TestCase):
    """Test cases for bullet validation logic."""

    def test_validate_bullet_structure(self):
        """Test bullet structure validation"""
        # Test implementation
```

**Common Failures**:
- Import errors (missing dependencies)
- Logic errors in business logic
- Validation errors in serializers

---

### Step 2: Medium Integration Tests (Run After Unit Tests Pass)

**Goal**: Verify service interactions with database and mocked APIs
**Expected Time**: ~0.20 seconds per test, typically 1-5 minutes total
**Tags**: `medium`, `integration`

```bash
# Run all integration tests
docker-compose exec backend uv run python manage.py test --tag=medium --tag=integration --keepdb
```

**Expected Outcome**:
```
Found 50+ tests
Creating test database for alias 'default'...
..................................................
----------------------------------------------------------------------
Ran 50 tests in 10.000s

OK
```

**Performance Benchmarks** (from verification tests):
- Auth integration: 5 tests in 1.006s (~0.20s per test)

**What Gets Tested**:
- Service methods with database interactions
- Model CRUD operations
- Serializer integration with models
- API endpoint logic (with mocked LLM calls)
- Celery task execution (eager mode)

**Example Tests**:
```python
@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactAPITests(APITestCase):
    """Test cases for Artifact API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)

    def test_create_artifact_success(self):
        """Test creating artifact via API"""
        # Test implementation with database
```

**Common Failures**:
- Database constraint violations
- Authentication/permission errors
- Service integration issues
- Mocked API call misconfigurations

---

### Step 3: Slow End-to-End Tests (Run Before Deployment)

**Goal**: Verify complete workflows with real/mocked external APIs
**Expected Time**: 2-30 seconds per test, typically 5-30 minutes total
**Tags**: `slow`, `e2e`

```bash
# Run end-to-end tests
docker-compose exec backend uv run python manage.py test --tag=slow --tag=e2e --keepdb -v 2
```

**Expected Outcome**:
```
Found 20+ tests
Creating test database for alias 'default'...
....................
----------------------------------------------------------------------
Ran 20 tests in 180.000s

OK
```

**What Gets Tested**:
- Complete user workflows (artifact upload → enrichment → CV generation)
- Celery task execution with real task queue
- Multi-step processes with error recovery
- Retry logic and circuit breaker patterns

**Example Tests**:
```python
@tag('slow', 'e2e', 'generation')
class CVGenerationWorkflowTests(TransactionTestCase):
    """End-to-end tests for CV generation workflow"""

    def test_full_cv_generation_workflow(self):
        # Test complete workflow from job description to generated CV
        # 1. Create job description
        # 2. Create artifacts
        # 3. Trigger CV generation
        # 4. Verify generated content
```

**Common Failures**:
- Timeout errors (increase timeout or optimize)
- Celery task failures
- External API errors (use mocking if not testing real APIs)
- Database transaction issues

---

### Step 4: Real API Tests (Optional, Manual Trigger Only)

**Goal**: Validate against actual LLM APIs (OpenAI, Anthropic)
**Expected Time**: 2-30+ seconds per test, costs real money
**Tags**: `real_api`, `slow`

```bash
# WARNING: This uses real API tokens and incurs costs
docker-compose exec -e FORCE_REAL_API_TESTS=true backend uv run python manage.py test llm_services.tests.integration.test_real_pipeline_integration --keepdb -v 2
```

**Expected Outcome**:
```
Found 4 tests
test_end_to_end_pipeline_minimal (llm_services.tests.integration.test_real_pipeline_integration.RealPipelineIntegrationTestCase) ... ok
test_artifact_enhancement_minimal (llm_services.tests.integration.test_real_pipeline_integration.RealPipelineIntegrationTestCase) ... ok
test_model_selection_and_fallback (llm_services.tests.integration.test_real_pipeline_integration.RealPipelineIntegrationTestCase) ... ok
test_cost_tracking_accuracy (llm_services.tests.integration.test_real_pipeline_integration.RealPipelineIntegrationTestCase) ... ok
----------------------------------------------------------------------
Ran 4 tests in 25.000s

OK

Pipeline test completed - Total cost: $0.150000, Total tokens: 15000
```

**Prerequisites**:
- Set `FORCE_REAL_API_TESTS=true` environment variable
- Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variables
- Budget awareness (tests cost ~$0.02-0.30 per test)

**What Gets Tested**:
- Real LLM API integration (no mocking)
- Token usage and cost tracking
- Model selection and fallback logic
- Circuit breaker behavior with real failures
- Performance tracking accuracy

**Safety Limits**:
- Max cost per test: $0.30
- Max cost total: $1.00
- Max tokens per test: 30,000

**Common Failures**:
- Missing API keys (raises RuntimeError)
- Rate limit exceeded (circuit breaker opens)
- Budget exceeded (test fails)
- Network timeout (retry logic activates)

---

## Test Execution Hierarchy

```
Recommended Execution Order (from fastest to slowest):

1. Fast Unit Tests (ALWAYS run first - baseline validation)
   │
   ├─ accounts.tests.test_models (8 tests, ~1.1s)
   ├─ artifacts.tests.test_models (3 test classes)
   ├─ generation.tests.test_models (7 test classes)
   ├─ export.tests.test_models (3 test classes)
   └─ llm_services.tests.unit.* (24 test modules)

   Expected: ~0.14-0.70s per test, 1-60s total
   If Failed: Fix logic errors before proceeding

2. Integration Tests (run after unit tests pass)
   │
   ├─ accounts.tests.test_auth_integration (5 tests, ~1.0s)
   ├─ artifacts.tests.test_api (4 test classes)
   ├─ generation.tests.test_api (5 test classes)
   ├─ export.tests.test_api (4 test classes)
   └─ llm_services.tests.integration.test_github_agent_integration (6 classes)

   Expected: ~0.20s per test, 1-5 min total
   If Failed: Fix service/database integration issues

3. End-to-End Tests (run before deployment only)
   │
   ├─ generation.tests.test_cv_generation_with_artifacts
   ├─ artifacts.tests.test_full_workflow
   └─ export.tests.test_export_workflow

   Expected: 2-30s per test, 5-30 min total
   If Failed: Fix workflow/orchestration issues

4. Real API Tests (optional, manual trigger only)
   │
   └─ llm_services.tests.integration.test_real_* (5 modules)

   Expected: 2-30s per test, variable cost ($0.02-1.00)
   If Failed: Check API keys, budget, circuit breaker state
```

---

## Running Tests by Scenario

### Development Workflow (Pre-commit)

```bash
# Quick validation before committing (~1-2 minutes)
docker-compose exec backend uv run python manage.py test --tag=fast --keepdb
```

**Expected**: All fast tests pass in <60 seconds

### CI/CD Pipeline

```bash
# Comprehensive validation excluding expensive tests (~5-10 minutes)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb
```

**Expected**: All unit and integration tests pass

### Pre-Deployment Validation

```bash
# Full test suite including e2e (~30-60 minutes)
docker-compose exec backend uv run python manage.py test --keepdb
```

**Expected**: All tests pass, including slow e2e tests

### Feature-Specific Testing

```bash
# Test specific feature during development
docker-compose exec backend uv run python manage.py test --tag=enrichment --keepdb
docker-compose exec backend uv run python manage.py test --tag=cv_generation --keepdb
docker-compose exec backend uv run python manage.py test --tag=bullet_generation --keepdb
```

**Expected**: All tests for that feature pass

### Module-Specific Testing

```bash
# Test specific Django app
docker-compose exec backend uv run python manage.py test accounts --keepdb
docker-compose exec backend uv run python manage.py test artifacts --keepdb
docker-compose exec backend uv run python manage.py test generation --keepdb
docker-compose exec backend uv run python manage.py test llm_services --keepdb
docker-compose exec backend uv run python manage.py test export --keepdb
```

**Expected**: All tests for that app pass

---

## Expected Outcomes Summary

| Test Category | Expected Time/Test | Total Time | Expected Outcome |
|--------------|-------------------|------------|------------------|
| **Fast Unit** | 0.14-0.70s | 1-60s | 100+ tests pass, no database writes |
| **Medium Integration** | ~0.20s | 1-5 min | 50+ tests pass, database operations work |
| **Slow E2E** | 2-30s | 5-30 min | 20+ tests pass, workflows complete |
| **Real API** | 2-30s | Variable | 4-10 tests pass, cost <$1.00 |

### Success Criteria

**All tests should display**:
```
----------------------------------------------------------------------
Ran X tests in Y.YYYs

OK
```

**If tests fail, you'll see**:
```
======================================================================
FAIL: test_name (module.TestClass)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: Expected X but got Y
----------------------------------------------------------------------
Ran X tests in Y.YYYs

FAILED (failures=1)
```

---

## CI/CD Integration Example

```yaml
# GitHub Actions / GitLab CI
name: Test Suite

stages:
  - fast_tests      # < 1 minute
  - integration     # 1-5 minutes
  - e2e            # 5-30 minutes (optional, pre-deployment only)

jobs:
  fast_tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run fast unit tests
        run: |
          docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb
        timeout-minutes: 2

  integration_tests:
    runs-on: ubuntu-latest
    needs: [fast_tests]
    steps:
      - name: Run integration tests
        run: |
          docker-compose exec backend uv run python manage.py test --tag=medium --tag=integration --keepdb
        timeout-minutes: 10

  e2e_tests:
    runs-on: ubuntu-latest
    needs: [integration_tests]
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    steps:
      - name: Run e2e tests
        run: |
          docker-compose exec backend uv run python manage.py test --tag=slow --tag=e2e --keepdb
        timeout-minutes: 45
```

---

## Test Coverage Goals

- **Overall**: 85%+ coverage
- **Services**: 90%+ coverage (critical business logic)
- **Models**: 80%+ coverage
- **API Views**: 85%+ coverage
- **Tasks**: 85%+ coverage

**Check coverage**:
```bash
docker-compose exec backend uv run coverage run --source='.' manage.py test --keepdb
docker-compose exec backend uv run coverage report
docker-compose exec backend uv run coverage html  # Generate HTML report
```

---

## Common Test Patterns

### 1. Service Tests with Mocked Dependencies

```python
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag

@tag('fast', 'unit', 'generation')
class CVGenerationServiceTests(TestCase):

    @patch('generation.services.cv_generation_service.TailoredContentService')
    def test_generate_cv_with_mocked_llm(self, mock_llm_service):
        # Arrange
        mock_llm_service.generate_tailored_content = AsyncMock(return_value={
            'cv_content': 'Sample CV',
            'processing_metadata': {'model_used': 'gpt-4'}
        })

        # Act
        result = await service.generate_cv_for_job(...)

        # Assert
        self.assertIsNotNone(result.cv_content)
```

### 2. Service Tests with Exception Handling

```python
@tag('medium', 'integration', 'artifacts')
class EnrichmentServiceTests(TestCase):

    def test_enrich_artifact_raises_on_no_evidence(self):
        """Service should raise InsufficientDataError when no evidence"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test',
            artifact_type='project'
        )

        service = ArtifactEnrichmentService()

        with self.assertRaises(InsufficientDataError):
            await service.preprocess_multi_source_artifact(artifact.id)
```

### 3. Async Test with Event Loop

```python
from common.test_base import AsyncTestCase

@tag('medium', 'integration', 'generation')
class AsyncGenerationTests(AsyncTestCase):

    async def test_async_cv_generation(self):
        """Test async CV generation with proper event loop"""
        service = CVGenerationService()
        result = await service.generate_cv_for_job(generation_id=1)

        self.assertIsNotNone(result.cv_content)
```

---

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Event Loop Errors** | `RuntimeError: Event loop is closed` | Use `AsyncTestCase` instead of `TestCase` |
| **Database Errors** | `Database "test_cv_tailor" already exists` | Use `--keepdb` flag to preserve test database |
| **Import Errors** | `ImportError: cannot import name 'X'` | Check for circular imports, missing models, or removed code |
| **Timeout Errors** | `TimeoutError` or test hangs | Increase timeout, add `@tag('slow')`, or optimize code |
| **Permission Errors** | `PermissionDenied` | Ensure test user has correct permissions, check `setUp()` |
| **API Key Errors** | `RuntimeError: OpenAI API key required` | Set environment variables or skip real API tests |

### Debug Commands

```bash
# Run single test with verbose output
docker-compose exec backend uv run python manage.py test \
  artifacts.tests.test_enrichment.EnrichmentTaskTests.test_enrich_artifact_success \
  --keepdb -v 2

# Run with Python debugger
docker-compose exec backend uv run python -m pdb manage.py test artifacts --keepdb

# Run with coverage report
docker-compose exec backend uv run coverage run --source='.' manage.py test --keepdb
docker-compose exec backend uv run coverage report

# Check test discovery (don't run tests)
docker-compose exec backend uv run python manage.py test --collect-only

# Run tests with specific verbosity
docker-compose exec backend uv run python manage.py test --keepdb -v 0  # Minimal output
docker-compose exec backend uv run python manage.py test --keepdb -v 1  # Normal output
docker-compose exec backend uv run python manage.py test --keepdb -v 2  # Verbose output
```

### Debugging Specific Test Failures

**If fast unit tests fail**:
1. Check logic errors in service methods
2. Verify mock configurations
3. Review test data fixtures
4. Check for missing imports

**If integration tests fail**:
1. Check database schema migrations
2. Verify service dependencies
3. Review API permissions
4. Check Celery task configurations

**If e2e tests fail**:
1. Check workflow orchestration
2. Verify external service mocking
3. Review timeout settings
4. Check transaction handling

**If real API tests fail**:
1. Verify API keys are set
2. Check budget limits
3. Review circuit breaker state
4. Check network connectivity

---

## Test Naming Conventions

### Test Class Names
- `{Feature}Tests` - Generic tests
- `{Feature}UnitTests` - Fast unit tests
- `{Feature}IntegrationTests` - Integration tests
- `{Feature}WorkflowTests` - End-to-end workflow tests
- `{Feature}APITests` - API endpoint tests

### Test Method Names
- `test_{what_is_being_tested}` - Standard format
- `test_{method_name}_{scenario}` - For specific scenarios
- `test_{method_name}_{expected_outcome}` - For outcome validation

**Examples**:
```python
# Good
def test_enrich_artifact_success(self):
def test_enrich_artifact_handles_service_failure(self):
def test_calculate_skill_match_score_empty_inputs(self):

# Bad
def test1(self):
def test_enrichment(self):
def testEnrich(self):  # Use snake_case, not camelCase
```

---

## Test Maintenance

### When to Update Tests

1. **After Service Changes**: Update integration tests to reflect new behavior
2. **After Model Changes**: Update model tests and integration tests
3. **After API Changes**: Update API tests and e2e tests
4. **After Task Changes**: Update task tests and integration tests
5. **After Adding New Features**: Add new test modules with appropriate tags

### Test Review Checklist

Before committing test code, verify:

- [ ] All tests have proper `@tag()` decorators
- [ ] Test names clearly describe what's being tested
- [ ] No hardcoded values (use factories or fixtures)
- [ ] Proper use of `setUp()` and `tearDown()`
- [ ] Async tests use `AsyncTestCase` base class
- [ ] Mocks are properly configured and verified
- [ ] Tests are independent (no shared state)
- [ ] Tests clean up after themselves
- [ ] Test coverage is adequate (>85%)
- [ ] All tests pass locally before pushing

---

## See Also

- **CV-Tailor Testing:**
  - [Test Benchmarks](./test-benchmarks.md) - Actual performance baselines ⭐ NEW
  - [Test Decorator Standards](./test-decorators.md) - Django @tag syntax and categorization
  - [TDD Workflow](../../rules/06-tdd/guide.md) - Conceptual TDD guidance
  - [TDD Policy](../../rules/06-tdd/policy.md) - Framework-agnostic TDD requirements
- **Django Documentation:**
  - [Django Testing Docs](https://docs.djangoproject.com/en/4.2/topics/testing/)
  - [Django Test Tags](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#tagging-tests)
  - [AsyncIO Testing](https://docs.python.org/3/library/asyncio-dev.html#testing)
  - [Coverage.py](https://coverage.readthedocs.io/)
