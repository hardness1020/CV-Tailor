# ADR: Fix Artifact Enrichment Quality Issues

**File:** docs/adrs/adr-020-artifact-enrichment-quality-issues.md
**Status:** Draft
**Date:** 2025-10-03
**Deciders:** Engineering Team, Backend Lead
**Technical Story:** Address user-reported enrichment quality issues

## Context and Problem Statement

Users report that artifact enrichment completes very quickly (within seconds) after upload, but the enriched content is of poor quality and appears to not have been processed by the LLM. The system shows "completed" status with high confidence, but the `unified_description` is minimal and `enriched_technologies`/`enriched_achievements` are empty or incorrect.

**Specific Issues Observed**:
1. Enrichment status changes to "completed" within 1-3 seconds of triggering
2. `unified_description` is just "{title}. {description}" (no LLM enhancement)
3. `enriched_technologies` is empty `[]` despite having evidence sources
4. `processing_confidence` shows 0.3 (very low) but status is "completed"
5. `sources_processed` shows 0, suggesting evidence wasn't found

**Expected Behavior**:
- Enrichment should take 30-60 seconds with real LLM calls
- Unified description should be 200-400 words synthesized from sources
- Technologies should be extracted from GitHub/PDFs
- Confidence should be >0.7 for quality enrichment

## Decision Drivers

- **User Experience**: Users expect high-quality enriched content for CV generation
- **System Reliability**: Silent failures undermine trust in the system
- **Data Quality**: Poor enrichment quality affects CV output quality
- **Transparency**: Users need visibility into processing issues
- **Debugging**: Need clear diagnostics to identify root causes

## Investigation Findings

### Root Cause #1: Race Condition with File Upload

**Issue**: Evidence records not found during enrichment.

**Flow**:
```
1. Frontend: POST /api/v1/artifacts/       → Creates artifact + evidence (from form)
2. Frontend: POST /artifacts/{id}/upload/  → Creates more evidence (uploaded files)
3. Frontend: POST /artifacts/{id}/enrich/  → Triggers enrichment immediately
4. Celery: enrich_artifact()               → Queries Evidence.objects.filter(artifact=...)
```

**Problem**: Step 3 triggers enrichment before Step 2's database transaction is fully committed.

**Evidence** from code (`backend/artifacts/views.py:227-230`, `tasks.py:100-108`):
```python
# Frontend waits for HTTP response, not DB commit
if uploadedFiles.length > 0:
    await apiClient.uploadArtifactFiles(artifact.id, uploadedFiles)
    # ↑ Returns 200 OK immediately
}

// Then immediately triggers enrichment
await apiClient.triggerEnrichment(artifact.id)

# Celery task starts before Evidence records committed
async for evidence in Evidence.objects.filter(artifact=artifact):
    # Returns [] if transaction not committed!
```

**Result**: Enrichment finds 0 evidence, returns early with fallback content.

---

### Root Cause #2: Silent LLM Failures with Fallback

**Issue**: LLM calls fail but enrichment still marks as "success".

**Code** (`backend/llm_services/services/core/artifact_enrichment_service.py:443-444`):
```python
unified_description = response.get('content', f"{artifact_title}. {artifact_description}")
#                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                              FALLBACK - no error raised!
```

**Why LLM Calls Fail**:
1. **API Keys Not Configured**: OpenAI/Anthropic keys missing or invalid
2. **Rate Limiting**: API quota exceeded
3. **Network Errors**: Timeout or connection failures
4. **Circuit Breaker**: Reliability layer opened due to repeated failures
5. **Mock/Test Mode**: LLM calls stubbed out in development environment

**Evidence**: When LLM fails, `_execute_llm_task()` returns `{'content': None}`, triggering fallback.

**Result**: Enrichment completes with minimal content but status="completed", success=True.

---

### Root Cause #3: Silent Extraction Failures

**Issue**: All source extractions fail but enrichment continues.

**Code** (`backend/llm_services/services/core/artifact_enrichment_service.py:346-366`):
```python
results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

for i, result in enumerate(results):
    if isinstance(result, Exception):
        logger.error(f"Extraction task {i} failed")
        extracted_contents.append(ExtractedContent(
            success=False,
            error_message=str(result)
        ))

successful_extractions = [ec for ec in extracted_contents if ec.success]
# ⚠️ Could be [] but enrichment continues!

unified_description = await unify_content_with_llm(
    extracted_contents=successful_extractions,  # Could be empty!
    ...
)
```

**Why Extractions Fail**:
1. **GitHub API Errors**: Rate limits, network errors, invalid repo URLs
2. **PDF Processing Errors**: Corrupted files, unsupported formats, encoding issues
3. **File Path Issues**: Uploaded files not accessible from Celery worker
4. **Media Storage Issues**: Files not found at expected path

**Result**: `successful_extractions = []`, LLM receives empty input, returns fallback.

---

### Root Cause #4: File Access from Celery Workers

**Issue**: Uploaded files not accessible during enrichment.

**Code** (`backend/llm_services/services/core/artifact_enrichment_service.py:289-293`):
```python
if evidence_type == 'document':
    if evidence.get('file_path'):  # e.g., "uploads/resume.pdf"
        pdf_load_result = await self.doc_loader.load_and_chunk_document(
            content=evidence['file_path'],  # Relative path!
            content_type='pdf',
        )
```

**Potential Issues**:
1. **Relative vs Absolute Paths**: `file_path` stored as relative, but Celery needs absolute
2. **Docker Volume Mounts**: Frontend uploads to one path, Celery reads from different mount
3. **Permissions**: Celery worker user lacks read access to uploaded files
4. **Storage Backend**: Files uploaded to S3 but Celery tries to read from local filesystem

**Result**: File not found → extraction fails → uses fallback content.

---

### Root Cause #5: No Quality Validation

**Issue**: Low-quality results still marked as "completed successfully".

**Code** (`backend/artifacts/tasks.py:177-192`):
```python
if result.success:  # ← Always True if no exception!
    processing_job.status = 'completed'
    processing_job.metadata_extracted = {
        'enrichment_success': True,
        ...
        'processing_confidence': 0.3,  # ← LOW but still "success"!
    }
```

**No Validation For**:
- Minimum confidence threshold (should fail if <0.5)
- Content length (description should be >100 chars)
- Extraction success rate (should warn if <50%)
- LLM fallback detection (should flag when fallback used)

**Result**: Poor quality enrichment shows as "completed" with green checkmark in UI.

## Considered Options

### Option A: Transaction Coordination

**Approach**: Ensure Evidence records are committed before enrichment.

**Implementation**:
```python
# In views.py upload_artifact_files()
from django.db import transaction

@transaction.atomic
def upload_artifact_files(request, artifact_id):
    for file in files:
        # Create UploadedFile and Evidence
        ...

    # Trigger enrichment AFTER transaction commits
    transaction.on_commit(
        lambda: enrich_artifact.delay(artifact_id=artifact_id, user_id=request.user.id)
    )
```

**Pros**:
- Guarantees Evidence records exist before enrichment
- Prevents race condition at source
- No changes to frontend needed

**Cons**:
- Still relies on database transaction timing
- Doesn't solve other issues (LLM failures, file access)

---

### Option B: Quality Validation Layer

**Approach**: Validate enrichment quality before marking as "completed".

**Implementation**:
```python
class EnrichmentQualityValidator:
    def validate(self, result: EnrichedArtifactResult) -> (bool, List[str]):
        errors = []
        warnings = []

        # Check extraction success rate
        if result.sources_processed > 0:
            success_rate = result.sources_successful / result.sources_processed
            if success_rate == 0:
                errors.append("All source extractions failed")
            elif success_rate < 0.5:
                warnings.append(f"Low extraction success: {success_rate:.0%}")

        # Check LLM enrichment quality
        if result.processing_confidence < 0.5:
            errors.append(f"Low confidence: {result.processing_confidence:.2f}")

        if len(result.unified_description) < 100:
            errors.append("Description too short - likely fallback content")

        if len(result.enriched_technologies) == 0:
            warnings.append("No technologies extracted")

        passed = len(errors) == 0
        return passed, errors, warnings

# In enrich_artifact task
result = await service.preprocess_multi_source_artifact(...)
passed, errors, warnings = validator.validate(result)

if not passed:
    processing_job.status = 'failed'
    processing_job.error_message = '; '.join(errors)
    processing_job.metadata_extracted['quality_warnings'] = warnings
else:
    processing_job.status = 'completed'
    processing_job.metadata_extracted['quality_warnings'] = warnings
```

**Pros**:
- Prevents low-quality results from showing as "success"
- Provides actionable error messages
- Easy to add more validation rules

**Cons**:
- Requires defining quality thresholds
- May need tuning based on real data

---

### Option C: Enhanced Error Reporting

**Approach**: Add detailed status tracking and diagnostics.

**Implementation**:
```python
# Add detailed progress tracking
processing_job.metadata_extracted = {
    'enrichment_success': True,
    'detailed_status': {
        'evidence_found': 3,
        'extraction_attempted': 3,
        'extraction_successful': 1,
        'extraction_failed': 2,
        'llm_calls': {
            'attempted': 1,
            'successful': 0,
            'used_fallback': True
        },
        'file_access_errors': [
            "File not found: uploads/resume.pdf"
        ]
    },
    'quality_warnings': [
        "Low extraction success rate (1/3 sources)",
        "LLM call failed, using fallback description",
        "Processing confidence below threshold (0.3)"
    ],
    ...
}
```

**Pros**:
- Provides full visibility into what went wrong
- Helps debugging in production
- Can surface warnings to users

**Cons**:
- More complex metadata structure
- Requires UI updates to display warnings

---

### Option D: File Verification Before Extraction

**Approach**: Verify file accessibility before attempting extraction.

**Implementation**:
```python
# In artifact_enrichment_service.py
if evidence_type == 'document':
    if evidence.get('file_path'):
        # Verify file exists
        file_path = evidence['file_path']
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        if not os.path.exists(full_path):
            logger.error(f"File not found: {full_path}")
            logger.error(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
            logger.error(f"Current working directory: {os.getcwd()}")

            extraction_tasks.append(self._create_failed_extraction(
                'document',
                url,
                f"File not accessible: {file_path}"
            ))
            continue

        # File exists, proceed with extraction
        pdf_load_result = await self.doc_loader.load_and_chunk_document(
            content=full_path,  # Use absolute path
            ...
        )
```

**Pros**:
- Catches file access issues early
- Provides clear error messages
- Helps diagnose Docker/storage issues

**Cons**:
- Doesn't fix the underlying storage configuration
- Still need to identify root cause

---

### Option E: Comprehensive Fix (All Above)

**Approach**: Combine all solutions for robust enrichment.

**Implementation**: Apply all fixes:
1. Transaction coordination for race condition
2. Quality validation before completion
3. Enhanced error reporting for debugging
4. File verification for diagnostics

**Pros**:
- Addresses all identified issues
- Robust and production-ready
- Good user experience

**Cons**:
- More implementation work
- Higher complexity

## Decision Outcome

**Chosen Option: Option E - Comprehensive Fix**

### Rationale

The issues are interconnected and require multiple fixes:
- **Race condition** needs transaction coordination
- **LLM failures** need quality validation
- **Extraction failures** need error reporting
- **File access** needs verification

Partial fixes would still leave gaps. A comprehensive approach ensures:
1. High-quality enrichment or clear failure messages
2. Diagnostic information for debugging
3. Better user experience
4. Production reliability

### Implementation Plan

**Phase 1: Immediate Fixes (Week 1)**
1. Add quality validation layer (Option B)
2. Add file verification (Option D)
3. Enhanced logging for diagnostics

**Phase 2: Structural Improvements (Week 2)**
4. Transaction coordination (Option A)
5. Enhanced error reporting (Option C)
6. UI updates to show warnings

**Phase 3: Monitoring (Week 3)**
7. Add Prometheus metrics for quality
8. Set up alerts for failures
9. Dashboard for enrichment health

### Success Criteria

**Immediate**:
- Enrichment failures properly reported (not "completed" with low quality)
- Clear error messages when file access fails
- Warnings surfaced when extraction fails

**Long-term**:
- Enrichment quality (confidence >0.7): ≥85% of artifacts
- User satisfaction with enriched content: ≥8/10
- Zero false "success" statuses (low quality marked as failed)

## Positive Consequences

- **Better UX**: Users see real errors instead of false success
- **Easier Debugging**: Detailed diagnostics help identify issues
- **Higher Quality**: Validation ensures minimum quality threshold
- **Transparency**: Users understand what went wrong
- **Reliability**: Catches issues before they reach users

## Negative Consequences

- **More Complexity**: Additional validation and reporting logic
- **Longer Implementation**: Comprehensive fix takes more time
- **Potential False Negatives**: Quality thresholds may reject valid results
- **More Status States**: UI needs to handle warnings/partial success

## Mitigation Strategies

**For False Negatives**:
- Start with conservative thresholds (confidence >0.5)
- Allow manual override/re-enrich
- Collect user feedback to tune thresholds

**For Complexity**:
- Centralize validation logic in single class
- Write comprehensive unit tests
- Document validation rules clearly

**For UI Changes**:
- Progressive enhancement (show warnings if available)
- Graceful degradation (work with old responses)
- A/B test new UI with subset of users

## Monitoring and Success Metrics

### Key Metrics

**Quality Metrics**:
```python
enrichment_quality = Histogram(
    'artifact_enrichment_quality',
    'Enrichment quality distribution',
    buckets=[0.3, 0.5, 0.7, 0.9, 1.0]
)

enrichment_failures = Counter(
    'artifact_enrichment_failures',
    'Enrichment failure reasons',
    ['failure_type']  # 'race_condition', 'llm_failure', 'extraction_failure', etc.
)
```

**Dashboards**:
- Enrichment quality distribution (confidence scores)
- Failure breakdown by type
- File access error trends
- LLM fallback usage rate

**Alerts**:
- Enrichment quality <0.5 for >20% of jobs (15 min window)
- File access failures >10% (5 min window)
- LLM fallback rate >30% (15 min window)

### Success Thresholds

| Metric | Current | Target (1 month) |
|--------|---------|-----------------|
| Avg Confidence | 0.3-0.5 | >0.75 |
| False Success Rate | ~50% | <5% |
| File Access Success | Unknown | >95% |
| LLM Call Success | Unknown | >90% |
| User Satisfaction | Unknown | ≥8/10 |

## Rollout Plan

**Week 1: Validation & Diagnostics**
- Deploy quality validation layer
- Add enhanced logging
- Monitor for new error patterns

**Week 2: Structural Fixes**
- Deploy transaction coordination
- Add file verification
- Update error reporting

**Week 3: UI & Monitoring**
- Deploy UI changes for warnings
- Set up dashboards
- Configure alerts

**Rollback Triggers**:
- False negative rate >20% (quality validation too strict)
- New errors exceeding current error rate
- User complaints about failed enrichments

## References

### Related Specifications
- [spec-artifact-upload-enrichment-flow.md](../specs/spec-artifact-upload-enrichment-flow.md) - Current implementation
- [spec-api.md](../specs/spec-api.md) - API contracts

### Related ADRs
- [adr-015-multi-source-artifact-preprocessing.md](adr-015-multi-source-artifact-preprocessing.md) - Original preprocessing design

### Related Features
- [ft-001-artifact-upload.md](../features/ft-001-artifact-upload.md) - Upload system
- [ft-005-multi-source-artifact-preprocessing.md](../features/ft-005-multi-source-artifact-preprocessing.md) - Preprocessing requirements

### External Resources
- Django transaction.on_commit: https://docs.djangoproject.com/en/4.2/topics/db/transactions/#performing-actions-after-commit
- Celery error handling: https://docs.celeryq.dev/en/stable/userguide/tasks.html#error-handling

## Immediate Next Steps for User

To debug the current issues:

1. **Check Celery Worker Logs**:
   ```bash
   docker-compose logs celery --tail=100 --follow
   ```
   Look for:
   - "Found X evidence links" (should be >0)
   - Extraction failures
   - File not found errors
   - LLM API errors

2. **Inspect Processing Job**:
   ```bash
   docker-compose exec backend uv run python manage.py shell
   ```
   ```python
   from artifacts.models import Artifact
   artifact = Artifact.objects.latest('created_at')
   job = artifact.processing_jobs.latest('created_at')
   print(f"Status: {job.status}")
   print(f"Confidence: {artifact.processing_confidence}")
   print(f"Metadata: {json.dumps(job.metadata_extracted, indent=2)}")
   ```

3. **Check Evidence Records**:
   ```python
   for e in artifact.evidence.all():
       print(f"{e.evidence_type}: {e.url}")
       print(f"  file_path: {e.file_path}")
       if e.file_path:
           import os
           full_path = os.path.join('/app/media', e.file_path)
           print(f"  exists: {os.path.exists(full_path)}")
   ```

4. **Verify LLM API Configuration**:
   ```bash
   docker-compose exec backend env | grep -E 'OPENAI|ANTHROPIC'
   ```

