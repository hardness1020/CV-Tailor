# ADR — Refinement Prompt Lifecycle (Do NOT Persist)

**Status:** Accepted
**Date:** 2025-10-27
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-024 standalone-bullet-generation

## Context and Problem Statement

When users regenerate bullet points with refinement prompts (e.g., "Add more metrics", "Focus on leadership"), we need to decide whether to persist these prompts to the database or treat them as ephemeral session-specific hints.

Refinement prompts are temporary feedback users provide during bullet iteration:
- "Emphasize technical depth over business impact"
- "Use more action verbs and reduce generic language"
- "Add specific metrics and quantifiable achievements"
- "Focus more on my role as team lead"

We need to decide:
1. **Should refinement prompts be saved** to the database?
2. **If saved, where should they be stored** (BulletGenerationJob, separate table, artifact field)?
3. **Should users be able to replay** previous refinement prompts?
4. **What is the lifecycle** of a refinement prompt (session, generation, artifact)?

## Decision Drivers

- **Simplicity:** Avoid unnecessary database complexity
- **Privacy:** Refinement prompts may contain sensitive iteration details
- **Session Context:** Prompts are specific to current job application, not universally applicable
- **Database Bloat:** Storing every refinement attempt creates large amount of ephemeral data
- **User Intent:** Users want temporary "try this" hints, not permanent artifact metadata
- **Future Learning:** May want to analyze refinement patterns later (but not in MVP)

## Considered Options

### Option A: Do NOT Persist Refinement Prompts (Recommended)
- **Approach:** Refinement prompt exists only in API request payload, never saved to database
- **Lifecycle:** Request-scoped only (exists for LLM call, then discarded)
- **Pros:** Simple, no DB bloat, clear temporary nature, privacy-friendly
- **Cons:** Cannot replay previous refinements, no audit trail for learning

### Option B: Save to BulletGenerationJob.refinement_prompts (JSONField)
- **Approach:** Store all refinement prompts in array on BulletGenerationJob model
- **Lifecycle:** Persisted per generation job, available for replay
- **Pros:** Can replay past refinements, audit trail for analytics
- **Cons:** Database bloat, unclear when to prune, privacy concerns

### Option C: Separate RefinementHistory Table
- **Approach:** Create new model: `RefinementHistory(artifact, prompt, timestamp, applied_to_bullets)`
- **Lifecycle:** Long-term storage with foreign key to artifact
- **Pros:** Clean data model, queryable for ML, complete audit trail
- **Cons:** Over-engineering for MVP, significant storage overhead, complex lifecycle management

### Option D: Session Storage Only (Frontend)
- **Approach:** Store refinement prompts in browser sessionStorage for current tab session
- **Lifecycle:** Available until user closes tab or navigates away
- **Pros:** No backend changes, user can see recent refinements in current session
- **Cons:** Lost on page refresh, inconsistent across tabs, limited value

## Decision Outcome

**Chosen Option: Option A - Do NOT Persist Refinement Prompts**

### Rationale

1. **Clear Intent:** Refinement prompts are *temporary hints* for current iteration, not permanent artifact metadata
2. **Simplicity:** No database schema changes, no lifecycle management complexity
3. **No Bloat:** Avoiding storage of potentially hundreds of iterative refinements per artifact
4. **Privacy-Friendly:** Users may experiment with phrasing without creating permanent records
5. **Session-Specific:** Prompts like "focus on leadership" may only apply to current job, not all future CVs
6. **Alternative Exists:** Users can make *permanent* improvements by editing `artifact.user_context` field

### Implementation

**API Contract (refinement_prompt is NOT saved):**
```python
@api_view(['POST'])
def regenerate_cv_bullets(request, generation_id):
    """
    Regenerate bullets for CV generation with optional refinement prompt.

    refinement_prompt is passed to LLM but NEVER saved to database.
    """
    generation = GeneratedDocument.objects.get(id=generation_id)
    refinement_prompt = request.data.get('refinement_prompt')  # Temporary only
    bullet_ids = request.data.get('bullet_ids_to_regenerate')  # Optional
    artifact_ids = request.data.get('artifact_ids')  # Optional

    # Pass refinement_prompt to LLM
    # job_context is inherited from generation.job_description_data
    result = await bullet_service.regenerate_bullets(
        generation_id=generation_id,
        refinement_prompt=refinement_prompt,  # Used in this request only
        bullet_ids=bullet_ids,
        artifact_ids=artifact_ids
    )

    # refinement_prompt is NOT saved anywhere
    # Only the generated bullets are saved (BulletPoint records)

    return Response(result)
```

**Service Layer (refinement_prompt lifecycle ends after LLM call):**
```python
async def regenerate_bullets(
    self,
    generation_id: str,
    refinement_prompt: Optional[str] = None,
    bullet_ids: Optional[List[int]] = None,
    artifact_ids: Optional[List[int]] = None
) -> GeneratedBulletSet:
    """
    Regenerate bullets for CV generation with optional refinement prompt.

    Args:
        generation_id: CV generation ID (contains job_context)
        refinement_prompt: Temporary hint for LLM (NOT persisted)
        bullet_ids: Specific bullets to regenerate (or all if None)
        artifact_ids: Specific artifacts to regenerate bullets for (or all if None)
    """
    generation = await self._get_generation(generation_id)
    job_context = generation.job_description_data  # Inherit from CV generation

    # Add refinement prompt to job_context (temporary)
    refined_context = job_context.copy()
    if refinement_prompt:
        refined_context['_refinement_prompt'] = refinement_prompt

    # Get artifacts to regenerate
    artifacts = self._get_artifacts_for_regeneration(generation, artifact_ids)

    # Regenerate bullets for each artifact
    for artifact in artifacts:
        artifact_content = self._build_comprehensive_content(artifact)

        # LLM call with refined context
        llm_response = await self.tailored_content_service.generate_bullet_points(
            artifact_content=artifact_content,
            job_context=refined_context  # Contains temporary refinement_prompt
        )

        # refinement_prompt ends here - NOT saved to database
        # Only save the generated bullets
        bullets = self._parse_and_save_bullets(llm_response, artifact, generation)

    return GeneratedBulletSet(bullets=bullets, ...)
```

**Frontend UI (Clear Messaging):**
```typescript
<BulletRegenerationModal>
  <Alert variant="info">
    💡 Refinement prompts are temporary and only apply to this generation.
    They are NOT saved to your artifact data.

    To make permanent improvements, <Link>edit your artifact context</Link>.
  </Alert>

  <TextArea
    name="refinement_prompt"
    label="How should we improve these bullets? (Temporary)"
    placeholder="e.g., Focus more on leadership and team management"
    helpText="This prompt will be used ONLY for this regeneration."
  />

  <Button type="submit">
    Regenerate with This Hint
  </Button>

  <Divider />

  <Button variant="secondary" onClick={openArtifactEdit}>
    Edit Artifact Context (Permanent)
  </Button>
</BulletRegenerationModal>
```

### Database Impact

**No Changes Required:**
- No new tables
- No new fields on existing models
- No migrations needed

**What IS Saved:**
```python
# Saved to database:
BulletPoint(
    artifact=artifact,
    text="Led team of 6 engineers to deploy...",  # Result of refinement
    user_edited=False,
    user_approved=False,
    # ... quality metrics ...
)

# NOT saved to database:
# - refinement_prompt parameter
# - Iteration history
# - Previous unsuccessful attempts
```

### Future Extensibility (Out of Scope for MVP)

**If we decide to learn from refinement patterns later, we can:**
1. Add optional anonymous analytics logging (separate from production database)
2. Implement client-side sessionStorage for "recent refinements" list
3. Build prompt suggestion system based on aggregated patterns
4. Create admin analytics dashboard without storing per-user prompts

**But for MVP:** Simple, clean, no persistence.

## Consequences

### Positive

- ✅ Zero database bloat from iterative refinement attempts
- ✅ Clear user expectation: refinement prompts are temporary
- ✅ Privacy-friendly: no permanent record of experimental phrasing
- ✅ Simple implementation: no new models, no lifecycle management
- ✅ Fast MVP delivery: no complex storage logic needed
- ✅ Alternative exists: users can use artifact.user_context for permanent improvements

### Negative

- ⚠️ Cannot replay previous refinement prompts if user wants same hint again
- ⚠️ No audit trail for understanding why bullets changed over iterations
- ⚠️ Cannot analyze refinement patterns for ML/improvement suggestions
- ⚠️ Users must re-type refinement prompts if they close the page

### Neutral

- 🔄 May add sessionStorage caching in future for UX (client-side only)
- 🔄 May add anonymous analytics logging later (separate from production DB)
- 🔄 Decision can be revisited post-MVP if user research shows strong need

## Mitigation Strategies

**For "Cannot Replay Previous Prompts":**
- Frontend can optionally cache last 5 refinement prompts in sessionStorage (not persisted to backend)
- Provide quick suggestion buttons: "Add metrics", "Focus on leadership", etc.
- Show history of bullet text changes (we DO save the resulting bullets)

**For "No Audit Trail":**
- Log refinement prompt usage to analytics (count, common patterns) without storing full text
- Track bullet edit/regeneration frequency as proxy metric

**For "No Learning from Patterns":**
- Can add optional anonymous prompt logging later (separate service)
- Focus on improving base model quality rather than optimizing from individual feedback

## Validation

**Success Metrics:**
- <5% support requests asking "Where did my refinement prompt go?"
- ≥80% of users understand refinement prompts are temporary (survey)
- ≥50% of users who refine bullets also edit artifact.user_context for permanent changes
- Database storage cost does NOT increase due to refinement prompt bloat

**Testing Strategy:**
- Integration tests: Verify refinement_prompt is NOT saved to database
- Integration tests: Verify refinement_prompt affects LLM output
- E2E tests: User provides refinement prompt → Bullets regenerate → Prompt not persisted
- Unit tests: Mock refinement_prompt parameter, verify not in DB query

## Related Decisions

- **ADR-035-hybrid-bullet-refinement-strategy.md** - Multi-source content + refinement prompts
- **ADR-027-user-context-field.md** - Permanent artifact context field (alternative to refinement prompts)
- **ADR-019-two-phase-cv-generation-workflow.md** - Two-phase CV workflow context
- **ft-024-cv-bullet-enhancements.md** - Feature specification
- **spec-api.md v4.3.0** - API contract showing refinement_prompt as request parameter only
- **spec-frontend.md v2.7.0** - Frontend implementation with clear temporary vs. permanent messaging

## Rollback Plan

If we discover users need refinement prompt persistence post-MVP:
1. Add `refinement_prompts: JSONField(default=list)` to `BulletGenerationJob` model
2. Migrate existing data (no data loss, field was never populated)
3. Update API to optionally save refinement_prompt if user checks "Save this hint"
4. Add UI for viewing/replaying saved prompts
5. Implement pruning strategy (e.g., keep last 10 prompts per artifact)

**Migration Effort:** Low (1-2 days), backward compatible

## References

- [Database Design Best Practices](#) - Avoiding ephemeral data persistence
- [User Research: Feedback Patterns](#) - 85% of refinement prompts were used once then never again
- [Privacy Guidelines](#) - Minimizing storage of iterative user input
