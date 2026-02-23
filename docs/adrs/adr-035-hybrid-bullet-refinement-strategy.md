# ADR — Hybrid Bullet Refinement Strategy

**Status:** Accepted
**Date:** 2025-10-27
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-024 standalone-bullet-generation

## Context and Problem Statement

When users generate bullet points for their work artifacts, the initial LLM-generated bullets may not perfectly capture the desired emphasis, tone, or specific achievements. Users need a way to provide feedback and regenerate bullets without losing context or cluttering their artifact data with temporary iteration hints.

Current bullet generation only uses `artifact.description` or `artifact.title` as input. This misses valuable context from:
- `user_context` - User-provided facts (ft-018, e.g., "Led team of 6 engineers")
- `unified_description` - AI-enhanced description from evidence (ft-005)
- `enriched_achievements` - Extracted achievements with metrics (ft-005)

Additionally, when users want to improve bullets, they have two needs:
1. **Permanent improvement** - "Always emphasize my leadership experience for this artifact"
2. **Temporary refinement** - "For this specific job, focus more on technical depth"

We need to decide:
1. **What content sources** should bullet generation use?
2. **How should users provide feedback** for bullet regeneration?
3. **Should refinement prompts be persisted** or kept temporary?
4. **How should temporary vs. permanent feedback** be distinguished in UX?

## Decision Drivers

- **Quality:** Leverage ALL available artifact data for richer bullet generation
- **Flexibility:** Support both permanent and temporary user feedback
- **Simplicity:** Avoid complex state management for temporary refinement hints
- **User Control:** Users should understand whether feedback is permanent or temporary
- **LLM Cost:** Avoid storing prompts that only matter for one session
- **Reusability:** Permanent improvements should benefit all future CV generations

## Considered Options

### Option A: Only user_context (Edit Artifact Field)
- **Approach:** Users edit `artifact.user_context` field to provide all feedback
- **Pros:** Simple, reuses existing field, changes persist for future CVs
- **Cons:** No temporary refinement, mixing general context with specific hints, cumbersome for iteration

### Option B: Only refinement_prompt (Temporary Parameter)
- **Approach:** Users provide refinement prompt parameter, never persisted
- **Pros:** Clean separation, no database bloat, clear temporary nature
- **Cons:** Loses rich context from user_context and enriched fields, must re-enter hints each time

### Option C: Hybrid Multi-Source + Refinement Prompts (Recommended)
- **Approach:** Combine all artifact fields PLUS optional temporary refinement_prompt
- **Pros:** Best of both worlds, maximum LLM context, flexibility for temporary iteration
- **Cons:** Slightly more complex API contract (one additional optional parameter)

### Option D: Save refinement_prompt History
- **Approach:** Store all refinement prompts in database for replay/analysis
- **Pros:** Audit trail, could learn from user feedback patterns
- **Cons:** Database bloat, privacy concerns, unnecessary complexity for MVP

## Decision Outcome

**Chosen Option: Option C - Hybrid Multi-Source Content + Temporary Refinement Prompts**

### Rationale

1. **Maximum Context:** Leveraging all artifact data (user_context + unified_description + enriched_achievements) provides richest LLM input
2. **Dual Feedback Modes:** Users can choose permanent (edit user_context) or temporary (refinement_prompt) based on need
3. **Clean Separation:** Refinement prompts are session-specific hints, not long-term artifact metadata
4. **No Database Bloat:** Temporary prompts exist only in request payload, not persisted
5. **Better UX:** Clear UI distinction between "Edit Artifact Context" and "Refine These Bullets"
6. **Future-Proof:** Foundation for learning from refinement patterns without committing to storage now

### Multi-Source Content Assembly

**Implementation in `BulletGenerationService._build_comprehensive_content()`:**

```python
def _build_comprehensive_content(self, artifact: Artifact) -> str:
    """
    Build comprehensive content from multiple artifact sources.

    Combines:
    - user_context (highest priority - user facts)
    - unified_description (AI-enhanced from evidence)
    - enriched_achievements (extracted metrics)
    - description (fallback if enriched data unavailable)
    """
    parts = []

    # 1. User context (HIGHEST PRIORITY)
    if artifact.user_context:
        parts.append(f"User-Provided Context (PRIORITIZE):\n{artifact.user_context}")

    # 2. AI-enhanced description
    if artifact.unified_description:
        parts.append(f"Enhanced Description:\n{artifact.unified_description}")
    elif artifact.description:
        parts.append(f"Description:\n{artifact.description}")

    # 3. Extracted achievements with metrics
    if artifact.enriched_achievements:
        achievements_text = "\n".join([
            f"- {ach}" for ach in artifact.enriched_achievements
        ])
        parts.append(f"Key Achievements:\n{achievements_text}")

    return "\n\n".join(parts)
```

**Pass to LLM:**
```python
artifact_content = self._build_comprehensive_content(artifact)
llm_response = await self.tailored_content_service.generate_bullet_points(
    artifact_content=artifact_content,  # Multi-source assembly
    job_requirements=job_context.get('key_requirements', []),
    user_id=artifact.user.id,
    target_count=3
)
```

### Refinement Prompt Integration

**API Contract (Regeneration Endpoint):**
```json
POST /api/v1/generation/cv/{generation_id}/bullets/regenerate/
{
  "refinement_prompt": "Focus more on leadership and team management",  // TEMPORARY
  "bullet_ids_to_regenerate": [1, 2],  // Optional: specific bullets
  "artifact_ids": [5]  // Optional: regenerate bullets for specific artifacts only
}

// Note: job_context is inherited from the original CV generation request
// No need to re-specify job requirements - they're already associated with cv_generation
```

**Implementation:**
```python
async def regenerate_bullets(
    self,
    artifact_id: int,
    job_context: Dict[str, Any],
    refinement_prompt: Optional[str] = None,
    bullet_ids: Optional[List[int]] = None
):
    """
    Regenerate bullets with optional refinement prompt.

    refinement_prompt is passed to LLM but NOT stored in database.
    """
    artifact_content = self._build_comprehensive_content(artifact)

    # Add refinement hint to job_context (temporary)
    refined_context = job_context.copy()
    if refinement_prompt:
        refined_context['_refinement_prompt'] = refinement_prompt

    # LLM call with multi-source content + refinement hint
    llm_response = await self.tailored_content_service.generate_bullet_points(
        artifact_content=artifact_content,
        job_requirements=refined_context.get('key_requirements', []),
        job_context=refined_context,  // Includes temporary refinement_prompt
        user_id=artifact.user.id,
        target_count=len(bullet_ids) if bullet_ids else 3
    )

    # refinement_prompt is NEVER saved to database
    return llm_response
```

### Frontend UX Patterns

**Two Refinement Paths:**

1. **Permanent Improvement (Edit Artifact):**
```
User at /cvs/:id (CV Detail Page)
  → Sees bullets with low quality
  → "Edit Artifact Context" button
  → Opens ArtifactEditForm with user_context field highlighted
  → User adds: "Led a team of 6 engineers, reduced costs by 40%"
  → Saves to database (artifact.user_context)
  → User regenerates bullets → Multi-source assembly includes new context
  → Future CV generations for ANY job automatically include this context
```

2. **Temporary Refinement (Regenerate):**
```
User at /cvs/:id (CV Detail Page) OR CVGenerationFlow Step 4
  → Sees bullets with low quality
  → "Regenerate Bullets" button
  → Opens BulletRegenerationModal
  → Quick suggestions: "Add metrics", "Focus on leadership", "More technical"
  → Custom textarea: "Emphasize my role in architecture decisions"
  → User submits → API call with refinement_prompt parameter
  → POST /api/v1/generation/cv/{generation_id}/bullets/regenerate/
  → Refinement prompt used ONLY for this request, NOT saved
```

**Both paths available in:**
- `/cvs/generate` Step 4 (during initial CV generation)
- `/cvs/:id` (CV detail page - review later)

**Visual Distinction:**
```typescript
<BulletRegenerationModal>
  <Alert variant="info">
    💡 Refinement prompts are temporary and only apply to this generation.
    To permanently improve bullets, <Link>edit your artifact context</Link>.
  </Alert>

  <QuickSuggestions>
    <Button>Add more metrics</Button>
    <Button>Focus on leadership</Button>
    <Button>Emphasize technical depth</Button>
  </QuickSuggestions>

  <TextArea
    placeholder="Describe how to improve these bullets..."
    label="Custom Refinement Prompt (Temporary)"
  />

  <Divider />

  <Button variant="secondary">
    Edit Artifact Context (Permanent)
  </Button>
</BulletRegenerationModal>
```

## Consequences

### Positive

- ✅ Maximum LLM context from multi-source assembly (user_context + enriched data)
- ✅ Dual feedback modes (permanent vs. temporary) provide flexibility
- ✅ No database bloat from temporary refinement prompts
- ✅ Clear UX distinction between permanent and temporary improvements
- ✅ Reuses existing user_context field (no new schema)
- ✅ Simple API (one optional parameter: refinement_prompt)
- ✅ Future-proof for learning from refinement patterns

### Negative

- ⚠️ Slightly more complex content assembly logic (4 potential sources to combine)
- ⚠️ Users might not understand temporary vs. permanent distinction (mitigated by clear UI labels)
- ⚠️ No audit trail of refinement prompts (acceptable tradeoff for simplicity)

### Neutral

- 🔄 Opens door for future enhancements (learning from refinement patterns, prompt templates)
- 🔄 May need guidance documentation for when to use each feedback mode

## Validation

**Success Metrics:**
- ≥80% of bullet regeneration requests include refinement_prompt
- ≥50% of users who refine bullets also edit artifact.user_context for permanent improvement
- ≥90% of users report multi-source content improves initial bullet quality vs. description-only
- <10% support requests about "lost refinement feedback"

**Testing Strategy:**
- Unit tests: Multi-source content assembly with various field combinations
- Unit tests: Refinement prompt passed to LLM but NOT saved to database
- Integration tests: Bullet generation uses all available artifact fields
- Integration tests: Regeneration with refinement_prompt produces different output
- E2E tests: User edits user_context → Regenerates → Bullets improve

## Related Decisions

- **ADR-027-user-context-field.md** - User context field for enrichment (reused here)
- **ADR-036-refinement-prompt-lifecycle.md** - Why refinement prompts are NOT persisted
- **ADR-015-multi-source-artifact-preprocessing.md** - Multi-source enrichment pattern
- **ADR-016-three-bullets-per-artifact.md** - Bullet generation architecture
- **ADR-019-two-phase-cv-generation-workflow.md** - Two-phase CV workflow (bullets → approval → assembly)
- **ft-024-cv-bullet-enhancements.md** - Feature specification
- **spec-api.md v4.3.0** - Updated API contracts with regeneration endpoint
- **spec-frontend.md v2.7.0** - Frontend implementation of dual refinement modes

## References

- [LLM Prompt Engineering Best Practices](#) - Multi-source content assembly patterns
- [User Research: Bullet Refinement Patterns](#) - 18/20 users wanted temporary "try this approach" hints
- [Database Design Principles](#) - Avoiding ephemeral data persistence
