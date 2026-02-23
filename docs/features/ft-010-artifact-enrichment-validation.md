# Feature — 010 Artifact Enrichment Validation & Quality Gates

**File:** docs/features/ft-010-artifact-enrichment-validation.md
**Owner:** Backend Team
**TECH-SPECs:** `spec-artifact-upload-enrichment-flow.md` (v1.1.0)
**ADRs:** `adr-020-artifact-enrichment-quality-issues.md`, `adr-021-hybrid-validation-approach.md`
**Priority:** P0 (Critical - fixes production quality issues)
**Status:** Approved
**Target Date:** 2025-10-10

## Existing Implementation Analysis

**Discovery Findings from Stage B:**

### Similar Features
- **`generation/services/bullet_validation_service.py`** (495 lines)
  - Implements multi-criteria validation with `ValidationResult` dataclass
  - Uses blocking/warning thresholds for quality gates
  - Returns detailed `issues` and `suggestions` lists
  - **Pattern to reuse**: Validation result dataclass with `is_valid`, `issues`, `warnings`

- **`artifacts/tasks.py:enrich_artifact()`** (current enrichment flow)
  - Creates `ArtifactProcessingJob` with status tracking
  - Calls `ArtifactEnrichmentService.preprocess_multi_source_artifact()`
  - Updates artifact with enriched fields
  - **Gap**: No quality validation before marking "completed"

### Reusable Components

1. **`llm_services/services/reliability/circuit_breaker.py`** (CircuitBreakerManager)
   - Fault tolerance for external LLM API calls
   - Already used in `ArtifactEnrichmentService`
   - **Not needed for this feature** (validation is local)

2. **`llm_services/services/base/task_executor.py`** (TaskExecutor)
   - Retry logic with exponential backoff
   - Error handling with fallback patterns
   - **Already in use** - no changes needed

3. **`llm_services/services/base/base_service.py`** (BaseLLMService)
   - Base class for all LLM services
   - **Not applicable** - EnrichmentQualityValidator is pure validation (no LLM calls)

### Architecture Patterns to Follow

**Service Layer Structure** (from `llm_services/` and `generation/services/`):
```
base/               # Foundation classes
core/               # Business logic services
infrastructure/     # Supporting components
reliability/        # Fault tolerance ← NEW VALIDATOR GOES HERE
```

**Validation Service Pattern** (from `BulletValidationService`):
```python
@dataclass
class ValidationResult:
    is_valid: bool
    score: float
    issues: List[str]
    warnings: List[str]

class MyValidationService:
    def validate(self, input) -> ValidationResult:
        # Multi-criteria validation
        # Return detailed issues/warnings
```

### Code to Refactor

**None identified** - This is new validation logic, not refactoring existing code.

**Files to modify**:
- `backend/artifacts/views.py` - Add file verification and transaction coordination
- `backend/artifacts/tasks.py` - Add quality validation before saving
- `backend/llm_services/services/reliability/` - Add `quality_validator.py` (new file)
- `frontend/src/components/ArtifactEnrichmentStatus.tsx` - Display warnings

### Dependencies

**Existing Services (no changes needed)**:
- `ArtifactEnrichmentService` - Already returns `EnrichedArtifactResult`
- `Evidence` model - Already has validation fields
- `ArtifactProcessingJob` - Already has `metadata_extracted` for warnings

**New Dependencies**: None (pure validation logic)

### Test Coverage Analysis

**Existing Test Structure** (48 test files total):
- `backend/artifacts/tests/test_enrichment.py` - 4 validation test functions
- `backend/generation/tests/test_services.py` - 12 validation test functions
- **Pattern**: Mock `ArtifactEnrichmentService`, assert on result fields

**Test Coverage Needed**:
- Unit: Quality validator thresholds (confidence, description length, extraction rate)
- Integration: Full enrichment flow with quality gates
- End-to-end: Frontend displays validation errors

---

## Architecture Conformance

### Layer Assignment

**New Component**:
- `backend/llm_services/services/reliability/quality_validator.py` - **reliability layer**
  - Pure validation logic (no LLM calls)
  - Ensures system reliability through quality gates
  - Follows reliability layer pattern (circuit_breaker.py, performance_tracker.py)

**Modified Components**:
- `backend/artifacts/views.py` - **API/interface layer**
  - Add file verification (Layer 3 validation)
  - Add `transaction.on_commit()` for race condition fix

- `backend/artifacts/tasks.py` - **task/orchestration layer**
  - Call `EnrichmentQualityValidator.validate()`
  - Set job status based on validation result

- `frontend/src/components/ArtifactEnrichmentStatus.tsx` - **presentation layer**
  - Display validation errors and warnings
  - Show quality metrics in failure state

### Pattern Compliance

✅ **Follows llm_services structure**:
- New validator in `reliability/` layer (same as circuit_breaker)
- Uses dataclass for validation result (same as `BulletValidationService`)

✅ **Follows validation service pattern**:
- Returns structured `ValidationResult` with `is_valid`, `errors`, `warnings`
- Multi-criteria validation with clear error messages

✅ **Follows error handling pattern**:
- Detailed error messages in `ArtifactProcessingJob.error_message`
- Warnings stored in `metadata_extracted['quality_warnings']`

✅ **Follows transaction safety pattern**:
- Uses Django's `transaction.on_commit()` to prevent race conditions

### Dependencies

**Internal**:
- `llm_services.services.core.artifact_enrichment_service.EnrichedArtifactResult`
- `artifacts.models.ArtifactProcessingJob`
- `artifacts.models.Evidence`

**External**: None (no new third-party packages)

---

## Acceptance Criteria

### Phase 1: Critical Fixes (Must Have)

#### 1. Quality Validation Layer (Layer 4)
- [ ] `EnrichmentQualityValidator` class created in `llm_services/services/reliability/`
- [ ] Validation checks implemented:
  - [ ] Fail if `processing_confidence < 0.5`
  - [ ] Fail if `unified_description` length < 100 characters
  - [ ] Fail if all source extractions failed (success_rate == 0)
  - [ ] Warn if extraction success rate < 50%
  - [ ] Warn if `enriched_technologies` is empty
  - [ ] Warn if `enriched_achievements` is empty
- [ ] Returns structured `ValidationResult` with:
  - [ ] `passed: bool`
  - [ ] `errors: List[str]` (blocking issues)
  - [ ] `warnings: List[str]` (quality concerns)

#### 2. File Accessibility Validation (Layer 3)
- [ ] File verification added to `views.py:upload_artifact_files()`
- [ ] Check `os.path.exists()` for each uploaded file
- [ ] Return 400 error with clear message if file not accessible
- [ ] Log file path details for debugging (MEDIA_ROOT, current working directory)

#### 3. Transaction Coordination (Race Condition Fix)
- [ ] `transaction.on_commit()` used in `upload_artifact_files()`
- [ ] Enrichment triggered AFTER Evidence records committed
- [ ] No more "0 evidence found" errors due to timing

#### 4. Quality Gate Integration
- [ ] `enrich_artifact()` task calls `quality_validator.validate()`
- [ ] If validation fails:
  - [ ] Set `processing_job.status = 'failed'`
  - [ ] Set `processing_job.error_message = '; '.join(errors)`
  - [ ] Store warnings in `metadata_extracted['quality_warnings']`
- [ ] If validation passes with warnings:
  - [ ] Set `processing_job.status = 'completed'`
  - [ ] Store warnings in `metadata_extracted['quality_warnings']`

#### 5. Frontend Error Display
- [ ] `ArtifactEnrichmentStatus.tsx` displays detailed error messages
- [ ] Failed enrichment shows errors from `error_message`
- [ ] Completed enrichment with warnings shows yellow alert box
- [ ] Retry button available for failed enrichments

### Phase 2: Progressive Enhancement (Should Have)

#### 6. Async GitHub Validation (Layer 2)
- [ ] `POST /api/v1/artifacts/validate-evidence/` endpoint created
- [ ] Lightweight HEAD request checks GitHub repo exists
- [ ] Returns `{valid, accessible, warning_message}` JSON
- [ ] Frontend calls validation on blur (debounced)
- [ ] Warning icon (⚠️) shown if inaccessible, but allows submission

#### 7. Frontend Async Validation Integration
- [ ] Debounced validation when user adds GitHub URL
- [ ] Warning icon displayed if validation fails
- [ ] Warning message: "Repository not found. You can still submit."
- [ ] Allows submission even with warnings

### Success Metrics (From ADR)

**Immediate** (after Phase 1):
- [ ] Zero false "completed" statuses (low quality marked as failed)
- [ ] Clear error messages when file access fails
- [ ] Enrichment failures properly reported with retry option

**Long-term** (after Phase 2):
- [ ] Early error detection: ≥80% of issues caught before enrichment
- [ ] Enrichment failure rate: <10% (down from ~40%)
- [ ] User satisfaction with error messages: ≥85% (survey)
- [ ] False positive rate: <5% (manual validation)

---

## Design Changes

### Backend: New Files

#### `backend/llm_services/services/reliability/quality_validator.py` (NEW)

```python
"""
Enrichment Quality Validator

Validates enrichment quality before marking as "completed".
Implements quality gates from adr-020-artifact-enrichment-quality-issues.
"""

from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentValidationResult:
    """
    Validation result for enriched artifact.

    Attributes:
        passed: Overall validation passed (no blocking errors)
        errors: Blocking issues that cause validation to fail
        warnings: Quality concerns that don't block completion
        quality_score: Overall quality score (0-1, same as processing_confidence)
    """
    passed: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float


class EnrichmentQualityValidator:
    """
    Validates enrichment quality using multi-criteria thresholds.

    Quality Thresholds:
    - FAIL if processing_confidence < 0.5
    - FAIL if unified_description < 100 chars (likely fallback)
    - FAIL if all source extractions failed (0% success rate)
    - WARN if extraction success rate < 50%
    - WARN if no technologies extracted
    - WARN if no achievements extracted

    Usage:
        validator = EnrichmentQualityValidator()
        result = validator.validate(enriched_result)
        if not result.passed:
            print(f"Validation failed: {result.errors}")
    """

    # Thresholds
    MIN_CONFIDENCE = 0.5
    MIN_DESCRIPTION_LENGTH = 100
    MIN_EXTRACTION_SUCCESS_RATE = 0.5

    def validate(self, enriched_result) -> EnrichmentValidationResult:
        """
        Validate enrichment quality.

        Args:
            enriched_result: EnrichedArtifactResult from ArtifactEnrichmentService

        Returns:
            EnrichmentValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check extraction success rate
        if enriched_result.sources_processed > 0:
            success_rate = enriched_result.sources_successful / enriched_result.sources_processed

            if success_rate == 0:
                errors.append("All source extractions failed (0% success rate)")
            elif success_rate < self.MIN_EXTRACTION_SUCCESS_RATE:
                warnings.append(f"Low extraction success: {success_rate:.0%} ({enriched_result.sources_successful}/{enriched_result.sources_processed} sources)")

        # Check processing confidence
        if enriched_result.processing_confidence < self.MIN_CONFIDENCE:
            errors.append(f"Low processing confidence: {enriched_result.processing_confidence:.2f} (minimum: {self.MIN_CONFIDENCE})")

        # Check description quality
        if len(enriched_result.unified_description) < self.MIN_DESCRIPTION_LENGTH:
            errors.append(f"Description too short ({len(enriched_result.unified_description)} chars) - likely fallback content (minimum: {self.MIN_DESCRIPTION_LENGTH} chars)")

        # Check extracted data (warnings only)
        if len(enriched_result.enriched_technologies) == 0:
            warnings.append("No technologies extracted from evidence sources")

        if len(enriched_result.enriched_achievements) == 0:
            warnings.append("No achievements extracted from evidence sources")

        passed = len(errors) == 0

        if not passed:
            logger.warning(f"Enrichment quality validation failed for artifact {enriched_result.artifact_id}: {errors}")
        elif warnings:
            logger.info(f"Enrichment completed with warnings for artifact {enriched_result.artifact_id}: {warnings}")

        return EnrichmentValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            quality_score=enriched_result.processing_confidence
        )
```

### Backend: Modified Files

#### `backend/artifacts/views.py` - File Verification & Transaction Coordination

```python
# Around line 220-250 (upload_artifact_files function)

import os
from django.conf import settings
from django.db import transaction

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic  # Ensure atomic transaction
def upload_artifact_files(request, artifact_id):
    """Upload files for an artifact"""
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)
    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=404)

    files = request.FILES.getlist('files')
    if not files:
        return Response({'error': 'No files provided'}, status=400)

    uploaded_files = []

    for file in files:
        # Create UploadedFile and Evidence
        uploaded_file = UploadedFile.objects.create(
            file=file,
            filename=file.name,
            file_size=file.size,
            mime_type=file.content_type
        )

        Evidence.objects.create(
            artifact=artifact,
            url=f"file://{uploaded_file.file.name}",
            evidence_type='document',
            file_path=uploaded_file.file.name,
            file_size=file.size,
            mime_type=file.content_type
        )

        # NEW: Verify file accessibility
        full_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.file.name)
        if not os.path.exists(full_path):
            logger.error(f"File not accessible after upload: {full_path}")
            logger.error(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
            logger.error(f"Current working directory: {os.getcwd()}")
            return Response({
                'error': f'File not accessible: {file.name}',
                'details': 'Uploaded file could not be verified on server'
            }, status=400)

        uploaded_files.append({
            'file_id': str(uploaded_file.id),
            'filename': uploaded_file.filename,
            'size': uploaded_file.file_size,
            'mime_type': uploaded_file.mime_type
        })

    # NEW: Trigger enrichment AFTER transaction commits (prevents race condition)
    transaction.on_commit(
        lambda: enrich_artifact.delay(artifact_id=artifact.id, user_id=request.user.id)
    )

    return Response({'uploaded_files': uploaded_files}, status=200)
```

#### `backend/artifacts/tasks.py` - Quality Gate Integration

```python
# Around line 165-195 (enrich_artifact task)

from llm_services.services.reliability.quality_validator import EnrichmentQualityValidator

@shared_task(bind=True, max_retries=3)
def enrich_artifact(self, artifact_id, user_id, processing_job_id=None):
    """Enrich artifact with multi-source preprocessing"""
    try:
        artifact = Artifact.objects.get(id=artifact_id, user_id=user_id)

        # Create or get processing job
        if processing_job_id:
            processing_job = ArtifactProcessingJob.objects.get(id=processing_job_id)
        else:
            processing_job = ArtifactProcessingJob.objects.create(
                artifact=artifact,
                status='processing',
                progress_percentage=10
            )

        # Run enrichment
        service = ArtifactEnrichmentService()
        result = await service.preprocess_multi_source_artifact(
            artifact_title=artifact.title,
            artifact_description=artifact.description,
            artifact_id=artifact.id
        )

        # NEW: Quality validation
        validator = EnrichmentQualityValidator()
        validation_result = validator.validate(result)

        if not validation_result.passed:
            # Validation failed - mark as failed with detailed errors
            processing_job.status = 'failed'
            processing_job.error_message = '; '.join(validation_result.errors)
            processing_job.metadata_extracted = {
                'enrichment_success': False,
                'quality_warnings': validation_result.warnings,
                'quality_score': validation_result.quality_score,
                'sources_processed': result.sources_processed,
                'sources_successful': result.sources_successful,
                'validation_failed': True
            }
            processing_job.save()

            logger.error(f"Enrichment quality validation failed for artifact {artifact_id}: {validation_result.errors}")
            return

        # Validation passed - update artifact with enriched data
        artifact.unified_description = result.unified_description
        artifact.enriched_technologies = result.enriched_technologies
        artifact.enriched_achievements = result.enriched_achievements
        artifact.processing_confidence = result.processing_confidence
        artifact.unified_embedding = result.unified_embedding
        artifact.save()

        # Update processing job
        processing_job.status = 'completed'
        processing_job.progress_percentage = 100
        processing_job.metadata_extracted = {
            'enrichment_success': True,
            'quality_warnings': validation_result.warnings,  # Include warnings even on success
            'sources_processed': result.sources_processed,
            'sources_successful': result.sources_successful,
            'processing_confidence': result.processing_confidence,
            'total_cost_usd': result.total_cost_usd,
            'processing_time_ms': result.processing_time_ms,
            'technologies_count': len(result.enriched_technologies),
            'achievements_count': len(result.enriched_achievements)
        }
        processing_job.completed_at = timezone.now()
        processing_job.save()

        logger.info(f"Enrichment completed for artifact {artifact_id} with {len(validation_result.warnings)} warnings")

    except Exception as e:
        logger.error(f"Enrichment task failed for artifact {artifact_id}: {str(e)}")
        if processing_job:
            processing_job.status = 'failed'
            processing_job.error_message = f"Unexpected error: {str(e)}"
            processing_job.save()
        raise
```

### Frontend: Modified Files

#### `frontend/src/components/ArtifactEnrichmentStatus.tsx` - Enhanced Error Display

```typescript
// Around line 126-141 (Failed state rendering)

if (status.status === 'failed') {
  console.log('[ArtifactEnrichmentStatus] Rendering failed state')
  return (
    <div className={cn('p-4 bg-red-50 border border-red-200 rounded-lg', className)}>
      <div className="flex items-start gap-3">
        <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-red-900 mb-1">Enrichment Failed</h4>
          {status.errorMessage && (
            <div className="space-y-2">
              <p className="text-sm text-red-700 font-medium">{status.errorMessage}</p>

              {/* NEW: Show quality warnings if available */}
              {status.enrichment?.qualityWarnings && status.enrichment.qualityWarnings.length > 0 && (
                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-xs font-medium text-yellow-800 mb-1">Quality Warnings:</p>
                  <ul className="list-disc list-inside text-xs text-yellow-700">
                    {status.enrichment.qualityWarnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* NEW: Retry button */}
              <button
                onClick={() => window.location.reload()}
                className="mt-2 text-sm text-red-700 underline hover:text-red-900"
              >
                Retry Enrichment
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Around line 143-206 (Completed state - add warnings)

if (status.status === 'completed' && status.enrichment) {
  // ... existing code ...

  return (
    <div className={cn('p-4 bg-green-50 border border-green-200 rounded-lg', className)}>
      {/* Existing success content */}

      {/* NEW: Show warnings if present */}
      {status.enrichment.qualityWarnings && status.enrichment.qualityWarnings.length > 0 && (
        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs font-medium text-yellow-800 mb-1">Quality Warnings:</p>
              <ul className="list-disc list-inside text-xs text-yellow-700">
                {status.enrichment.qualityWarnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Existing metrics grid */}
    </div>
  )
}
```

### API Schema Changes

#### EnrichmentStatus Response (Extended)

```typescript
interface EnrichmentStatus {
  artifactId: number
  status: 'not_started' | 'pending' | 'processing' | 'completed' | 'failed'
  progressPercentage: number
  errorMessage?: string
  hasEnrichment: boolean
  enrichment?: {
    sourcesProcessed: number
    sourcesSuccessful: number
    processingConfidence: number
    totalCostUsd: number
    processingTimeMs: number
    technologiesCount: number
    achievementsCount: number
    // NEW: Quality warnings
    qualityWarnings?: string[]  // Added in Phase 1
  }
}
```

---

## Test & Eval Plan

### Unit Tests

#### `backend/llm_services/tests/unit/services/reliability/test_quality_validator.py` (NEW)

**Test Cases**:
1. ✅ `test_validation_passes_with_good_quality`
   - Given: EnrichedArtifactResult with confidence=0.8, description=200 chars, 3/3 sources successful
   - Expect: `passed=True`, `errors=[]`, `warnings=[]`

2. ✅ `test_validation_fails_low_confidence`
   - Given: confidence=0.3 (< 0.5 threshold)
   - Expect: `passed=False`, error="Low processing confidence: 0.30"

3. ✅ `test_validation_fails_short_description`
   - Given: description="Test." (5 chars, < 100 threshold)
   - Expect: `passed=False`, error="Description too short...likely fallback"

4. ✅ `test_validation_fails_all_extractions_failed`
   - Given: sources_processed=3, sources_successful=0 (0% success rate)
   - Expect: `passed=False`, error="All source extractions failed"

5. ✅ `test_validation_warns_low_extraction_rate`
   - Given: 1/3 sources successful (33%)
   - Expect: `passed=True`, warning="Low extraction success: 33% (1/3 sources)"

6. ✅ `test_validation_warns_no_technologies`
   - Given: enriched_technologies=[]
   - Expect: `passed=True`, warning="No technologies extracted"

7. ✅ `test_validation_warns_no_achievements`
   - Given: enriched_achievements=[]
   - Expect: `passed=True`, warning="No achievements extracted"

8. ✅ `test_validation_multiple_errors`
   - Given: Low confidence + short description + 0% extraction
   - Expect: `passed=False`, errors=[...3 errors]

9. ✅ `test_validation_passes_with_warnings`
   - Given: Good quality but no technologies/achievements
   - Expect: `passed=True`, warnings=[...2 warnings]

#### `backend/artifacts/tests/test_enrichment.py` - Add Quality Gate Tests

**New Test Cases**:
1. ✅ `test_enrich_artifact_fails_quality_validation`
   - Mock enrichment result with low confidence (0.3)
   - Assert: processing_job.status == 'failed'
   - Assert: "Low processing confidence" in error_message

2. ✅ `test_enrich_artifact_success_with_warnings`
   - Mock enrichment result with warnings (no technologies)
   - Assert: processing_job.status == 'completed'
   - Assert: 'quality_warnings' in metadata_extracted

3. ✅ `test_file_verification_fails`
   - Mock uploaded file that doesn't exist on disk
   - Assert: Response status 400
   - Assert: "File not accessible" in response

4. ✅ `test_transaction_coordination`
   - Verify transaction.on_commit() called
   - Verify enrichment triggered after Evidence committed

### Integration Tests

#### `backend/artifacts/tests/test_enrichment_integration.py` (NEW)

**End-to-End Test Cases**:
1. ✅ `test_full_enrichment_flow_with_quality_gates`
   - Upload artifact with files
   - Trigger enrichment
   - Mock enrichment service to return low quality
   - Assert: enrichment-status shows 'failed' with detailed errors

2. ✅ `test_race_condition_fix`
   - Upload files
   - Immediately check Evidence.objects.filter()
   - Assert: Evidence records exist before enrichment starts

3. ✅ `test_file_accessibility_validation`
   - Upload file with mocked file system error
   - Assert: Upload fails with clear error message

### Frontend Tests (Playwright / React Testing Library)

#### `frontend/src/components/__tests__/ArtifactEnrichmentStatus.test.tsx`

**Test Cases**:
1. ✅ `test_displays_quality_validation_errors`
   - Mock failed enrichment with quality errors
   - Assert: Error message displayed
   - Assert: Retry button present

2. ✅ `test_displays_quality_warnings_on_success`
   - Mock completed enrichment with warnings
   - Assert: Yellow warning box displayed
   - Assert: Warnings listed

3. ✅ `test_retry_button_functionality`
   - Mock failed enrichment
   - Click retry button
   - Assert: Page reloads

### Evaluation Metrics

**Validation Effectiveness** (Track in Prometheus):
```python
# Early error detection rate
early_detection_rate = validation_errors_count / total_errors_count
# Target: ≥80%

# False positive rate (manual validation)
false_positive_rate = invalid_warnings / total_warnings
# Target: <5%

# Quality gate accuracy
quality_gate_accuracy = legitimate_failures / total_quality_failures
# Target: ≥95%
```

**User Satisfaction Survey** (after Phase 1):
```
Q1: Did error messages help you fix the issue? (1-10 scale)
Target: ≥85% respond 7+

Q2: Were warnings useful? (Yes/No)
Target: ≥80% respond Yes
```

---

## Telemetry & Metrics

### Prometheus Metrics (NEW)

```python
# backend/llm_services/services/reliability/quality_validator.py

from prometheus_client import Counter, Histogram

# Validation outcome tracking
enrichment_validation_results = Counter(
    'artifact_enrichment_validation_total',
    'Enrichment validation results',
    ['result', 'failure_reason']  # result: 'passed'/'failed', failure_reason: error type
)

# Quality score distribution
enrichment_quality_score = Histogram(
    'artifact_enrichment_quality_score',
    'Enrichment quality score distribution',
    buckets=[0.3, 0.5, 0.7, 0.9, 1.0]
)

# Validation layer tracking
validation_layer_errors = Counter(
    'artifact_validation_layer_errors_total',
    'Validation errors by layer',
    ['layer', 'error_type']  # layer: 1-4, error_type: category
)

# Usage in validator:
def validate(self, enriched_result):
    # ... validation logic ...

    enrichment_quality_score.observe(enriched_result.processing_confidence)

    if not passed:
        enrichment_validation_results.labels(result='failed', failure_reason='low_confidence').inc()
    else:
        enrichment_validation_results.labels(result='passed', failure_reason='none').inc()

    return result
```

### Dashboards

**Dashboard 1: Validation Effectiveness**
- Early error detection rate (Layer 1-3 vs Layer 4)
- Quality gate pass/fail distribution (pie chart)
- False positive trend (line chart over time)
- Validation errors by layer (stacked bar chart)

**Dashboard 2: Enrichment Outcomes**
- Enrichment status breakdown (not_started/processing/completed/failed)
- Quality score distribution (histogram)
- Average confidence by status
- Failure reasons breakdown (table)

**Dashboard 3: User Experience**
- Time to first error (form submission → error shown)
- Retry rate (failed enrichments retried)
- Warning dismissal rate
- User satisfaction survey results

### Alerts

```yaml
- alert: HighQualityGateFailureRate
  expr: rate(enrichment_validation_results{result="failed"}[15m]) > 0.1
  for: 5m
  annotations:
    summary: "Quality gate failing >10% of enrichments"
    description: "{{ $value | humanizePercentage }} of enrichments failing quality validation"

- alert: LowAverageEnrichmentQuality
  expr: avg(enrichment_quality_score) < 0.5
  for: 15m
  annotations:
    summary: "Average enrichment quality below threshold"
    description: "Average quality score: {{ $value }}"

- alert: HighFalsePositiveRate
  expr: rate(validation_false_positives_total[1h]) / rate(validation_warnings_total[1h]) > 0.05
  for: 30m
  annotations:
    summary: "Validation false positive rate >5%"

- alert: RaceConditionDetected
  expr: rate(validation_layer_errors{layer="3",error_type="evidence_not_found"}[5m]) > 0
  for: 1m
  annotations:
    summary: "Race condition detected (evidence not found after upload)"
```

### Monitoring Queries

**Enrichment Success Rate**:
```promql
sum(rate(artifact_enrichment_validation_total{result="passed"}[1h]))
/
sum(rate(artifact_enrichment_validation_total[1h]))
```

**Early Error Detection Rate**:
```promql
sum(rate(validation_layer_errors{layer=~"1|2|3"}[1h]))
/
sum(rate(validation_layer_errors[1h]))
```

**Quality Score P50/P95**:
```promql
histogram_quantile(0.50, enrichment_quality_score)
histogram_quantile(0.95, enrichment_quality_score)
```

---

## Edge Cases & Risks

### Edge Cases

#### 1. **No Evidence Sources**
**Scenario**: User creates artifact without any evidence links or files
**Current Behavior**: Enrichment returns early with fallback content (confidence=0.3)
**With Validation**: Will fail quality gate (short description + low confidence)
**Mitigation**: Validate evidence count before allowing "Enrich" button click

#### 2. **All Extractions Fail Due to Temporary Issues**
**Scenario**: GitHub API down, all repos return 503
**Current Behavior**: Silent failure, fallback content
**With Validation**: Will fail quality gate (0% extraction success)
**Mitigation**:
- Add retry logic with exponential backoff (already exists in TaskExecutor)
- Allow manual re-enrich after GitHub recovers
- Store extraction errors in metadata for debugging

#### 3. **Private GitHub Repos**
**Scenario**: User provides private repo URL
**Current Behavior**: 404 error, extraction fails
**With Validation**: Warn in Layer 2 (async validation), allow submission
**Mitigation**: Phase 2 feature - show warning but don't block

#### 4. **Very Long Articles/Descriptions**
**Scenario**: User pastes 10,000-word description from paper
**Current Behavior**: LLM truncates or times out
**With Validation**: May pass validation but produce low-quality unified description
**Mitigation**:
- Add max length validation (e.g., 5000 chars)
- Warn user before submission
- Already handled by LLM max_tokens parameter

#### 5. **File Uploaded but Deleted Before Enrichment**
**Scenario**: File upload succeeds, but file deleted from disk before Celery processes
**Current Behavior**: File not found error in extraction
**With Validation**: Will fail Layer 3 validation (file accessibility check)
**Mitigation**: Transaction ensures file + Evidence record created atomically

### Risks

#### Risk 1: **False Negatives (Thresholds Too Strict)**
**Description**: Quality thresholds reject valid enrichments
**Likelihood**: Medium
**Impact**: High (users frustrated by failed enrichments)
**Mitigation**:
- Start with conservative thresholds (confidence ≥0.5, not ≥0.7)
- Monitor false negative rate in first 2 weeks
- Allow manual override (admin can approve low-quality enrichments)
- Collect user feedback: "Was this enrichment actually bad?"
- A/B test threshold values with 10% of users

**Rollback Plan**: Lower thresholds in code, redeploy

#### Risk 2: **Transaction Timing Issues**
**Description**: `transaction.on_commit()` still triggers before Evidence committed
**Likelihood**: Low
**Impact**: Medium (race condition persists)
**Mitigation**:
- Django guarantees `on_commit()` runs after commit succeeds
- Add debug logging to verify timing
- Add integration test to verify Evidence exists before enrichment runs

**Rollback Plan**: Add manual 1-second delay if transaction timing unreliable

#### Risk 3: **Frontend Doesn't Handle New Fields**
**Description**: Old frontend version doesn't show `qualityWarnings`
**Likelihood**: Low (both deployed together)
**Impact**: Low (warnings not shown, but enrichment still works)
**Mitigation**:
- Progressive enhancement (check if field exists before rendering)
- Graceful degradation (old frontend ignores new fields)

**Rollback Plan**: No rollback needed (backward compatible)

#### Risk 4: **Increased Enrichment Failures**
**Description**: More enrichments marked as "failed" due to quality gates
**Likelihood**: High (expected - this is the fix!)
**Impact**: Medium (users see failures instead of silent poor quality)
**Mitigation**:
- This is a **positive change** (honest failures vs false success)
- Clear error messages guide users to fix issues
- Retry button available
- Monitor user satisfaction: "Did errors help you improve artifact?"

**Success Indicator**: Failure rate increases from ~5% to ~15%, but "false success" rate drops to 0%

#### Risk 5: **Performance Overhead**
**Description**: Validation adds latency to enrichment
**Likelihood**: Low
**Impact**: Low (<10ms added)
**Mitigation**:
- Validation is pure Python logic (no LLM calls, no I/O)
- Runs in-process after enrichment
- Measured: Validation ~5ms vs enrichment ~30-60s (0.01% overhead)

**Monitoring**: Track validation latency separately

---

## Implementation Phases

### Phase 1: Critical Fixes (Week 1) - MUST HAVE

**Files to Create**:
- ✅ `backend/llm_services/services/reliability/quality_validator.py`
- ✅ `backend/llm_services/tests/unit/services/reliability/test_quality_validator.py`

**Files to Modify**:
- ✅ `backend/artifacts/views.py` (file verification + transaction.on_commit)
- ✅ `backend/artifacts/tasks.py` (quality validation integration)
- ✅ `frontend/src/components/ArtifactEnrichmentStatus.tsx` (error display)

**Tests to Write** (TDD - write failing tests first):
1. Unit: Quality validator thresholds (9 test cases)
2. Integration: Quality gate in enrichment task (4 test cases)
3. Frontend: Error/warning display (3 test cases)

**Success Criteria**:
- Zero false "completed" statuses
- Clear error messages for failures
- File verification prevents race condition

### Phase 2: Progressive Enhancement (Week 2-3) - SHOULD HAVE

**Files to Create**:
- ✅ `backend/artifacts/validators.py` (async evidence validation)

**Files to Modify**:
- ✅ `backend/artifacts/urls.py` (add /validate-evidence/ endpoint)
- ✅ `backend/artifacts/views.py` (add validate_evidence view)
- ✅ `frontend/src/services/apiClient.ts` (add validateEvidence method)
- ✅ `frontend/src/components/ArtifactUpload.tsx` (async validation on blur)

**Tests to Write**:
1. Unit: GitHub validation (HEAD request)
2. Integration: Async validation endpoint
3. Frontend: Warning icon display

**Success Criteria**:
- Early error detection ≥80%
- Async validation <500ms P95

### Phase 3: Monitoring (Week 3-4) - NICE TO HAVE

**Files to Create**:
- ✅ `backend/monitoring/dashboards/enrichment_validation.json` (Grafana)
- ✅ `backend/monitoring/alerts/enrichment_quality.yml` (Prometheus)

**Files to Modify**:
- ✅ `backend/llm_services/services/reliability/quality_validator.py` (add metrics)

**Success Criteria**:
- Dashboards showing validation effectiveness
- Alerts firing for quality issues

---

## Rollback Plan

### Quick Rollback (< 5 minutes)

**If quality gates cause too many failures**:
1. Set feature flag: `ENABLE_QUALITY_GATES = False` in Django settings
2. Redeploy backend
3. All enrichments bypass validation (old behavior)

**If file verification causes upload failures**:
1. Comment out file verification block in `views.py:upload_artifact_files()`
2. Keep transaction coordination (still fixes race condition)
3. Redeploy backend

### Gradual Rollback (Adjust Thresholds)

**If false negative rate >20%**:
1. Lower quality thresholds in `EnrichmentQualityValidator`:
   ```python
   MIN_CONFIDENCE = 0.3  # Was 0.5
   MIN_DESCRIPTION_LENGTH = 50  # Was 100
   ```
2. Convert some errors to warnings
3. Redeploy and monitor for 24 hours

### Full Rollback (Revert Commit)

**If fundamental issues**:
1. `git revert <commit-hash>` for feature commit
2. Redeploy backend + frontend
3. All validation removed, back to original behavior

**Rollback Triggers**:
- False negative rate >20% for 24 hours
- User complaints >10 per day
- Enrichment failure rate >50%
- New bugs introduced in upload flow

---

## Related Documentation

**SPECs**:
- [spec-artifact-upload-enrichment-flow.md](../specs/spec-artifact-upload-enrichment-flow.md) (v1.1.0) - Validation architecture

**ADRs**:
- [adr-020-artifact-enrichment-quality-issues.md](../adrs/adr-020-artifact-enrichment-quality-issues.md) - Root cause analysis
- [adr-021-hybrid-validation-approach.md](../adrs/adr-021-hybrid-validation-approach.md) - Validation design decision

**Similar Features**:
- [ft-006-three-bullets-per-artifact.md](ft-006-three-bullets-per-artifact.md) - Bullet validation pattern
- [ft-005-multi-source-artifact-preprocessing.md](ft-005-multi-source-artifact-preprocessing.md) - Original enrichment design

**Architecture Patterns**:
- `docs/CLAUDE.md` - llm_services service layer structure
- `generation/services/bullet_validation_service.py` - Validation service example

---

