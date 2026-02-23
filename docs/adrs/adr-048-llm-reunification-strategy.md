# ADR — LLM-Based Re-unification from User-Edited Evidence

**Status:** Draft → Accepted (upon implementation completion)
**Date:** 2025-01-06
**Deciders:** Engineering Team, Product Team
**Technical Story:** Implement ft-045 Evidence Review & Acceptance Workflow

## Context and Problem Statement

After users review and edit AI-extracted evidence content in the evidence review workflow (ft-045), the system must **re-unify the artifact content** to reflect user corrections before bullet generation.

**Current Flow (Initial Upload):**
```
Evidence sources (GitHub, PDFs)
  ↓
AI extracts content → EnhancedEvidence.processed_content (technologies, achievements, summary)
  ↓
unify_content_with_llm(ExtractedContent[]) → Artifact.unified_description
  ↓
Artifact content used for bullet generation
```

**New Flow (After Evidence Review - ft-045):**
```
User reviews EnhancedEvidence.processed_content
  ↓
User edits inline (fix errors, add missing items, remove incorrect items)
  ↓
User accepts all evidence (100% acceptance required)
  ↓
❓ HOW TO RE-UNIFY? ❓
  ↓
reunify_from_accepted_evidence(artifact_id) → Updated Artifact.unified_description
  ↓
Artifact content used for bullet generation (now with user corrections)
```

**Problems to Solve:**

1. **User Edits Must Propagate:** EnhancedEvidence.processed_content (user-edited) contains corrections that must appear in final artifact content
2. **Not Simple Concatenation:** User confirmed: "The unification should be process by LLM like the original design" (not basic string joining)
3. **Accepted Evidence Only:** Only use evidence where `accepted=True` (user rejected evidence must be excluded)
4. **Preserve User Context:** Artifact.user_context field is immutable ground truth (ADR-027, ft-018)
5. **Data Source Change:** Original unification uses ExtractedContent, new unification must use EnhancedEvidence.processed_content
6. **Confidence Recalculation:** Re-unified artifact needs updated processing_confidence based on edited evidence

**User Requirements:**
> "If user edit and approve the evidences, then what is the workflow to generate downstream, artifact content?"
> **User confirmed:** "The unification should be process by LLM like the original design"

**We need to decide:**

1. **Data source:** Read from EnhancedEvidence.processed_content (user-edited) vs. raw_content vs. ExtractedContent (stale)
2. **Unification strategy:** LLM-based (like original) vs. template-based vs. simple concatenation
3. **Prompt design:** Reuse unify_content_with_llm prompt vs. new prompt emphasizing user edits
4. **Confidence scoring:** How to calculate processing_confidence after user edits
5. **Service layer:** New method reunify_from_accepted_evidence() vs. overload unify_content_with_llm()

## Decision Drivers

- **User Edits are Ground Truth:** User corrections must be preserved exactly (numbers, metrics, achievements)
- **LLM Quality:** Professional narrative generation requires LLM intelligence (not templates)
- **Consistency:** Re-unification should match quality of original unification
- **User Trust:** User sees immediate effect of edits in downstream artifacts
- **Accepted Evidence Only:** Rejected evidence must not affect artifact content
- **Performance:** Re-unification should complete in ≤5 seconds (finalize-evidence-review endpoint SLO)
- **Prompt Engineering:** Leverage existing unify_content_with_llm prompt patterns

## Considered Options

### Option A: Simple Concatenation (String Joining)

**Approach:** Join EnhancedEvidence.processed_content summaries with newlines

**Implementation:**
```python
def reunify_from_accepted_evidence(artifact_id):
    evidence = EnhancedEvidence.objects.filter(
        evidence__artifact_id=artifact_id,
        accepted=True
    )
    summaries = [e.processed_content.get('summary', '') for e in evidence]
    artifact.unified_description = '\n\n'.join(summaries)
```

**Pros:**
- Fastest implementation (no LLM calls)
- Deterministic output
- No API costs

**Cons:**
- **Violates user requirement:** "The unification should be process by LLM like the original design"
- **Poor quality:** Awkward narrative flow, repetition, unprofessional tone
- **No synthesis:** Doesn't deduplicate technologies or achievements
- **Loses context:** Doesn't integrate with user_context field
- **Inconsistent:** Different quality than initial unification (confusing for users)

**Estimated Effort:** 2-3 hours (simple implementation)

---

### Option B: Template-Based Unification

**Approach:** Use Django templates to structure evidence into predefined format

**Implementation:**
```python
template = """
{{ artifact.title }}

User Context: {{ artifact.user_context }}

Evidence Summary:
{% for evidence in accepted_evidence %}
- {{ evidence.processed_content.summary }}
  Technologies: {{ evidence.processed_content.technologies|join:", " }}
{% endfor %}
"""
```

**Pros:**
- Consistent structure
- No LLM costs
- Faster than LLM (1-2 seconds)

**Cons:**
- **Violates user requirement:** Not LLM-based as requested
- **Robotic output:** Template-generated text feels mechanical
- **No synthesis:** Can't merge overlapping technologies or achievements
- **Fixed structure:** Can't adapt narrative to content type
- **Poor CV quality:** Professional CVs need flowing narrative, not bullet lists

**Estimated Effort:** 4-6 hours (template design + integration)

---

### Option C: LLM Re-unification from EnhancedEvidence (Recommended) ✅

**Approach:** New reunify_from_accepted_evidence() method that calls LLM with EnhancedEvidence.processed_content (user-edited) instead of ExtractedContent

**Implementation:**
```python
async def reunify_from_accepted_evidence(self, artifact_id: int, user_id: Optional[int] = None):
    """
    Re-unify artifact content from user-accepted and edited evidence.

    Uses LLM to generate professional narrative from EnhancedEvidence.processed_content
    (user-edited) instead of ExtractedContent (original extraction).
    """
    # 1. Fetch artifact and accepted evidence
    artifact = await Artifact.objects.get(id=artifact_id)
    accepted_evidence = await EnhancedEvidence.objects.filter(
        evidence__artifact=artifact,
        accepted=True
    ).select_related('evidence')

    # 2. Build evidence summaries from user-edited processed_content
    source_summaries = []
    for enhanced_ev in accepted_evidence:
        summary = f"Source: {enhanced_ev.title} ({enhanced_ev.content_type})\n"

        # Use user-edited processed_content (not raw_content)
        pc = enhanced_ev.processed_content
        if pc.get('technologies'):
            summary += f"Technologies: {', '.join(pc['technologies'][:10])}\n"
        if pc.get('achievements'):
            summary += f"Achievements: {', '.join(pc['achievements'][:5])}\n"
        if pc.get('summary'):
            summary += f"Summary: {pc['summary']}\n"

        source_summaries.append(summary)

    # 3. Call LLM with similar prompt to unify_content_with_llm
    # (reuse prompt pattern, emphasize user edits as ground truth)
    unified_description = await self._call_unification_llm(
        artifact.title,
        artifact.user_context,
        source_summaries,
        user_id
    )

    # 4. Update artifact fields
    artifact.unified_description = unified_description
    artifact.enriched_technologies = self._extract_technologies(accepted_evidence)
    artifact.enriched_achievements = self._extract_achievements(accepted_evidence)
    artifact.processing_confidence = self._calculate_confidence(accepted_evidence)
    await artifact.save()

    return artifact
```

**Pros:**
- **Meets user requirement:** LLM-based like original design
- **Professional quality:** Same high-quality narrative as initial unification
- **User edits preserved:** processed_content (user-edited) is source of truth
- **Synthesis:** LLM deduplicates technologies, merges achievements naturally
- **User context integration:** Respects Artifact.user_context as immutable (ADR-027)
- **Consistent experience:** Same quality as unify_content_with_llm
- **Flexible:** LLM adapts narrative to evidence type and content

**Cons:**
- **LLM cost:** ~$0.01-0.03 per re-unification (GPT-5 inference)
- **Latency:** 3-5 seconds vs. instant (templates/concatenation)
- **Error handling:** Must handle LLM failures gracefully

**Estimated Effort:** 6-8 hours (new method + prompt design + tests)

---

### Option D: Hybrid with User Edits Highlighted

**Approach:** LLM unification with special prompt markers for user-edited fields

**Implementation:**
```python
# Mark user-edited fields in prompt
summary = f"Source: {enhanced_ev.title}\n"
summary += f"[USER EDITED] Summary: {pc['summary']}\n"
summary += f"[USER EDITED] Technologies: {pc['technologies']}\n"

prompt = """CRITICAL: Fields marked [USER EDITED] are user-corrected and MUST be preserved exactly..."""
```

**Pros:**
- Explicit user edit preservation
- Clear provenance of data
- LLM knows which content to trust

**Cons:**
- **Over-engineering:** LLM already respects all input equally
- **Prompt bloat:** Extra markers increase token usage
- **Unnecessary:** All EnhancedEvidence.processed_content is user-accepted (already trustworthy)
- **Confusing:** Markers might confuse LLM narrative generation

**Estimated Effort:** 8-10 hours (complex prompt engineering + validation)

---

### Option E: Progressive Enhancement (Start Simple, Add LLM Later)

**Approach:** Phase 1: Template-based, Phase 2: LLM-based (deferred)

**Pros:**
- Faster initial delivery
- Can ship ft-045 sooner

**Cons:**
- **Violates user requirement immediately:** User confirmed LLM-based needed
- **Technical debt:** Will need LLM eventually, why delay?
- **Poor user experience:** Users see low-quality output initially
- **Migration complexity:** Need to re-unify all artifacts later

**Estimated Effort:** 4-6 hours (Phase 1) + 6-8 hours (Phase 2) = 10-14 hours total (more than Option C)

## Decision Outcome

**Chosen Option: Option C - LLM Re-unification from EnhancedEvidence**

### Rationale

1. **Meets User Requirement:**
   - User explicitly confirmed: "The unification should be process by LLM like the original design"
   - LLM-based approach is non-negotiable (user requirement)

2. **Professional Quality:**
   - LLM generates flowing, professional narrative (matching CV standards)
   - Deduplicates technologies naturally ("React, React" → "React")
   - Synthesizes achievements into cohesive story
   - Adapts tone and structure to content

3. **User Edits are Ground Truth:**
   - Reads from EnhancedEvidence.processed_content (user-edited, not raw extraction)
   - User corrections (fixed technologies, corrected achievements) propagate to artifact
   - Rejected evidence excluded (accepted=False not used)

4. **Consistency with Original Design:**
   - Reuses unify_content_with_llm prompt patterns (proven to work)
   - Same GPT-5 model and reasoning approach
   - Users get consistent quality (initial unification vs. re-unification)

5. **Respects User Context (ADR-027):**
   - Artifact.user_context is immutable ground truth
   - LLM prompt treats user_context as ABSOLUTE TRUTH (same as original)
   - User-provided facts preserved exactly (numbers, metrics, team sizes)

6. **Reasonable Cost:**
   - ~$0.01-0.03 per re-unification (one-time cost per artifact)
   - User already paid for initial unification (same pattern)
   - Quality justifies cost (prevents poor CV generation downstream)

7. **Acceptable Latency:**
   - 3-5 seconds for re-unification (within 5s SLO)
   - User expects processing time (just reviewed evidence for 2-5 minutes)
   - One-time cost at finalization (not repeated)

### Architecture Decision

**Service Layer Method:**
```python
# backend/llm_services/services/core/artifact_enrichment_service.py

class ArtifactEnrichmentService(BaseLLMService):

    async def reunify_from_accepted_evidence(
        self,
        artifact_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Re-unify artifact content from user-accepted and edited evidence.

        Similar to unify_content_with_llm but:
        - Reads from EnhancedEvidence.processed_content (user-edited) instead of ExtractedContent
        - Only uses evidence where accepted=True
        - Returns updated artifact with unified_description, enriched_technologies, enriched_achievements

        Args:
            artifact_id: Artifact ID to re-unify
            user_id: User ID for tracking

        Returns:
            Dict with updated artifact fields:
            {
                'unified_description': str,
                'enriched_technologies': List[str],
                'enriched_achievements': List[str],
                'processing_confidence': float
            }
        """
        # Implementation details in next section
```

**Data Flow:**
```
POST /api/v1/artifacts/{id}/finalize-evidence-review/
  ↓
ArtifactViewSet.finalize_evidence_review()
  ↓
service = ArtifactEnrichmentService()
result = await service.reunify_from_accepted_evidence(artifact_id, user_id)
  ↓
Artifact.unified_description = result['unified_description']
Artifact.enriched_technologies = result['enriched_technologies']
Artifact.enriched_achievements = result['enriched_achievements']
Artifact.processing_confidence = result['processing_confidence']
Artifact.save()
  ↓
Return updated artifact to frontend
```

**Prompt Design (Reuse unify_content_with_llm Pattern):**

```python
# Build source summaries from ACCEPTED EnhancedEvidence only
source_summaries = []
for enhanced_ev in accepted_evidence:
    summary = f"Source: {enhanced_ev.title} ({enhanced_ev.content_type})\n"

    # Use user-edited processed_content (not raw_content)
    pc = enhanced_ev.processed_content

    if pc.get('technologies'):
        summary += f"Technologies: {', '.join(pc['technologies'][:10])}\n"

    if pc.get('achievements'):
        summary += f"Achievements: {', '.join(pc['achievements'][:5])}\n"

    if pc.get('summary'):
        summary += f"Description: {pc['summary']}\n"

    source_summaries.append(summary)

# Reuse ft-018 prompt pattern (user_context as immutable ground truth)
has_user_context = artifact.user_context and artifact.user_context.strip()

if has_user_context:
    prompt = f"""You are creating a professional CV/resume description. You MUST follow this strict hierarchy:

**GROUND TRUTH (User-Provided Facts - IMMUTABLE):**
{artifact.user_context.strip()}

**USER-ACCEPTED EVIDENCE (Already reviewed and corrected by user):**
{chr(10).join(source_summaries)}

**CRITICAL RULES:**
1. User-provided FACTS are ABSOLUTE TRUTH - preserve all numbers, team sizes, metrics, roles EXACTLY
2. Evidence has been reviewed and corrected by user - trust this content
3. INTEGRATE facts naturally into flowing narrative - DO NOT copy-paste as standalone sentences
4. Create ONE cohesive narrative - not "user section + evidence section"
5. Maintain professional CV/resume tone

**Your Task:**
Create a unified description (200-400 words) for "{artifact.title}" that:
- WEAVES user-provided facts naturally throughout the narrative
- INTEGRATES them seamlessly with user-corrected evidence details
- Creates ONE flowing, professional paragraph
- Maintains professional CV/resume tone

Return ONLY the unified description, no preamble or explanation."""
else:
    prompt = f"""Create a comprehensive, professional description for this project/artifact from USER-ACCEPTED EVIDENCE.

Artifact Title: {artifact.title}
Original Description: {artifact.description}

USER-ACCEPTED EVIDENCE (Already reviewed and corrected):
{chr(10).join(source_summaries)}

Generate a unified, coherent description (200-400 words) that:
1. Combines insights from all user-accepted evidence
2. Highlights key technologies and frameworks
3. Emphasizes quantifiable achievements and impact
4. Maintains professional tone
5. Is optimized for CV/resume use

Return ONLY the unified description, no preamble."""
```

**Confidence Calculation:**
```python
def _calculate_reunification_confidence(self, accepted_evidence: List[EnhancedEvidence]) -> float:
    """
    Calculate processing confidence from user-accepted evidence.

    User acceptance implies high confidence (user verified content).
    Weighted average of original processing_confidence scores.
    """
    if not accepted_evidence:
        return 0.0

    # User acceptance boosts confidence
    # Average original processing_confidence + 0.1 bonus for user acceptance
    avg_confidence = sum(e.processing_confidence for e in accepted_evidence) / len(accepted_evidence)
    user_acceptance_bonus = 0.1

    return min(1.0, avg_confidence + user_acceptance_bonus)
```

### Technology & Achievement Extraction

**Technologies:**
```python
def _extract_reunified_technologies(self, accepted_evidence: List[EnhancedEvidence]) -> List[str]:
    """Extract unique technologies from user-edited processed_content"""
    tech_set = set()
    for evidence in accepted_evidence:
        pc = evidence.processed_content
        if pc.get('technologies'):
            tech_set.update(pc['technologies'])
    return sorted(list(tech_set))
```

**Achievements:**
```python
def _extract_reunified_achievements(self, accepted_evidence: List[EnhancedEvidence]) -> List[str]:
    """Extract unique achievements from user-edited processed_content"""
    achievements = []
    for evidence in accepted_evidence:
        pc = evidence.processed_content
        if pc.get('achievements'):
            achievements.extend(pc['achievements'])
    return achievements[:10]  # Limit to top 10
```

## Consequences

### Positive

1. **User Edits Preserved:**
   - EnhancedEvidence.processed_content (user-edited) is source of truth
   - User corrections propagate to Artifact.unified_description
   - Rejected evidence excluded automatically (accepted=False)

2. **Professional Quality:**
   - LLM generates flowing narrative (CV-ready)
   - Deduplicates technologies naturally
   - Synthesizes achievements cohesively
   - Adapts tone to content type

3. **Consistent Experience:**
   - Same quality as initial unification (unify_content_with_llm)
   - Same LLM model (GPT-5)
   - Same prompt patterns (ft-018 user context as immutable)

4. **User Trust:**
   - Users see immediate effect of edits
   - "I fixed the technologies, now my CV has correct tech stack"
   - Transparent process (user reviewed → LLM unifies → artifact updated)

5. **Respects User Context (ADR-027):**
   - Artifact.user_context remains immutable ground truth
   - User-provided facts preserved exactly (numbers, metrics, roles)
   - LLM integrates evidence without contradicting user facts

6. **Performance:**
   - 3-5 seconds (within 5s SLO)
   - One-time cost at finalization
   - Acceptable latency for quality gain

### Negative

1. **LLM Cost:**
   - **Impact:** ~$0.01-0.03 per re-unification (GPT-5 API call)
   - **Mitigation:**
     - One-time cost per artifact finalization
     - Same cost as initial unification (users already accept this)
     - Quality justifies cost (prevents poor CV generation)
     - Alternative: Could use GPT-4 for cost savings (trade quality)

2. **Latency:**
   - **Impact:** 3-5 seconds for re-unification (vs. instant concatenation)
   - **Mitigation:**
     - User just spent 2-5 minutes reviewing evidence (processing time expected)
     - Loading spinner with message: "Finalizing your artifact..."
     - One-time cost (not repeated)
     - Async processing option (return immediately, update later)

3. **LLM Failures:**
   - **Impact:** LLM call might fail (rate limits, API errors)
   - **Mitigation:**
     - Fallback to concatenation (graceful degradation)
     - Retry logic with exponential backoff
     - Circuit breaker pattern (existing in llm_services)
     - Error message with retry option

4. **Prompt Engineering Complexity:**
   - **Impact:** Must maintain prompt quality (user context + evidence integration)
   - **Mitigation:**
     - Reuse proven unify_content_with_llm prompt patterns
     - Comprehensive unit tests for edge cases
     - Fallback prompt if user_context missing

### Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM cost exceeds budget | Low | Medium | Monitor usage, implement rate limiting per user, fallback to cheaper model |
| LLM hallucinations | Low | High | User already reviewed evidence (ground truth), prompt emphasizes user corrections |
| Latency >5 seconds | Low | Medium | Async processing option, progress indicators, caching for re-unifications |
| API failures | Medium | High | Retry logic, circuit breaker, fallback to concatenation, error messages |
| Prompt drift (quality degrades) | Low | Medium | Automated quality tests, A/B testing, prompt version tracking |
| User edits lost | Very Low | Critical | Database transactions, rollback on failure, audit logging |

## Implementation Notes

### Phase 1: Service Layer Method (4 hours)

**Deliverable:**
```python
# backend/llm_services/services/core/artifact_enrichment_service.py

async def reunify_from_accepted_evidence(
    self,
    artifact_id: int,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """Re-unify artifact content from user-accepted and edited evidence"""

    # 1. Fetch artifact and accepted evidence
    artifact = await sync_to_async(Artifact.objects.get)(id=artifact_id)
    accepted_evidence = await sync_to_async(list)(
        EnhancedEvidence.objects.filter(
            evidence__artifact=artifact,
            accepted=True
        ).select_related('evidence')
    )

    # 2. Build source summaries from processed_content
    source_summaries = self._build_evidence_summaries(accepted_evidence)

    # 3. Call LLM (reuse unify_content_with_llm prompt pattern)
    unified_description = await self._call_unification_llm(
        artifact.title,
        artifact.description,
        artifact.user_context,
        source_summaries,
        user_id
    )

    # 4. Extract technologies and achievements
    technologies = self._extract_reunified_technologies(accepted_evidence)
    achievements = self._extract_reunified_achievements(accepted_evidence)
    confidence = self._calculate_reunification_confidence(accepted_evidence)

    # 5. Update artifact
    artifact.unified_description = unified_description
    artifact.enriched_technologies = technologies
    artifact.enriched_achievements = achievements
    artifact.processing_confidence = confidence
    await sync_to_async(artifact.save)()

    return {
        'artifact_id': artifact.id,
        'unified_description': unified_description,
        'enriched_technologies': technologies,
        'enriched_achievements': achievements,
        'processing_confidence': confidence
    }
```

### Phase 2: API Endpoint Integration (2 hours)

**Deliverable:**
```python
# backend/artifacts/views.py

@action(detail=True, methods=['post'], url_path='finalize-evidence-review')
async def finalize_evidence_review(self, request, pk=None):
    """Finalize evidence review and re-unify artifact content"""

    # Check all evidence accepted
    acceptance_status = await self._get_acceptance_status(pk)
    if not acceptance_status['can_finalize']:
        return Response(
            {'error': 'All evidence must be accepted before finalizing'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Re-unify from accepted evidence
    service = ArtifactEnrichmentService()
    result = await service.reunify_from_accepted_evidence(
        artifact_id=int(pk),
        user_id=request.user.id
    )

    # Return updated artifact
    return Response(result, status=status.HTTP_200_OK)
```

### Phase 3: Error Handling & Fallbacks (1 hour)

**Deliverable:**
```python
# Fallback if LLM fails
try:
    unified_description = await self._call_unification_llm(...)
except LLMError as e:
    logger.error(f"LLM unification failed: {e}")
    # Fallback: concatenate summaries
    unified_description = self._fallback_concatenation(accepted_evidence)
```

### Phase 4: Tests (1-2 hours)

**Unit Tests:**
- ✅ reunify_from_accepted_evidence with user_context
- ✅ reunify_from_accepted_evidence without user_context
- ✅ Only accepted evidence used (rejected excluded)
- ✅ User edits preserved in unified description
- ✅ LLM failure fallback
- ✅ Confidence calculation

**Integration Tests:**
- ✅ Full workflow: review → edit → accept → finalize → verify artifact updated
- ✅ API endpoint: POST /finalize-evidence-review/

### Performance Optimization

**Caching (Future Enhancement):**
```python
# Cache re-unification results (if evidence unchanged)
cache_key = f"artifact:{artifact_id}:reunified:{evidence_hash}"
cached = cache.get(cache_key)
if cached:
    return cached
```

**Async Processing (Future Enhancement):**
```python
# Return immediately, process in background
@action(detail=True, methods=['post'])
async def finalize_evidence_review(self, request, pk=None):
    # Queue re-unification task
    task = reunify_artifact.delay(artifact_id=pk, user_id=request.user.id)
    return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
```

## References

- **PRD:** `docs/prds/prd.md` (v1.5.0) - Evidence Review & Acceptance workflow
- **DISCOVERY:** `docs/discovery/disco-001-evidence-review-workflow.md` - Workflow analysis
- **TECH SPECS:**
  - `docs/specs/spec-llm.md` (v4.3.0) - reunify_from_accepted_evidence method
  - `docs/specs/spec-api.md` (v4.9.0) - finalize-evidence-review endpoint
- **FEATURE:** `docs/features/ft-045-evidence-review-workflow.md` - Implementation plan (Stage E)
- **Related ADRs:**
  - ADR-046: Blocking Evidence Review Workflow (triggers re-unification)
  - ADR-047: EnhancedEvidence Consolidation (EnhancedEvidence is single source)
  - ADR-027: User Context Field (user_context as immutable ground truth)
  - ADR-015: Multi-Source Artifact Preprocessing (original unify_content_with_llm design)

## Related Decisions

- **Future ADR:** If LLM costs become prohibitive, evaluate cheaper models (GPT-4 vs. GPT-5)

## Notes

- This ADR will transition from "Draft" to "Accepted" upon successful implementation and deployment
- Git tag: `adr-048-llm-reunification-strategy` after acceptance
- User confirmed: "The unification should be process by LLM like the original design"
- Reuses proven unify_content_with_llm prompt patterns (ft-018, ADR-027)
- Performance SLO: ≤5 seconds for re-unification (95th percentile)
- LLM cost: ~$0.01-0.03 per artifact finalization (acceptable for quality)
