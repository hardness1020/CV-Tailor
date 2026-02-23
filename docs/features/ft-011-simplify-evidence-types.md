# Feature — 011 Simplify Evidence Types

**Feature ID:** ft-011
**Title:** Simplify Evidence Types to GitHub + PDF Only
**Status:** Documented (Stage E Complete)
**Priority:** P1 (Product Simplification)
**Owner:** Backend + Frontend Teams
**Target Date:** TBD
**Sprint:** TBD

## Overview

Simplify the artifact evidence system by reducing supported evidence types from 8 to 2: GitHub repositories (links) and PDF documents (uploads). This change streamlines the user experience, reduces processing complexity, and focuses on the most valuable proof sources for technical portfolios.

## Links
- **PRD**: [prd.md](../prds/prd.md)
- **SPEC (API)**: [spec-api.md](../specs/spec-api.md) - v4.0.0
- **SPEC (System)**: [spec-system.md](../specs/spec-system.md) - v1.1.0
- **SPEC (Frontend)**: [spec-frontend.md](../specs/spec-frontend.md) - v2.1.0
- **Related Features**: [ft-001-artifact-upload.md](ft-001-artifact-upload.md), [ft-005-multi-source-artifact-preprocessing.md](ft-005-multi-source-artifact-preprocessing.md)

## Codebase Discovery (Stage B)

### Current Evidence Types (8 total)
**Backend:** `backend/artifacts/models.py:86-99`
```python
EVIDENCE_TYPES = [
    ('github', 'GitHub Repository'),          # KEEP
    ('live_app', 'Live Application'),         # REMOVE
    ('document', 'Document/PDF'),             # KEEP
    ('video', 'Video File'),                  # REMOVE
    ('audio', 'Audio File'),                  # REMOVE
    ('website', 'Website'),                   # REMOVE
    ('portfolio', 'Portfolio'),               # REMOVE
    ('other', 'Other'),                       # REMOVE
]
```

### Affected Components

**Backend Files:**
- `backend/artifacts/models.py:86-99` - Evidence.EVIDENCE_TYPES enum
- `backend/artifacts/serializers.py` - Evidence validation logic
- `backend/artifacts/views.py:106,230` - Evidence creation endpoints
- `backend/artifacts/tasks.py:71` - GitHub-specific processing
- `backend/llm_services/services/core/document_loader_service.py` - LangChain document loaders

**Frontend Files:**
- `frontend/src/components/ArtifactUpload.tsx:35-78` - Evidence type UI (8 options → 2 options)
- `frontend/src/services/apiClient.ts` - API client evidence type definitions

**Test Files:**
- `backend/artifacts/tests/test_editing.py` - Evidence type validation tests
- `backend/artifacts/tests/test_enrichment.py` - Evidence processing tests
- `backend/artifacts/tests/test_api.py` - API endpoint tests

### Data Migration Requirements
**Existing Evidence Records:**
- Query existing evidence to identify deprecated types usage
- Strategy: Map deprecated types to closest equivalent or mark for user review
  - `live_app` → manual user review (convert to GitHub if code-based, or remove)
  - `video`, `audio` → manual user review (remove or convert to document if transcription exists)
  - `website`, `portfolio`, `other` → manual user review (convert to GitHub or remove)

## Acceptance Criteria

### Backend
- ✅ Evidence.EVIDENCE_TYPES contains only `github` and `document`
- ✅ API endpoints validate and reject deprecated evidence types
- ✅ Serializers validate only `github` and `document` types
- ✅ Database migration script handles existing deprecated evidence
- ✅ All tests updated to use only supported evidence types

### Frontend
- ✅ Artifact upload UI shows only 2 evidence type options
- ✅ Evidence type selector displays GitHub and Document options only
- ✅ Removed UI components for deprecated evidence types
- ✅ Form validation rejects deprecated evidence types
- ✅ TypeScript types updated to `'github' | 'document'`

### Data Migration
- ✅ Migration script identifies all existing evidence with deprecated types
- ✅ User notification system for affected artifacts
- ✅ Admin dashboard shows migration progress
- ✅ Rollback plan documented in OP-NOTE

## Design Changes

### Database Schema

**Evidence Model Update:**
```python
# backend/artifacts/models.py
class Evidence(models.Model):
    EVIDENCE_TYPES = [
        ('github', 'GitHub Repository'),
        ('document', 'Document/PDF'),
    ]

    evidence_type = models.CharField(
        max_length=20,
        choices=EVIDENCE_TYPES,
        help_text='Evidence type: github (repository) or document (PDF upload)'
    )
```

### API Endpoints

**Evidence Validation:**
```python
# backend/artifacts/serializers.py
class EvidenceLinkSerializer(serializers.ModelSerializer):
    evidence_type = serializers.ChoiceField(
        choices=['github', 'document'],
        help_text='Only github and document types are supported'
    )

    def validate_evidence_type(self, value):
        if value not in ['github', 'document']:
            raise serializers.ValidationError(
                f"Evidence type '{value}' is not supported. Use 'github' or 'document'."
            )
        return value
```

### Frontend UI Updates

**Simplified Evidence Type Selector:**
```typescript
// frontend/src/components/ArtifactUpload.tsx
const evidenceTypeOptions = [
  { value: 'github', label: 'GitHub Repository', icon: Github },
  { value: 'document', label: 'Document (PDF)', icon: FileText }
]

const evidenceTypeLabels = {
  github: 'GitHub Repository',
  document: 'Document/PDF',
}

// Remove deprecated types
// OLD: 8 options (github, live_app, paper, video, document, website, portfolio, other)
// NEW: 2 options (github, document)
```

### Data Migration Script

**Migration Plan:**
```python
# Migration: artifacts/migrations/0006_simplify_evidence_types.py
from django.db import migrations

def migrate_deprecated_evidence(apps, schema_editor):
    Evidence = apps.get_model('artifacts', 'Evidence')

    deprecated_types = ['live_app', 'video', 'audio', 'website', 'portfolio', 'other']
    deprecated_evidence = Evidence.objects.filter(evidence_type__in=deprecated_types)

    # Log deprecated evidence for manual review
    for evidence in deprecated_evidence:
        print(f"Review required: Artifact {evidence.artifact_id}, "
              f"Type: {evidence.evidence_type}, URL: {evidence.url}")

    # Option 1: Mark for manual review
    deprecated_evidence.update(
        is_accessible=False,
        validation_metadata={'migration_note': 'Deprecated type - requires user review'}
    )

    # Option 2: Auto-convert where possible (conservative approach)
    # Evidence.objects.filter(evidence_type='live_app', url__contains='github.com').update(evidence_type='github')

class Migration(migrations.Migration):
    dependencies = [
        ('artifacts', '0005_previous_migration'),
    ]

    operations = [
        migrations.RunPython(migrate_deprecated_evidence),
        migrations.AlterField(
            model_name='evidence',
            name='evidence_type',
            field=models.CharField(
                choices=[('github', 'GitHub Repository'), ('document', 'Document/PDF')],
                max_length=20
            ),
        ),
    ]
```

## Test & Eval Plan

### Unit Tests

**Backend Tests:**
```python
# backend/artifacts/tests/test_models.py
def test_evidence_type_validation():
    """Test that only github and document types are accepted"""
    # Valid types
    evidence = Evidence(evidence_type='github', url='https://github.com/user/repo')
    evidence.full_clean()  # Should pass

    evidence = Evidence(evidence_type='document', url='', file_path='/uploads/doc.pdf')
    evidence.full_clean()  # Should pass

    # Invalid types
    with pytest.raises(ValidationError):
        evidence = Evidence(evidence_type='live_app', url='https://example.com')
        evidence.full_clean()

# backend/artifacts/tests/test_api.py
def test_create_artifact_with_invalid_evidence_type():
    """Test API rejects deprecated evidence types"""
    response = client.post('/api/v1/artifacts/', {
        'title': 'Test',
        'description': 'Test artifact',
        'evidence_links': [
            {'url': 'https://example.com', 'evidence_type': 'live_app'}
        ]
    })
    assert response.status_code == 400
    assert 'evidence_type' in response.json()['errors']
```

**Frontend Tests:**
```typescript
// frontend/src/components/ArtifactUpload.test.tsx
describe('ArtifactUpload - Evidence Types', () => {
  it('shows only github and document options', () => {
    render(<ArtifactUpload />)

    const evidenceTypeSelect = screen.getByLabelText(/evidence type/i)
    const options = within(evidenceTypeSelect).getAllByRole('option')

    expect(options).toHaveLength(2)
    expect(options[0]).toHaveTextContent('GitHub Repository')
    expect(options[1]).toHaveTextContent('Document (PDF)')
  })

  it('rejects deprecated evidence types', async () => {
    const onSubmit = jest.fn()
    render(<ArtifactUpload onSubmit={onSubmit} />)

    // Try to submit with deprecated type (should be prevented by UI)
    const form = screen.getByRole('form')
    await userEvent.type(screen.getByLabelText(/url/i), 'https://example.com/video.mp4')

    // Deprecated types should not be selectable
    expect(screen.queryByText('Video File')).not.toBeInTheDocument()
  })
})
```

### Integration Tests

**Data Migration Testing:**
```python
# backend/artifacts/tests/test_migrations.py
def test_evidence_type_migration():
    """Test migration handles deprecated evidence types correctly"""
    # Create test data with deprecated types
    artifact = Artifact.objects.create(title='Test', description='Test')
    Evidence.objects.create(artifact=artifact, evidence_type='live_app', url='https://app.example.com')
    Evidence.objects.create(artifact=artifact, evidence_type='video', url='https://youtube.com/watch?v=123')

    # Run migration
    call_command('migrate', 'artifacts', '0006')

    # Verify deprecated evidence is marked for review
    deprecated = Evidence.objects.filter(is_accessible=False)
    assert deprecated.count() == 2
    for evidence in deprecated:
        assert 'Deprecated type' in evidence.validation_metadata.get('migration_note', '')
```

### Performance Tests
- Evidence validation performance with reduced type set
- Database query performance after migration
- Frontend rendering performance with simplified UI

## Telemetry & Metrics

### Migration Metrics
- **Deprecated Evidence Count**: Total number of evidence records with deprecated types
- **Migration Success Rate**: Percentage of evidence successfully migrated or marked for review
- **User Review Required**: Number of artifacts requiring manual user review

### Post-Migration Metrics
- **Evidence Creation Rate**: Track adoption of new simplified types
- **Validation Error Rate**: Monitor errors related to evidence type validation
- **User Confusion Events**: Track support tickets related to evidence types

## Edge Cases & Risks

### Data Migration Risks
**Risk:** Existing evidence with deprecated types may be critical for user artifacts
**Mitigation:**
- Conservative approach: Mark for manual review rather than auto-delete
- Email notification to affected users before migration
- Provide UI for users to review and update their evidence
- Document rollback procedure

**Risk:** Users may have workflows dependent on deprecated evidence types
**Mitigation:**
- Provide migration guide and communication timeline
- Offer grace period with deprecation warnings
- Support team training for handling migration questions

### Technical Risks
**Risk:** Migration script failures could corrupt evidence data
**Mitigation:**
- Test migration thoroughly in staging environment
- Database backup before migration
- Transaction-based migration with rollback capability
- Dry-run mode to preview changes

## Dependencies

### External
- No external dependencies

### Internal
- Database migration system (Django migrations)
- Frontend component library
- API serialization layer

## Rollout Strategy

### Phase 1: Deprecation Warning (Week 1-2)
- Add deprecation warnings to UI for deprecated evidence types
- Email notification to users with affected artifacts
- Documentation update with migration timeline

### Phase 2: Data Migration (Week 3)
- Run migration script in production
- Mark deprecated evidence for review
- Provide user dashboard for reviewing affected artifacts

### Phase 3: UI Update (Week 4)
- Deploy simplified UI with only 2 evidence types
- Remove deprecated type selectors
- Monitor error rates and user feedback

### Phase 4: Cleanup (Week 5+)
- Remove deprecated type handling code
- Archive migration scripts
- Post-mortem and lessons learned

## Open Questions

1. **Auto-conversion Strategy:** Should we attempt to auto-convert `live_app` URLs containing 'github.com' to `github` type, or require manual review for all?
2. **User Notification Timing:** How much advance notice should users receive before migration?
3. **Grace Period:** Should we keep deprecated types read-only for a grace period, or hard-remove immediately?
4. **Migration Support:** Do we need dedicated support resources during migration window?

## Status

**Current Stage:** E (Plan) - Documentation Complete
**Next Steps:** Await approval to proceed to Stage F (TDD implementation)
