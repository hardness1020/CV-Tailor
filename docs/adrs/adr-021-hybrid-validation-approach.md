# ADR: Hybrid Validation Approach for Artifact Evidence

**File:** docs/adrs/adr-021-hybrid-validation-approach.md
**Status:** Draft
**Date:** 2025-10-03
**Deciders:** Engineering Team, Backend Lead, Frontend Lead
**Technical Story:** Improve evidence validation UX and reduce failed enrichments

## Context and Problem Statement

Users currently experience poor UX when uploading artifacts with evidence sources:

**Current Pain Points:**
1. **Delayed error feedback**: Invalid GitHub URLs cause enrichment to fail 30-60 seconds after submission
2. **Silent failures**: Corrupted files fail during processing without clear error messages
3. **False success**: All evidence extractions fail but enrichment marked as "completed" with low quality
4. **Wasted processing**: Invalid evidence sources consume Celery worker time and LLM API quota
5. **User confusion**: Unclear what went wrong or how to fix it

**User Journey Example:**
```
1. User uploads artifact with GitHub URL: "https://github.com/user/typo-repo"
2. User waits 45 seconds
3. Enrichment shows "Completed" ✓
4. But: unified_description is just "{title}. {description}" (no LLM enhancement)
5. User doesn't know why quality is poor
```

**Related Issues:**
- Race condition: Evidence not committed before enrichment starts (ADR-020-artifact-enrichment-quality-issues)
- LLM failures with fallback: Silent failures still marked as "success"
- No quality validation: Low confidence results (0.3) shown as "completed"

## Decision Drivers

- **User Experience**: Immediate feedback is critical for form usability
- **System Reliability**: Prevent wasted enrichment jobs on invalid evidence
- **Flexibility**: Don't block submission for temporary issues (GitHub down, private repos)
- **Performance**: Validation overhead must not slow down happy path
- **Transparency**: Clear error messages guide users to fix issues
- **Graceful Degradation**: System works even if some evidence is inaccessible

## Considered Options

### Option A: Early Validation Only

**Approach**: Validate all evidence during form submission (before artifact creation)

**Implementation**:
```typescript
// Frontend validates GitHub URL before submission
const validateEvidence = async (url: string, type: string) => {
  if (type === 'github') {
    const response = await apiClient.validateGitHubRepo(url)
    if (!response.accessible) {
      throw new Error('GitHub repository not accessible')
    }
  }
}

// Block submission if any evidence invalid
await Promise.all(evidenceLinks.map(link => validateEvidence(link.url, link.type)))
```

**Pros:**
- ✅ Immediate feedback - user fixes issues before submitting
- ✅ Prevents creating artifacts with invalid evidence
- ✅ Reduces failed enrichment jobs
- ✅ Simple error handling (before submission)

**Cons:**
- ❌ Slow form interaction (API calls during submission)
- ❌ **Blocks submission if GitHub temporarily down**
- ❌ **Blocks private repos that user can access**
- ❌ More complex frontend validation logic
- ❌ Extra API load (validation + actual processing)
- ❌ Doesn't catch file accessibility issues (only validate after upload)

---

### Option B: Late Validation Only (Current Approach)

**Approach**: Validate evidence during enrichment processing (no early checks)

**Implementation**:
```python
# Current: Validation happens in Celery worker
async def enrich_artifact(artifact_id):
    evidence = await Evidence.objects.filter(artifact_id=artifact_id)
    for e in evidence:
        try:
            content = await extract_content(e)
        except Exception:
            logger.error(f"Extraction failed: {e.url}")
            # Continue with other sources...
```

**Pros:**
- ✅ Fast form submission (no blocking)
- ✅ Can retry if external services temporarily unavailable
- ✅ Simple frontend (no validation logic)
- ✅ Works with private repos (if Celery has access)

**Cons:**
- ❌ **User discovers issues 30-60 seconds later** (after enrichment fails)
- ❌ **Silent failures** (current bug - fallback used)
- ❌ Wasted Celery worker time on obviously invalid evidence
- ❌ Wasted LLM API quota
- ❌ Poor UX - feels broken

---

### Option C: Hybrid Approach (4 Validation Layers) ⭐

**Approach**: Progressive validation at multiple stages

**Implementation**:

#### Layer 1: Synchronous Frontend Validation (Immediate)
```typescript
// Zod schema validation during form input
const evidenceLinkSchema = z.object({
  url: z.string().url('Please enter a valid URL'),
  evidence_type: z.enum(['github', 'live_app', ...]),
})

// File validation on drop
- File size: Max 10MB
- File type: Only PDF/DOC/DOCX
```
**Coverage**: URL format, file size/type
**UX**: Red error text immediately

#### Layer 2: Async Pre-flight Checks (On blur/add)
```typescript
// Debounced validation when user moves to next field
const validateGitHubUrl = async (url: string) => {
  const result = await apiClient.validateEvidence({ url, evidence_type: 'github' })
  if (!result.accessible) {
    showWarning('⚠️ Repository not found. You can still submit.')
  }
}
```
**Coverage**: GitHub repo exists, live app responds
**UX**: Warning icon (⚠️) but allows submission

#### Layer 3: Upload Validation (Before enrichment)
```python
# Backend verifies files after upload
@transaction.atomic
def upload_artifact_files(request, artifact_id):
    for file in files:
        # Create UploadedFile and Evidence
        uploaded_file = UploadedFile.objects.create(...)

        # Verify file accessible
        if not os.path.exists(uploaded_file.file_path):
            return Response({'error': f'File not accessible: {file.name}'}, status=400)

    # Trigger enrichment AFTER transaction commits
    transaction.on_commit(lambda: enrich_artifact.delay(artifact_id))
```
**Coverage**: File exists, readable, Evidence committed
**UX**: File upload fails with clear error

#### Layer 4: Enrichment Quality Gates (During processing)
```python
# Quality validator in Celery worker
class EnrichmentQualityValidator:
    def validate(self, result: EnrichedArtifactResult) -> (bool, errors, warnings):
        errors = []
        if result.processing_confidence < 0.5:
            errors.append(f"Low confidence: {result.processing_confidence}")
        if len(result.unified_description) < 100:
            errors.append("Description too short - likely fallback")
        return len(errors) == 0, errors, warnings

# In enrich_artifact task
result = await service.preprocess_multi_source_artifact(...)
passed, errors, warnings = validator.validate(result)

if not passed:
    processing_job.status = 'failed'
    processing_job.error_message = '; '.join(errors)
else:
    processing_job.status = 'completed'
    processing_job.metadata_extracted['quality_warnings'] = warnings
```
**Coverage**: Confidence thresholds, content quality, extraction success
**UX**: Failed enrichment with detailed error + warnings

**Pros:**
- ✅ Immediate feedback for obvious errors (Layer 1)
- ✅ Quick async checks for accessibility (Layer 2)
- ✅ **Allows submission even with warnings** (flexibility)
- ✅ Prevents race conditions (Layer 3)
- ✅ Catches quality issues before marking "completed" (Layer 4)
- ✅ Better error reporting at every stage
- ✅ Graceful degradation (some evidence can fail)
- ✅ Reduces failed enrichments (~40% → <10% target)

**Cons:**
- ❌ More complex implementation (4 layers)
- ❌ Extra API load (validation requests)
- ❌ Need to tune quality thresholds
- ❌ Potential false positives (repo temporarily down)

---

### Option D: No Validation

**Approach**: Trust user input, handle all errors during enrichment

**Pros:**
- ✅ Simplest implementation

**Cons:**
- ❌ Current state - poor UX, silent failures
- ❌ Not acceptable given user feedback

---

## Decision Outcome

**Chosen Option: Option C - Hybrid Approach (4 Validation Layers)**

### Rationale

The issues are **interconnected** and require **multiple fixes**:
- Immediate user errors (typos, wrong file type) → Layer 1 (sync validation)
- External resource issues (GitHub down) → Layer 2 (async with warnings)
- File access failures → Layer 3 (upload verification)
- LLM/extraction quality → Layer 4 (quality gates)

**Partial fixes leave gaps:**
- Early-only (Option A) blocks valid use cases (private repos, temporary issues)
- Late-only (Option B) provides poor UX (30-60s delay)
- Hybrid approach balances **early feedback** with **flexibility**

**Key Principle**: **Warn, don't block**
- Layer 1: Block (invalid input)
- Layer 2: Warn (inaccessible but allow)
- Layer 3: Block (file upload failed)
- Layer 4: Fail enrichment (quality too low)

### Implementation Plan

**Phase 1: Critical Fixes (Week 1) - Must Have**
1. ✅ Layer 3: File accessibility validation
   - Verify files readable after upload
   - Use `transaction.on_commit()` to prevent race condition
2. ✅ Layer 4: Quality validation
   - Create `EnrichmentQualityValidator` class
   - Fail if confidence <0.5 or all extractions failed
   - Add detailed error messages
3. ✅ Update frontend error handling
   - Display detailed error messages from enrichment
   - Show warnings for low quality

**Phase 2: Progressive Enhancement (Week 2-3) - Should Have**
4. ⚠️ Layer 2: Async GitHub validation endpoint
   - `POST /api/v1/artifacts/validate-evidence/`
   - Lightweight HEAD request to check repo exists
   - Return warning (not error) if inaccessible
5. ⚠️ Frontend async validation integration
   - Debounced validation on blur
   - Show warning icon (⚠️) but allow submission

**Phase 3: Monitoring (Week 3-4) - Nice to Have**
6. ⚠️ Add Prometheus metrics
   - Early error detection rate
   - False positive rate
   - Quality gate accuracy
7. ⚠️ Set up alerts
   - Quality failures >10% (15 min window)
   - Validation false positives >5%

### Success Criteria

**Immediate (Phase 1)**:
- Zero false "completed" statuses (low quality marked as failed)
- Clear error messages when file access fails
- Enrichment failures properly reported

**Long-term (Phase 2-3)**:
- Early error detection: ≥80% of issues caught before enrichment
- Enrichment failure rate: <10% (down from ~40%)
- User satisfaction with error messages: ≥85%
- False positive rate: <5%

## Positive Consequences

- **Better UX**: Immediate feedback for obvious errors
- **Reduced wasted work**: Invalid evidence caught early
- **Clearer errors**: Users understand what went wrong
- **Higher quality**: Quality gates prevent low-quality "success"
- **Flexibility**: Warnings don't block submission
- **Transparency**: Detailed error messages guide users
- **Reliability**: Catches issues before they reach users

## Negative Consequences

- **More complexity**: Additional validation and reporting logic (4 layers)
- **Longer implementation**: Comprehensive fix takes 3-4 weeks
- **Potential false negatives**: Quality thresholds may reject valid results
- **More status states**: UI needs to handle warnings/partial success
- **Extra API load**: Validation requests add overhead
- **Tuning required**: Quality thresholds need adjustment based on real data

## Mitigation Strategies

**For False Negatives** (quality thresholds too strict):
- Start with conservative thresholds (confidence >0.5, not >0.7)
- Allow manual override/re-enrich
- Collect user feedback to tune thresholds
- A/B test threshold values with 10% of users

**For Complexity** (4 validation layers):
- Centralize validation logic in single service class
- Write comprehensive unit tests for each layer
- Document validation rules clearly in SPEC
- Gradual rollout (Phase 1 → Phase 2 → Phase 3)

**For False Positives** (accessibility warnings wrong):
- Retry validation before showing warning
- Cache validation results (15 min TTL)
- Allow user to dismiss warnings
- Monitor false positive rate (<5% target)

**For UI Changes** (warnings/errors display):
- Progressive enhancement (show warnings if available)
- Graceful degradation (work with old responses)
- A/B test new UI with subset of users
- Provide "What went wrong?" help text

## Rollback Plan

**If validation causes issues**, we can disable layers independently:

1. **Phase 2 rollback** (async validation):
   - Feature flag: `ENABLE_ASYNC_VALIDATION = False`
   - Frontend skips Layer 2 checks
   - No breaking changes (optional feature)

2. **Phase 1 rollback** (quality gates):
   - Feature flag: `ENABLE_QUALITY_GATES = False`
   - Mark all enrichments as "completed" (old behavior)
   - Keep detailed logging for diagnosis

3. **Partial rollback** (thresholds too strict):
   - Lower quality thresholds (0.5 → 0.3)
   - Convert errors to warnings
   - Continue collecting data

**Rollback Triggers**:
- False negative rate >20% (quality validation too strict)
- User complaints about blocked submissions
- Validation API errors >10%
- New enrichment failures exceeding baseline

## Monitoring and Success Metrics

### Key Metrics (Prometheus)

```python
# Early error detection
validation_errors = Counter(
    'artifact_validation_errors_total',
    'Validation errors by layer',
    ['layer', 'error_type']  # layer: 1-4, error_type: 'format', 'accessibility', 'quality'
)

# Quality gate effectiveness
quality_gate_results = Counter(
    'enrichment_quality_gate_total',
    'Quality validation results',
    ['result']  # 'passed', 'failed', 'warning'
)

# Enrichment outcome distribution
enrichment_outcome = Counter(
    'artifact_enrichment_outcome_total',
    'Enrichment final status',
    ['status', 'quality_gate']  # status: 'completed'/'failed', quality_gate: 'passed'/'bypassed'
)

# Validation API performance
validation_api_duration = Histogram(
    'validation_api_duration_seconds',
    'Validation API latency',
    ['evidence_type']
)
```

### Dashboards

**Validation Effectiveness Dashboard**:
- Early error detection rate (Layer 1-3 vs Layer 4)
- Enrichment failure breakdown by cause
- Quality gate pass/fail/warning distribution
- False positive trend (accessibility warnings)

**User Experience Dashboard**:
- Time to first error (form submission to error shown)
- Validation feedback helpfulness (survey)
- Enrichment retry rate (after quality failure)

### Alerts

```yaml
- alert: HighQualityFailureRate
  expr: rate(quality_gate_results{result="failed"}[15m]) > 0.1
  annotations:
    summary: "Quality gate failing >10% of enrichments"

- alert: HighValidationFalsePositives
  expr: validation_false_positives_rate > 0.05
  annotations:
    summary: "Validation false positive rate >5%"

- alert: ValidationAPILatency
  expr: histogram_quantile(0.95, validation_api_duration_seconds) > 2.0
  annotations:
    summary: "Validation API P95 latency >2s"
```

### Success Thresholds

| Metric | Baseline (Pre-Validation) | Target (1 month) | Measured |
|--------|---------------------------|------------------|----------|
| Enrichment Failure Rate | ~40% | <10% | ArtifactProcessingJob.status='failed' |
| Early Error Detection | 0% | ≥80% | (Layer 1-3 errors) / (total errors) |
| Avg Processing Confidence | 0.3-0.5 | >0.7 | Artifact.processing_confidence |
| False Positive Rate | N/A | <5% | Manual validation of warnings |
| User Satisfaction | Unknown | ≥85% | Survey: "Error messages helpful?" |
| Time to First Error | 45s avg | <2s | Validation layer 1-2 latency |

## Links

### Related Specifications
- **SPEC**: [spec-artifact-upload-enrichment-flow.md](../specs/spec-artifact-upload-enrichment-flow.md) (v1.1.0) - Validation design documentation
- **API Contracts**: [spec-api.md](../specs/spec-api.md) - API endpoint specifications

### Related ADRs
- **ADR-20251003**: [adr-020-artifact-enrichment-quality-issues.md](adr-020-artifact-enrichment-quality-issues.md) - Root cause analysis for enrichment quality
- **ADR-20250927**: [adr-015-multi-source-artifact-preprocessing.md](adr-015-multi-source-artifact-preprocessing.md) - Original preprocessing design

### Related Features
- **ft-001**: [ft-001-artifact-upload.md](../features/ft-001-artifact-upload.md) - Artifact upload system
- **ft-005**: [ft-005-multi-source-artifact-preprocessing.md](../features/ft-005-multi-source-artifact-preprocessing.md) - Multi-source preprocessing requirements

### External Resources
- **Django Transactions**: https://docs.djangoproject.com/en/4.2/topics/db/transactions/#performing-actions-after-commit
- **React Hook Form Validation**: https://react-hook-form.com/docs/useform/register#options
- **Zod Schema Validation**: https://zod.dev/

