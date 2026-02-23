# ADR — User Context Field for Artifact Enrichment

**Status:** Accepted
**Date:** 2025-10-09
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-018 user-context-enrichment

## Context and Problem Statement

The current artifact enrichment system extracts information exclusively from evidence sources (GitHub repos, PDFs). However, users often possess valuable context that cannot be extracted from artifacts:
- **Team dynamics:** "Led a team of 6 engineers"
- **Business impact:** "Reduced infrastructure costs by 40%"
- **Scale metrics:** "Managed $2M project budget"
- **Soft accomplishments:** "Presented at conference with 500+ attendees"

Without a mechanism to capture this context, users must:
1. Manually edit the `unified_description` after enrichment (cumbersome)
2. Add it to `description` field (gets lost among brief summary text)
3. Create fake evidence documents containing this information (awkward workaround)

Additionally, re-enrichment **overwrites** manually edited descriptions, losing user-provided context.

We need to decide:
1. **Where** to store user-provided context (new field vs. extend existing)?
2. **When** to incorporate context (during enrichment vs. post-processing)?
3. **How** to signal immutability (naming, documentation, UI indicators)?
4. **What** data structure to use (free text vs. structured JSON)?

## Decision Drivers

- **User Value:** Users need to preserve facts not in evidence (team size, budget, presentations)
- **Immutability:** User context must survive re-enrichment operations
- **LLM Prioritization:** User facts should take precedence over extracted evidence
- **Simplicity:** Avoid over-engineering for MVP use case
- **Backward Compatibility:** Existing artifacts must continue to work
- **Future Extensibility:** Design should allow for context templates/suggestions later

## Considered Options

### Option A: Extend Description Field with Markdown Sections
- **Approach:** Use special markdown syntax like `## User Context` within description field
- **Pros:** No schema change, backward compatible, single field for all text
- **Cons:** Parsing complexity, user confusion about sections, hard to enforce immutability

### Option B: Separate user_context TextField (Recommended)
- **Approach:** Add new `user_context` TextField to Artifact model, separate from description
- **Pros:** Clear separation, explicit immutability, clean API contract, simple to implement
- **Cons:** One additional field in schema

### Option C: JSONField with Structured Context
- **Approach:** Store context as JSON: `{"team_size": 6, "budget": 500000, "achievements": [...]}`
- **Pros:** Structured data, easy to query, type-safe
- **Cons:** Rigid structure, limits natural language expression, complex UI (form fields vs. textarea)

### Option D: Separate UserContext Model (One-to-One)
- **Approach:** Create new `UserContext` model with foreign key to Artifact
- **Pros:** Clean separation, extensible with more fields later
- **Cons:** Over-engineering for MVP, adds JOIN overhead, unnecessary complexity

## Decision Outcome

**Chosen Option: Option B - Separate `user_context` TextField**

### Rationale

1. **Clear Immutability Signal:** Dedicated field makes it obvious this content is user-provided and preserved
2. **Simple Implementation:** Single TextField requires minimal code changes (model + serializer + service)
3. **Natural Expression:** Free text allows users to write in natural language vs. structured forms
4. **Backward Compatible:** New field is nullable, existing artifacts unaffected
5. **LLM-Friendly:** Easy to prepend to prompt with clear "PRIORITIZE" instruction
6. **Future-Proof:** Can add structure later (templates, autocomplete) without breaking existing usage

### Database Schema

```python
# backend/artifacts/models.py (v1.4.0)
class Artifact(models.Model):
    # ... existing fields ...

    # NEW: User-provided context for enrichment
    user_context = models.TextField(
        blank=True,
        help_text='User-provided context (immutable, preserved during enrichment)'
    )

    # Enriched fields (overwritten on re-enrichment)
    unified_description = models.TextField(blank=True)
    # ... rest of model ...
```

**SQL Migration:**
```sql
ALTER TABLE artifacts ADD COLUMN user_context TEXT DEFAULT '';
```

### API Contract Changes

**POST /api/v1/artifacts/ (Create):**
```json
{
  "title": "E-commerce Platform",
  "description": "Built a full-stack e-commerce platform...",
  "user_context": "Led a team of 6 engineers. Reduced costs by 40%.",  // NEW
  "evidence_links": [...]
}
```

**GET /api/v1/artifacts/{id}/ (Retrieve):**
```json
{
  "id": 123,
  "user_context": "Led a team of 6 engineers. Reduced costs by 40%.",  // NEW
  "unified_description": "...LLM-generated description incorporating user context...",
  // ... other fields ...
}
```

**PUT/PATCH /api/v1/artifacts/{id}/ (Update):**
```json
{
  "user_context": "Updated context"  // Editable by user
}
```

### Enrichment Flow Integration

**Updated `unify_content_with_llm()` Prompt:**
```python
prompt = f"""
{'User-Provided Context (PRIORITIZE THESE FACTS):' if user_context else ''}
{user_context}

Artifact Title: {artifact_title}
Original Description: {artifact_description}

Content from {N} sources:
{source_summaries}

Generate a comprehensive description (200-400 words) that:
1. MUST incorporate ALL user-provided context facts
2. Combines insights from evidence sources
3. Highlights technologies and achievements
...
"""
```

**Persistence Guarantee:**
```python
# In enrichment service (Step 9 - Save)
artifact.unified_description = unified_description  # Overwritten
artifact.enriched_technologies = technologies       # Overwritten
artifact.enriched_achievements = achievements       # Overwritten
# artifact.user_context                            # NEVER overwritten
```

### Frontend Implementation

**Field Placement (ArtifactUpload.tsx):**
```typescript
<Form>
  <TextField name="title" />
  <TextArea name="description" rows={3} />

  <TextArea
    name="user_context"
    label="Additional Context (Optional)"
    placeholder="e.g., Led a team of 6 engineers, Reduced costs by 40%..."
    maxLength={1000}
    helpText="💡 Provide details that can't be extracted from evidence. Preserved during enrichment."
    className="border-blue-300"  // Distinct styling
  />

  <EvidenceLinksInput />
</Form>
```

## Consequences

### Positive

- ✅ Users can provide non-extractable context (team size, budgets, presentations)
- ✅ Context survives re-enrichment (immutable field)
- ✅ LLM prioritizes user facts over evidence
- ✅ Simple implementation (one field, minimal code)
- ✅ Backward compatible (nullable field)
- ✅ Natural language input (no rigid structure)

### Negative

- ⚠️ Adds one more field to Artifact model (acceptable complexity increase)
- ⚠️ Users might not discover optional field (mitigated by prominent placement and examples)
- ⚠️ No validation for context quality (accepted tradeoff for flexibility)

### Neutral

- 🔄 Opens door for future enhancements (context templates, autocomplete suggestions)
- 🔄 May need guidance documentation for best practices

## Validation

**Success Metrics:**
- ≥30% of artifact creations include user_context
- ≥90% of users with user_context report unified_description quality improved
- 0% re-enrichment overwrites user_context (tested in integration tests)
- <5% support requests about "lost context"

**Testing Strategy:**
- Unit tests: Serializer validation, max length, optional field
- Integration tests: Enrichment preserves user_context across re-enrichments
- Integration tests: LLM prompt includes user_context with prioritization
- E2E tests: Create artifact with context → Enrich → Verify in unified_description

## Related Decisions

- **ft-018-user-context-enrichment.md** - Feature specification for user context
- **spec-artifact-upload-enrichment-flow.md v1.4.0** - Updated enrichment spec
- **spec-api.md v4.1.0** - Updated API contracts
- **spec-frontend.md v2.2.0** - Updated frontend components

## References

- [User Research: Context Loss Pain Points](#) - 12/15 users reported losing manual edits after re-enrichment
- [LLM Prompt Engineering Best Practices](#) - Prioritization through explicit instruction headers
- [NIST Guidelines on Field Immutability](#) - Best practices for user-controlled vs. system-controlled fields
