# ADR — Consolidate Evidence Storage to Single Model (EnhancedEvidence)

**Status:** Draft → Accepted (upon implementation completion)
**Date:** 2025-01-06
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-045 Evidence Review & Acceptance Workflow

## Context and Problem Statement

The application currently maintains **two separate storage models** for evidence content extraction:

**1. ExtractedContent (Intermediate Storage)**
```python
class ExtractedContent(models.Model):
    """Per-source extraction results for multi-source artifact preprocessing"""
    preprocessing_job = ForeignKey('ArtifactProcessingJob')
    source_type = CharField  # github, pdf, video, audio, web_link, text
    raw_data = JSONField
    processed_summary = TextField
    extraction_confidence = FloatField
    # ...metadata fields
```

**2. EnhancedEvidence (User-Facing Storage)**
```python
class EnhancedEvidence(models.Model):
    """Enhanced content from a SINGLE evidence source"""
    evidence = OneToOneField('Evidence')
    raw_content = TextField
    processed_content = JSONField  # Structured achievements, skills
    processing_confidence = FloatField
    accepted = BooleanField  # User acceptance tracking
    # ...metadata fields
```

**Current Data Flow (Problematic):**
```
Evidence extraction via Celery
  ↓
Create ExtractedContent (intermediate)
  ↓
Create EnhancedEvidence (copy data from ExtractedContent)
  ↓
ExtractedContent never queried again (stale)
  ↓
EnhancedEvidence used for artifact unification and user display
  ↓
User edits EnhancedEvidence (evidence review workflow)
  ✗ ExtractedContent remains unchanged (out of sync)
  ✗ Two versions of same data (redundancy)
  ✗ Confusion about which is source of truth
```

**Problems with Dual Storage:**

1. **Data Redundancy:** Same content stored twice (ExtractedContent.processed_summary ≈ EnhancedEvidence.processed_content)
2. **Synchronization Issues:** User edits in evidence review update EnhancedEvidence but not ExtractedContent (data divergence)
3. **Storage Waste:** ExtractedContent never deleted, accumulates indefinitely (178 usages across codebase but rarely queried after creation)
4. **Code Complexity:** Developers must understand two models for same conceptual entity
5. **Migration Burden:** Schema changes require updating both models
6. **Query Confusion:** Which model should be queried? (Answer: Always EnhancedEvidence in practice)
7. **Audit Trail Illusion:** ExtractedContent appears to track history but doesn't (single version per job)

**Discovery Findings (disco-001-evidence-review-workflow.md):**
> "ExtractedContent is redundant storage that duplicates EnhancedEvidence. After initial extraction, all queries go to EnhancedEvidence. ExtractedContent is write-once, never updated, never queried after creation. Consolidate to EnhancedEvidence as single source of truth."

**We need to decide:**

1. **Which model to keep:** ExtractedContent vs. EnhancedEvidence vs. new unified model
2. **How to migrate:** Data migration strategy for existing ExtractedContent records
3. **History tracking:** Whether to preserve extraction history or single version
4. **Foreign key updates:** How to handle GitHubRepositoryAnalysis.extracted_content references
5. **Test cleanup:** How to handle 178 ExtractedContent references across 32 files

## Decision Drivers

- **Single Source of Truth:** One canonical storage for evidence content (DRY principle)
- **Data Consistency:** User edits should update the only version (no sync issues)
- **User-Facing Model:** EnhancedEvidence has user acceptance fields (accepted, accepted_at)
- **Storage Efficiency:** Eliminate redundant storage (save database space)
- **Code Simplicity:** Reduce cognitive load (one model to understand)
- **Evidence Review Workflow:** ft-045 requires editable evidence storage (EnhancedEvidence.processed_content)
- **Query Performance:** Fewer tables to join, simpler queries
- **Migration Safety:** Preserve existing data during consolidation

## Considered Options

### Option A: Keep Both Models (Status Quo)

**Approach:** Maintain ExtractedContent and EnhancedEvidence as separate storage

**Pros:**
- No migration effort
- No risk of data loss
- Existing code continues to work

**Cons:**
- **Data redundancy:** Wasted storage and sync complexity
- **Divergence risk:** User edits EnhancedEvidence, ExtractedContent stale
- **Confusion:** Developers unclear which model to query
- **Violates DRY:** Same data in two places
- **Blocks evidence review:** Unclear which model to update on user edit

**Estimated Effort:** 0 hours (no change)

---

### Option B: Consolidate to ExtractedContent (Discard EnhancedEvidence)

**Approach:** Keep ExtractedContent, migrate EnhancedEvidence data, delete EnhancedEvidence model

**Pros:**
- ExtractedContent has preprocessing_job relationship (richer metadata)
- Preserves extraction pipeline history

**Cons:**
- **Missing acceptance fields:** ExtractedContent lacks `accepted`, `accepted_at` (required for ft-045)
- **Wrong abstraction:** ExtractedContent is job-scoped, not evidence-scoped
- **API breaking change:** All EnhancedEvidence API endpoints must change
- **More complex migration:** 32 files reference EnhancedEvidence
- **No OneToOne with Evidence:** ExtractedContent doesn't link to Evidence model directly

**Estimated Effort:** 20-24 hours (complex migration + API changes)

---

### Option C: Consolidate to EnhancedEvidence (Remove ExtractedContent) ✅ Recommended

**Approach:** Keep EnhancedEvidence as single source of truth, migrate ExtractedContent data, delete ExtractedContent model

**Pros:**
- **User-facing model:** EnhancedEvidence already has acceptance workflow fields
- **Evidence-scoped:** OneToOne relationship with Evidence model (correct abstraction)
- **Simpler API:** No changes to existing EnhancedEvidence endpoints
- **Less migration:** ExtractedContent is intermediate storage, rarely queried
- **Supports ft-045:** EnhancedEvidence.processed_content is editable by users
- **Clear ownership:** One model, one source of truth

**Cons:**
- **History loss:** ExtractedContent could theoretically track re-extractions (but doesn't in practice)
- **Foreign key cleanup:** GitHubRepositoryAnalysis.extracted_content must be removed or made optional
- **Test updates:** 32 files with ExtractedContent references need cleanup

**Estimated Effort:** 8-12 hours (migration + foreign key cleanup + test updates)

---

### Option D: Create Unified EvidenceContent Model (New Model)

**Approach:** Create new model combining best of both, migrate both ExtractedContent and EnhancedEvidence

**Pros:**
- Clean slate design
- Incorporate lessons learned
- Optimal field structure

**Cons:**
- **Highest migration cost:** Move data from two models to one
- **Breaking changes:** All APIs must change
- **Over-engineering:** Existing EnhancedEvidence is already sufficient
- **Delayed delivery:** Blocks ft-045 implementation

**Estimated Effort:** 16-20 hours (design + double migration + API changes)

---

### Option E: Soft Delete ExtractedContent (Keep Schema, Stop Using)

**Approach:** Stop creating ExtractedContent records, mark model as deprecated, keep schema for historical data

**Pros:**
- No data migration needed
- Historical ExtractedContent preserved
- Gradual deprecation path

**Cons:**
- **Schema debt:** Unused table occupies database
- **Code confusion:** Deprecated model still in codebase
- **Incomplete solution:** Still have redundancy for existing records
- **Delayed cleanup:** Eventually need full removal anyway

**Estimated Effort:** 4-6 hours (deprecation markers + stop creating new records)

## Decision Outcome

**Chosen Option: Option C - Consolidate to EnhancedEvidence (Remove ExtractedContent)**

### Rationale

1. **EnhancedEvidence is User-Facing Model:**
   - Has acceptance workflow fields (accepted, accepted_at) required for ft-045
   - OneToOne relationship with Evidence model (correct abstraction)
   - processed_content field is user-editable (inline editing in evidence review)
   - Already returned by all evidence API endpoints

2. **ExtractedContent is Intermediate Storage Only:**
   - Created during extraction, then never queried again
   - Data immediately copied to EnhancedEvidence
   - No user-facing functionality depends on it
   - Removal has minimal impact (intermediate storage pattern)

3. **Prevents Data Divergence:**
   - User edits EnhancedEvidence.processed_content in evidence review
   - Without consolidation, ExtractedContent becomes stale
   - Single model = single version = no sync issues

4. **Simplifies Codebase:**
   - One model to understand (reduced cognitive load)
   - Simpler queries (no joins with ExtractedContent)
   - Clear data flow: Evidence → EnhancedEvidence → User acceptance → Artifact unification

5. **Lowest Migration Cost:**
   - ExtractedContent data is redundant (already in EnhancedEvidence)
   - No data loss (EnhancedEvidence has all necessary fields)
   - Foreign key cleanup is straightforward (GitHubRepositoryAnalysis)

6. **Enables Evidence Review Workflow:**
   - EnhancedEvidence.processed_content is the editable storage
   - EnhancedEvidence.accepted tracks user acceptance
   - No confusion about which model to update

### Architecture Decision

**Data Model After Consolidation:**
```python
# KEEP: EnhancedEvidence (single source of truth)
class EnhancedEvidence(models.Model):
    evidence = OneToOneField('Evidence')  # Link to source
    raw_content = TextField              # Original content
    processed_content = JSONField        # User-editable structured data
    processing_confidence = FloatField   # Extraction quality
    accepted = BooleanField              # User acceptance (ft-045)
    accepted_at = DateTimeField          # Acceptance timestamp (ft-045)
    # ... metadata fields

# REMOVE: ExtractedContent (redundant intermediate storage)
# class ExtractedContent(models.Model):  # DELETE THIS MODEL
```

**Foreign Key Cleanup:**
```python
# GitHubRepositoryAnalysis currently references ExtractedContent
class GitHubRepositoryAnalysis(models.Model):
    evidence = OneToOneField('Evidence')  # Already has this
    # extracted_content = OneToOneField(ExtractedContent)  # REMOVE THIS
    # No replacement needed - evidence → enhanced_version gives EnhancedEvidence
```

**Migration Strategy:**

**Phase 1: Data Verification (Pre-Migration)**
1. Verify all ExtractedContent data is in EnhancedEvidence
2. Identify orphaned ExtractedContent records (no matching EnhancedEvidence)
3. Backup database before migration

**Phase 2: Foreign Key Removal**
1. Remove GitHubRepositoryAnalysis.extracted_content field (migration)
2. Update GitHubRepositoryAgent to not create ExtractedContent
3. Update EvidenceContentExtractor to only create EnhancedEvidence

**Phase 3: Model Removal**
1. Delete ExtractedContent model from models.py
2. Remove ExtractedContent from admin.py
3. Create migration to drop extracted_content table

**Phase 4: Code Cleanup**
1. Remove ExtractedContent imports (32 files)
2. Update tests to use EnhancedEvidence only
3. Update documentation references

**Phase 5: Verification**
1. Run full test suite
2. Verify no broken foreign keys
3. Check API endpoints still work

### No History Tracking Needed

**User confirmed:** "Not necessary to keep the history of extraction"

- ExtractedContent doesn't track history (single version per job)
- Re-extraction would overwrite ExtractedContent anyway
- EnhancedEvidence is the final version after user review
- History tracking adds complexity without value (YAGNI principle)

## Consequences

### Positive

1. **Single Source of Truth:**
   - EnhancedEvidence is canonical storage
   - No confusion about which model to query
   - DRY principle enforced

2. **Data Consistency:**
   - User edits update the only version
   - No sync issues between models
   - accepted field accurately tracks user acceptance

3. **Simplified Codebase:**
   - One model instead of two (reduced cognitive load)
   - Simpler queries (no ExtractedContent joins)
   - Less code to maintain (fewer migrations, tests, admin)

4. **Storage Efficiency:**
   - Eliminate redundant storage
   - Faster database queries (fewer tables)
   - Reduced backup size

5. **Enables Evidence Review:**
   - Clear which model to update (EnhancedEvidence)
   - processed_content is user-editable
   - accepted field tracks user acceptance

6. **Better API Design:**
   - EnhancedEvidence endpoints remain unchanged
   - No breaking changes for frontend
   - Clear data model for developers

### Negative

1. **Migration Effort:**
   - **Impact:** 8-12 hours to remove ExtractedContent references (32 files)
   - **Mitigation:**
     - Gradual cleanup (file by file)
     - Automated search/replace for imports
     - Test coverage ensures no regressions
     - Clear migration checklist

2. **Historical Data Loss (Theoretical):**
   - **Impact:** ExtractedContent records deleted (no history of intermediate extractions)
   - **Mitigation:**
     - User confirmed history not needed
     - ExtractedContent doesn't track history anyway (single version)
     - Backup database before migration (recovery option)
     - EnhancedEvidence has all necessary data

3. **Foreign Key Cleanup:**
   - **Impact:** GitHubRepositoryAnalysis.extracted_content field removed
   - **Mitigation:**
     - Field is SET_NULL (deletion safe)
     - Alternative access: analysis.evidence.enhanced_version
     - Migration adds helpful comment

4. **Test Updates:**
   - **Impact:** Update tests that create/query ExtractedContent
   - **Mitigation:**
     - Test coverage ensures correctness
     - Replace ExtractedContent factories with EnhancedEvidence
     - Automated test run after each change

### Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during migration | Low | High | Database backup, verification script, staged rollout |
| Broken foreign keys | Low | High | Cascade analysis, migration testing, null handling |
| Test failures | Medium | Medium | Run tests after each change, update factories incrementally |
| Orphaned ExtractedContent | Low | Low | Verification query, manual cleanup before migration |
| Performance regression | Very Low | Low | Same query patterns, fewer tables = faster queries |
| Rollback complexity | Low | Medium | Database backup, migration reversal script ready |

## Implementation Notes

### Phase 1: Verification & Backup (1 hour)

**Deliverables:**
```sql
-- Verification query: All ExtractedContent has matching EnhancedEvidence
SELECT ec.id, ec.source_type, ec.created_at
FROM extracted_content ec
LEFT JOIN enhanced_evidence ee ON ee.evidence_id = ec.preprocessing_job_id
WHERE ee.id IS NULL;

-- Expected: 0 rows (all ExtractedContent has EnhancedEvidence)
```

**Backup:**
```bash
# Full database backup before migration
pg_dump cv_tailor > backup_pre_consolidation_$(date +%Y%m%d).sql
```

### Phase 2: Foreign Key Removal (2-3 hours)

**Migration:**
```python
# backend/llm_services/migrations/00XX_remove_extracted_content_fk.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('llm_services', '00XX_previous_migration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='githubrepositoryanalysis',
            name='extracted_content',
        ),
    ]
```

**Code Updates:**
```python
# backend/llm_services/services/core/github_repository_agent.py
# BEFORE:
extracted_content = ExtractedContent.objects.create(...)
analysis.extracted_content = extracted_content

# AFTER:
# Remove ExtractedContent creation
# Access via: analysis.evidence.enhanced_version
```

### Phase 3: Model Removal (2 hours)

**Migration:**
```python
# backend/llm_services/migrations/00XX_drop_extracted_content.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('llm_services', '00XX_remove_extracted_content_fk'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ExtractedContent',
        ),
    ]
```

**Code Changes:**
```python
# backend/llm_services/models.py
# DELETE: class ExtractedContent(models.Model): ...

# backend/llm_services/admin.py
# DELETE: from .models import ExtractedContent
# DELETE: @admin.register(ExtractedContent) class ExtractedContentAdmin...
```

### Phase 4: Code Cleanup (4-6 hours)

**Files to Update (32 files):**
```bash
# Remove ExtractedContent imports
grep -rl "from llm_services.models import.*ExtractedContent" backend/
grep -rl "ExtractedContent" backend/llm_services/tests/

# Update to EnhancedEvidence
find backend -name "*.py" -exec sed -i '' 's/ExtractedContent/EnhancedEvidence/g' {} \;
```

**Test Factory Updates:**
```python
# backend/llm_services/tests/factories.py
# REMOVE: class ExtractedContentFactory(factory.django.DjangoModelFactory): ...

# UPDATE tests to use EnhancedEvidenceFactory instead
```

### Phase 5: Verification (1 hour)

**Test Execution:**
```bash
# Run full test suite
docker-compose exec backend uv run python manage.py test --keepdb

# Check for ExtractedContent references (should be 0 in code)
grep -r "ExtractedContent" backend/ --exclude-dir=migrations
```

**Success Criteria:**
- ✅ All tests passing
- ✅ No ExtractedContent references in code (except migrations)
- ✅ API endpoints return EnhancedEvidence correctly
- ✅ Database schema has no extracted_content table
- ✅ No broken foreign keys

### Rollback Plan

**If migration fails:**

```bash
# 1. Restore database from backup
psql cv_tailor < backup_pre_consolidation_YYYYMMDD.sql

# 2. Revert migrations
docker-compose exec backend uv run python manage.py migrate llm_services 00XX_before_consolidation

# 3. Restore ExtractedContent model from git
git checkout HEAD~1 -- backend/llm_services/models.py

# 4. Re-run migrations
docker-compose exec backend uv run python manage.py migrate
```

## References

- **PRD:** `docs/prds/prd.md` (v1.5.0) - Evidence Review & Acceptance workflow
- **DISCOVERY:** `docs/discovery/disco-001-evidence-review-workflow.md` - Redundancy analysis
- **TECH SPECS:**
  - `docs/specs/spec-llm.md` (v4.3.0) - Evidence processing architecture
- **FEATURE:** `docs/features/ft-045-evidence-review-workflow.md` - Implementation plan (Stage E)
- **Related ADRs:**
  - ADR-046: Blocking Evidence Review Workflow (depends on single source of truth)
  - ADR-048: LLM Re-unification Strategy (uses EnhancedEvidence.processed_content)
  - ADR-015: Multi-Source Artifact Preprocessing (original ExtractedContent rationale)

## Related Decisions

- **Future ADR:** If history tracking becomes necessary, implement audit log pattern (not dual models)

## Notes

- This ADR will transition from "Draft" to "Accepted" upon successful implementation and deployment
- Git tag: `adr-047-enhanced-evidence-consolidation` after acceptance
- User confirmed: "Not necessary to keep the history of extraction"
- ExtractedContent currently has 178 references across 32 files (will be reduced to 0 in code, kept in migrations only)
- Migration is safe: All ExtractedContent data is redundant (already in EnhancedEvidence)
- Single source of truth enables evidence review workflow (ft-045)
