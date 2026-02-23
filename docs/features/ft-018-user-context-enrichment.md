# Feature — 018 User Context for Artifact Enrichment

**File:** docs/features/ft-018-user-context-enrichment.md
**Owner:** Backend/Frontend Team
**TECH-SPECs:** `spec-artifact-upload-enrichment-flow.md` (v1.4), `spec-api.md` (v4.1), `spec-frontend.md` (v2.2)
**Related ADRs:** [ADR-027-user-context-field](../adrs/adr-027-user-context-field.md)

## Existing Implementation Analysis

**Similar Features:**
- `artifacts/models.py` - Artifact model with enriched fields (description, unified_description)
- `llm_services/services/core/artifact_enrichment_service.py` - Enrichment orchestration with LLM unification
- `artifacts/serializers.py` - Artifact serializers for API contracts
- `frontend/src/components/ArtifactUpload.tsx` - Artifact creation form
- `frontend/src/components/ArtifactEditForm.tsx` - Artifact editing form

**Reusable Components:**
- `ArtifactEnrichmentService.unify_content_with_llm()` - LLM prompt construction for unified description
- `ArtifactSerializer` - Existing serializer to extend with user_context field
- `ArtifactUpload.tsx` - Form component to add user_context textarea
- `ArtifactDetailPage.tsx` - Detail view to display user_context

**Patterns to Follow:**
- TextField for flexible natural language input (vs. JSONField)
- Immutable field pattern: Never overwrite user_context during enrichment
- LLM prioritization: Prepend user_context to prompt with "PRIORITIZE" instruction
- Form validation: Optional field, 1000 character limit

**Code Already Implemented:**
- ✅ Enrichment service with LLM unification (`unify_content_with_llm()`)
- ✅ Artifact model with enriched fields
- ✅ Artifact serializers for API CRUD
- ✅ Frontend forms for artifact creation/editing

**Dependencies:**
- `artifacts.models.Artifact` (model to extend)
- `artifacts.serializers.ArtifactCreateSerializer` (serializer to extend)
- `llm_services.services.core.ArtifactEnrichmentService` (service to enhance)
- `artifacts.tasks.enrich_artifact` (task to pass user_context)

## Architecture Conformance

**Layer Assignment:**
- Model changes in `artifacts/models.py` (data layer)
- Serializer changes in `artifacts/serializers.py` (API layer)
- Service changes in `llm_services/services/core/artifact_enrichment_service.py` (business logic layer)
- Task changes in `artifacts/tasks.py` (async processing layer)
- Frontend changes in `src/components/` (UI layer)

**Pattern Compliance:**
- ✅ Follows service layer pattern (llm_services architecture)
- ✅ Uses LLM prompt engineering for prioritization
- ✅ Maintains immutability through field separation
- ✅ Backward compatible (nullable field, optional in API)

**Database Impact:**
- Add `user_context` TEXT field to `artifacts` table
- Migration is non-breaking (nullable, default='')
- No indexes required (not queried, only read/written with artifact)

**Test Coverage Target:**
- ≥85% coverage for new/modified code
- Unit tests for serializers, model, validation
- Integration tests for enrichment flow with user_context
- E2E tests for full artifact creation → enrichment flow

## Acceptance Criteria

- ✅ User can enter optional context during artifact creation
- ✅ Context field has helpful examples and placeholder text
- ✅ Context is limited to 1000 characters with live counter
- ✅ Context field has distinct visual styling (blue border + preservation icon)
- ✅ Context is passed to LLM during enrichment with prioritization
- ✅ Context is NEVER overwritten during re-enrichment
- ✅ User can edit context after artifact creation
- ✅ Unified description incorporates user context facts
- ✅ Empty context doesn't break enrichment (backward compatible)
- ✅ API accepts and returns user_context in artifact endpoints
- ✅ Frontend displays user_context in artifact detail view with "User-Provided" badge
- ✅ Test coverage ≥85% for all new/modified code

## Design Changes

### Database Schema

**New field in Artifact model:**
```python
# backend/artifacts/models.py
class Artifact(models.Model):
    # ... existing fields ...

    # NEW (v1.4.0): User-provided context for enrichment
    user_context = models.TextField(
        blank=True,
        help_text='User-provided context (immutable, preserved during enrichment)'
    )

    # Enriched fields (overwritten on re-enrichment)
    unified_description = models.TextField(blank=True)
    enriched_technologies = models.JSONField(default=list)
    enriched_achievements = models.JSONField(default=list)
    # ... rest of model ...
```

**Migration:**
```python
# Generated migration
class Migration(migrations.Migration):
    dependencies = [
        ('artifacts', '0XXX_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='user_context',
            field=models.TextField(blank=True, default='', help_text='User-provided context (immutable, preserved during enrichment)'),
        ),
    ]
```

### API Contracts

**POST /api/v1/artifacts/ (Create):**
```json
Request:
{
  "title": "E-commerce Platform",
  "description": "Built a full-stack e-commerce platform",
  "user_context": "Led a team of 6 engineers. Reduced costs by 40%. Managed $500K budget.",
  "evidence_links": [...]
}

Response: 201 Created
{
  "id": 123,
  "user_context": "Led a team of 6 engineers. Reduced costs by 40%. Managed $500K budget.",
  "unified_description": null,  // Not yet enriched
  // ... other fields ...
}
```

**GET /api/v1/artifacts/{id}/ (Retrieve):**
```json
Response: 200 OK
{
  "id": 123,
  "user_context": "Led a team of 6 engineers. Reduced costs by 40%. Managed $500K budget.",
  "unified_description": "...LLM-generated description incorporating user context...",
  // ... other fields ...
}
```

**PUT/PATCH /api/v1/artifacts/{id}/ (Update):**
```json
Request:
{
  "user_context": "Updated: Led a team of 8 engineers. Reduced costs by 45%."
}

Response: 200 OK
{
  "id": 123,
  "user_context": "Updated: Led a team of 8 engineers. Reduced costs by 45%.",
  // ... other fields ...
}
```

### Enrichment Service Changes

**Update `unify_content_with_llm()` signature:**
```python
# llm_services/services/core/artifact_enrichment_service.py

async def unify_content_with_llm(self,
                                extracted_contents: List[ExtractedContent],
                                artifact_title: str,
                                artifact_description: str,
                                user_context: str = "",  # NEW parameter
                                user_id: Optional[int] = None) -> str:
    """
    Generate unified description from all extracted content using LLM.

    Args:
        extracted_contents: Content extracted from evidence sources
        artifact_title: Title of artifact
        artifact_description: Brief description from user
        user_context: User-provided context (NEW - prioritized in prompt)
        user_id: User ID for tracking

    Returns:
        Unified description incorporating user context and evidence
    """
    # Build unified prompt with user context prioritization
    source_summaries = []
    for ec in extracted_contents:
        if ec.success:
            # ... existing logic ...
            source_summaries.append(summary)

    # NEW: Prepend user context with prioritization instruction
    user_context_section = ""
    if user_context and user_context.strip():
        user_context_section = f"""User-Provided Context (PRIORITIZE THESE FACTS):
{user_context}

"""

    unification_prompt = f"""{user_context_section}Artifact Title: {artifact_title}
Original Description: {artifact_description}

Content from {len(extracted_contents)} sources:

{chr(10).join(source_summaries)}

Generate a unified, coherent description (200-400 words) that:
1. MUST incorporate ALL user-provided context facts (if provided)
2. Combines insights from all evidence sources
3. Highlights key technologies and frameworks used
4. Emphasizes quantifiable achievements and impact
5. Maintains a professional tone
6. Is optimized for CV/resume use

Return ONLY the unified description, no preamble."""

    # Call LLM with updated prompt
    response = await self._execute_llm_task(...)

    return response.get('content', '').strip()
```

**Update task layer to pass user_context:**
```python
# artifacts/tasks.py

@shared_task
def enrich_artifact(artifact_id: int, user_id: int, processing_job_id: Optional[int] = None):
    """Enrich artifact with multi-source content extraction and LLM synthesis"""

    # Load artifact
    artifact = Artifact.objects.get(id=artifact_id)

    # Run enrichment service
    result = await enrichment_service.preprocess_multi_source_artifact(
        artifact_id=artifact_id,
        job_id=processing_job_id,
        user_id=user_id
    )

    # In preprocess_multi_source_artifact, pass user_context to unification:
    unified_description = await self.unify_content_with_llm(
        extracted_contents=successful_extractions,
        artifact_title=artifact.title,
        artifact_description=artifact.description,
        user_context=artifact.user_context,  # NEW: Pass user context
        user_id=user_id
    )

    # Save enriched fields (user_context NEVER overwritten)
    artifact.unified_description = unified_description
    artifact.enriched_technologies = technologies
    artifact.enriched_achievements = achievements
    # artifact.user_context - UNCHANGED (immutable)
    artifact.save()
```

### Frontend Changes

**ArtifactUpload.tsx (Creation Form):**
```typescript
import React, { useState } from 'react';

interface ArtifactFormData {
  title: string;
  description: string;
  user_context?: string;  // NEW
  // ... other fields
}

export const ArtifactUpload: React.FC = () => {
  const [formData, setFormData] = useState<ArtifactFormData>({
    title: '',
    description: '',
    user_context: '',  // NEW
  });

  const [contextLength, setContextLength] = useState(0);

  const handleContextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setContextLength(value.length);
    setFormData({ ...formData, user_context: value });
  };

  return (
    <form>
      <div>
        <label>Title</label>
        <input name="title" />
      </div>

      <div>
        <label>Description</label>
        <textarea name="description" rows={3} />
      </div>

      {/* NEW: User Context Field */}
      <div className="form-section">
        <label htmlFor="user_context" className="block text-sm font-medium text-gray-700">
          Additional Context (Optional)
        </label>
        <p className="text-xs text-gray-500 mt-1 mb-2">
          💡 Provide details that can't be extracted from evidence. This information will be preserved and used during enrichment.
        </p>

        <textarea
          id="user_context"
          name="user_context"
          value={formData.user_context}
          onChange={handleContextChange}
          className="w-full border-2 border-blue-300 rounded-md p-3 focus:ring-blue-500 focus:border-blue-500"
          placeholder="e.g., Led a team of 6 engineers, Reduced infrastructure costs by 40%, Presented at conference with 500+ attendees"
          rows={4}
          maxLength={1000}
        />

        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-400 flex items-center gap-1">
            🔒 Preserved during enrichment
          </span>
          <span className="text-xs text-gray-500">
            {contextLength}/1000 characters
          </span>
        </div>

        <details className="mt-2">
          <summary className="text-xs text-blue-600 cursor-pointer hover:underline">
            See more examples
          </summary>
          <ul className="text-xs text-gray-600 mt-2 ml-4 list-disc space-y-1">
            <li>Led a team of 6 engineers over 18 months</li>
            <li>Reduced infrastructure costs by 40% ($50K annually)</li>
            <li>Presented at conference with 500+ attendees</li>
            <li>Managed $2M project budget</li>
            <li>Mentored 3 junior developers</li>
          </ul>
        </details>
      </div>

      {/* Evidence links, etc. */}
    </form>
  );
};
```

**ArtifactEditForm.tsx (Edit Form):**
```typescript
// Similar to ArtifactUpload.tsx but for editing existing artifacts
// Includes pre-filled user_context value from artifact data
```

**ArtifactDetailPage.tsx (Display):**
```typescript
export const ArtifactDetailPage: React.FC = () => {
  const { artifact } = useArtifact(artifactId);

  return (
    <div>
      {/* ... other artifact details ... */}

      {/* NEW: Display user context if present */}
      {artifact.user_context && (
        <div className="mt-4 p-4 bg-blue-50 border-l-4 border-blue-500 rounded">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-blue-700 uppercase tracking-wide">
              👤 User-Provided Context
            </span>
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
              Preserved
            </span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {artifact.user_context}
          </p>
        </div>
      )}

      {/* Unified description (LLM-generated) */}
      <div className="mt-4">
        <h3>Unified Description</h3>
        <p>{artifact.unified_description}</p>
      </div>
    </div>
  );
};
```

### Type Definitions

**frontend/src/types/artifact.ts:**
```typescript
export interface Artifact {
  id: number;
  title: string;
  description: string;
  user_context?: string;  // NEW (optional)
  artifact_type: 'project' | 'publication' | 'presentation' | 'certification' | 'experience' | 'education';
  start_date: string;
  end_date?: string;
  technologies: string[];
  collaborators: string[];
  evidence_links: Evidence[];
  unified_description: string;
  enriched_technologies: string[];
  enriched_achievements: string[];
  processing_confidence: number;
  created_at: string;
  updated_at: string;
}

export interface ArtifactCreate {
  title: string;
  description: string;
  user_context?: string;  // NEW (optional)
  artifact_type?: string;
  start_date?: string;
  end_date?: string;
  technologies?: string[];
  collaborators?: string[];
  evidence_links?: EvidenceCreate[];
}
```

## Testing Strategy

### Unit Tests (Backend)

**test_models.py:**
```python
def test_artifact_user_context_optional():
    """user_context field is optional (blank=True)"""
    artifact = Artifact.objects.create(
        user=user,
        title="Test",
        description="Test description"
        # user_context NOT provided
    )
    assert artifact.user_context == ""

def test_artifact_user_context_stored():
    """user_context is stored correctly"""
    artifact = Artifact.objects.create(
        user=user,
        title="Test",
        description="Test description",
        user_context="Led a team of 6 engineers"
    )
    assert artifact.user_context == "Led a team of 6 engineers"
```

**test_serializers.py:**
```python
def test_artifact_create_serializer_with_user_context():
    """ArtifactCreateSerializer accepts user_context"""
    data = {
        "title": "Test",
        "description": "Test description",
        "user_context": "Led a team of 6 engineers",
    }
    serializer = ArtifactCreateSerializer(data=data)
    assert serializer.is_valid()
    artifact = serializer.save(user=user)
    assert artifact.user_context == "Led a team of 6 engineers"

def test_artifact_serializer_includes_user_context():
    """ArtifactSerializer includes user_context in response"""
    artifact = Artifact.objects.create(
        user=user,
        title="Test",
        description="Test description",
        user_context="Led a team of 6 engineers"
    )
    serializer = ArtifactSerializer(artifact)
    assert "user_context" in serializer.data
    assert serializer.data["user_context"] == "Led a team of 6 engineers"
```

**test_enrichment_service.py:**
```python
async def test_unify_content_with_llm_includes_user_context():
    """Enrichment service includes user_context in LLM prompt"""
    service = ArtifactEnrichmentService()

    user_context = "Led a team of 6 engineers. Reduced costs by 40%."

    # Mock LLM call to capture prompt
    with patch.object(service, '_execute_llm_task') as mock_llm:
        mock_llm.return_value = {'content': 'Unified description'}

        result = await service.unify_content_with_llm(
            extracted_contents=[],
            artifact_title="Test Project",
            artifact_description="Test description",
            user_context=user_context,
            user_id=1
        )

        # Verify prompt includes user context with prioritization
        call_args = mock_llm.call_args
        prompt = call_args[1]['context']['messages'][1]['content']
        assert "User-Provided Context (PRIORITIZE THESE FACTS):" in prompt
        assert user_context in prompt

async def test_enrichment_preserves_user_context():
    """Re-enrichment never overwrites user_context field"""
    artifact = await Artifact.objects.acreate(
        user=user,
        title="Test",
        description="Test description",
        user_context="Led a team of 6 engineers"
    )

    # Run enrichment
    result = await enrichment_service.preprocess_multi_source_artifact(
        artifact_id=artifact.id,
        job_id=1,
        user_id=user.id
    )

    # Reload artifact
    artifact.refresh_from_db()

    # Verify user_context unchanged
    assert artifact.user_context == "Led a team of 6 engineers"
    # Verify unified_description was generated
    assert artifact.unified_description != ""
```

### Integration Tests

**test_enrichment_integration.py:**
```python
@pytest.mark.asyncio
async def test_artifact_enrichment_with_user_context_end_to_end():
    """Full enrichment flow incorporates user context into unified description"""

    # Create artifact with user context
    artifact = await Artifact.objects.acreate(
        user=user,
        title="E-commerce Platform",
        description="Built a full-stack platform",
        user_context="Led a team of 6 engineers. Reduced infrastructure costs by 40%."
    )

    # Add evidence
    await Evidence.objects.acreate(
        artifact=artifact,
        url="https://github.com/user/project",
        evidence_type="github"
    )

    # Run enrichment
    result = await enrichment_service.preprocess_multi_source_artifact(
        artifact_id=artifact.id,
        job_id=1,
        user_id=user.id
    )

    # Verify user context preserved
    artifact.refresh_from_db()
    assert artifact.user_context == "Led a team of 6 engineers. Reduced infrastructure costs by 40%."

    # Verify unified description contains user context facts
    assert "6 engineers" in artifact.unified_description.lower() or "team" in artifact.unified_description.lower()
    assert "40%" in artifact.unified_description or "costs" in artifact.unified_description.lower()
```

### Frontend Tests

**ArtifactUpload.test.tsx:**
```typescript
describe('ArtifactUpload', () => {
  it('renders user context field', () => {
    render(<ArtifactUpload />);
    expect(screen.getByLabelText(/Additional Context/i)).toBeInTheDocument();
  });

  it('shows character counter', () => {
    render(<ArtifactUpload />);
    const textarea = screen.getByLabelText(/Additional Context/i);
    fireEvent.change(textarea, { target: { value: 'Test context' } });
    expect(screen.getByText(/12\/1000 characters/i)).toBeInTheDocument();
  });

  it('enforces 1000 character limit', () => {
    render(<ArtifactUpload />);
    const textarea = screen.getByLabelText(/Additional Context/i) as HTMLTextAreaElement;
    expect(textarea.maxLength).toBe(1000);
  });

  it('includes user_context in form submission', async () => {
    const mockSubmit = jest.fn();
    render(<ArtifactUpload onSubmit={mockSubmit} />);

    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: 'Test desc' } });
    fireEvent.change(screen.getByLabelText(/Additional Context/i), {
      target: { value: 'Led a team of 6' }
    });

    fireEvent.click(screen.getByText(/Submit/i));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Test',
          description: 'Test desc',
          user_context: 'Led a team of 6'
        })
      );
    });
  });
});
```

## Success Metrics

**Adoption Metrics:**
- ≥30% of artifact creations include user_context within 30 days of launch
- ≥50% of users who add user_context report improved unified_description quality
- <5% support tickets related to "lost context" after re-enrichment

**Quality Metrics:**
- ≥90% of unified_descriptions incorporate user_context facts when provided
- ≥85% user satisfaction with context-enhanced descriptions (survey)
- 0% re-enrichment operations overwrite user_context (tested automatically)

**Technical Metrics:**
- Test coverage ≥85% for new/modified code
- API response time <100ms additional overhead for user_context
- Zero production incidents related to user_context feature

## Rollout Plan

**Phase 1: Development & Testing (Week 1-2)**
- Implement backend changes (model, serializers, service, task)
- Write comprehensive unit and integration tests
- Implement frontend changes (forms, display)
- Conduct internal testing

**Phase 2: Beta Release (Week 3)**
- Deploy to staging environment
- Run QA testing with sample artifacts
- Gather feedback from internal team (5-10 users)
- Monitor for errors and edge cases

**Phase 3: Production Release (Week 4)**
- Deploy to production (database migration first, then code)
- Monitor adoption metrics and error rates
- Collect user feedback via in-app survey
- Iterate based on feedback

## Related Documentation

- [ADR-027-user-context-field](../adrs/adr-027-user-context-field.md) - Architecture decision
- [spec-artifact-upload-enrichment-flow.md v1.4.0](../specs/spec-artifact-upload-enrichment-flow.md) - Updated enrichment spec
- [spec-api.md v4.1.0](../specs/spec-api.md) - Updated API contracts
- [spec-frontend.md v2.2.0](../specs/spec-frontend.md) - Updated frontend components
