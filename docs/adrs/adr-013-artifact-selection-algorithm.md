# ADR — Artifact Selection Algorithm

**Status:** ~~Draft~~ **Superseded by ADR-028** (2025-10-16)
**Date:** 2025-09-27
**Deciders:** Engineering, ML Team
**Technical Story:** Implement intelligent artifact selection for CV generation

---
> **⚠️ SUPERSEDED:** This ADR is superseded by [ADR-028: Remove Embeddings and Implement Manual Artifact Selection](adr-028-remove-embeddings-manual-selection.md) dated 2025-10-16. The multi-factor semantic ranking approach was replaced with keyword-based suggestions and manual user selection.
---

## Context and Problem Statement

The CV generation system must select the most relevant artifacts from a user's portfolio to include in a tailored CV. With users potentially having 20+ artifacts containing multiple data sources (GitHub repos, PDFs, videos, etc.), we need an algorithm that selects 6-8 most relevant artifacts for a given job description while ensuring diversity, quality, and optimal CV length.

**Key Challenge:** Multi-source artifacts require complex processing to extract relevant information for similarity calculation. Processing GitHub repositories, PDF documents, and media files on-the-fly during CV generation would be too slow and inconsistent.

**Preprocessing Solution:** Artifacts are preprocessed when uploaded, generating unified descriptions, extracting technologies/achievements, and computing embeddings. This enables fast, consistent artifact selection during CV generation.

## Decision Drivers

- **Relevance Accuracy:** Selected artifacts must be highly relevant to the target job
- **Processing Speed:** Selection must complete within 5 seconds for good UX
- **Diversity:** Avoid selecting too many similar artifacts (e.g., all backend projects)
- **Scalability:** Algorithm must work with 1-100+ artifacts per user
- **Interpretability:** Users should understand why artifacts were selected/rejected
- **Quality Consideration:** Artifact quality and evidence strength should influence selection
- **Career Progression:** Selection should reflect appropriate seniority level

## Considered Options

### Option A: Pure Vector Similarity Matching
- **Algorithm:** Embed job description and artifacts, select top N by cosine similarity
- **Pros:** Fast, simple implementation, good baseline relevance
- **Cons:** No diversity consideration, may miss skill gaps, ignores artifact quality

### Option B: Rule-Based Expert System
- **Algorithm:** Hand-crafted rules based on skills, technologies, and role types
- **Pros:** Highly interpretable, incorporates domain expertise, controllable behavior
- **Cons:** Brittle, maintenance overhead, poor generalization to new domains

### Option C: Simplified Multi-Factor Scoring (Recommended)
- **Algorithm:** Combine vector similarity, skill matching, and role level appropriateness
- **Pros:** Balanced approach, focused on core relevance criteria, simple implementation
- **Cons:** Less granular than full multi-factor approach

### Option D: ML-Based Ranking Model
- **Algorithm:** Train a ranking model on user feedback and successful CV outcomes
- **Pros:** Learns from user behavior, potentially optimal selections
- **Cons:** Requires extensive training data, less interpretable, cold start problem

## Decision Outcome

**Chosen Option: Option C - Simplified Multi-Factor Scoring Algorithm**

### Rationale

1. **Focused Relevance:** Combines the three most critical factors for artifact selection
2. **Interpretability:** Each scoring factor can be clearly explained to users
3. **Simple Implementation:** Reduces complexity while maintaining effectiveness
4. **Tunable:** Weights can be adjusted based on user feedback and A/B testing
5. **Immediate Implementation:** Doesn't require extensive ML training data

### Algorithm Design

```python
class ArtifactSelector:
    def __init__(self):
        self.scoring_weights = {
            "vector_similarity": 0.50,    # Primary relevance
            "skill_match": 0.25,          # Explicit skill alignment
            "role_level_match": 0.25,     # Seniority appropriateness
        }

    async def select_artifacts(
        self,
        user_artifacts: List[Artifact],
        job_context: JobContext,
        max_artifacts: int = 8
    ) -> List[RankedArtifact]:
        """Multi-factor artifact selection algorithm"""

        # Step 1: Calculate base scores for each artifact
        scored_artifacts = []
        for artifact in user_artifacts:
            score = await self._calculate_composite_score(artifact, job_context)
            scored_artifacts.append((artifact, score))

        # Step 2: Apply diversity filtering
        diverse_artifacts = self._apply_diversity_filtering(
            scored_artifacts, job_context
        )

        # Step 3: Final ranking and selection
        final_selection = sorted(
            diverse_artifacts,
            key=lambda x: x[1],
            reverse=True
        )[:max_artifacts]

        return [
            RankedArtifact(
                artifact=artifact,
                total_score=score,
                score_breakdown=self._get_score_breakdown(artifact, job_context)
            )
            for artifact, score in final_selection
        ]

    async def _calculate_composite_score(
        self,
        artifact: Artifact,
        job_context: JobContext
    ) -> float:
        """Calculate weighted composite score"""

        scores = {}

        # Vector similarity (50% weight)
        scores["vector_similarity"] = await self._vector_similarity_score(
            artifact, job_context
        )

        # Explicit skill matching (25% weight)
        scores["skill_match"] = self._skill_match_score(
            artifact.technologies, job_context.required_skills
        )

        # Role level appropriateness (25% weight)
        scores["role_level_match"] = self._role_level_score(
            artifact, job_context.seniority_level
        )

        # Calculate weighted sum
        total_score = sum(
            scores[factor] * self.scoring_weights[factor]
            for factor in scores
        )

        return min(total_score, 1.0)
```

### Diversity Filtering Strategy

```python
def _apply_diversity_filtering(
    self,
    scored_artifacts: List[Tuple[Artifact, float]],
    job_context: JobContext
) -> List[Tuple[Artifact, float]]:
    """Ensure portfolio diversity in selection"""

    selected = []
    technology_counts = defaultdict(int)
    domain_counts = defaultdict(int)

    # Sort by score for greedy selection
    candidates = sorted(scored_artifacts, key=lambda x: x[1], reverse=True)

    for artifact, score in candidates:
        # Check diversity constraints
        primary_tech = self._get_primary_technology(artifact)
        domain = self._get_artifact_domain(artifact)

        # Diversity penalties
        tech_penalty = min(technology_counts[primary_tech] * 0.1, 0.3)
        domain_penalty = min(domain_counts[domain] * 0.15, 0.4)

        # Apply penalties
        adjusted_score = score - tech_penalty - domain_penalty

        # Apply diversity bonus for complementary skills
        if self._complements_existing_selection(artifact, selected, job_context):
            adjusted_score += 0.05

        selected.append((artifact, adjusted_score))
        technology_counts[primary_tech] += 1
        domain_counts[domain] += 1

    return selected
```

### Scoring Function Details

```python
# Vector Similarity (50% weight)
async def select_artifacts_with_preprocessing(
    self,
    user_id: int,
    job_context: JobContext,
    max_artifacts: int = 8
) -> List[RankedArtifact]:
    """Fast artifact selection using preprocessed embeddings and metadata"""

    # Get job description embedding (only computed once)
    job_embedding = await self.embedding_service.embed(
        f"{job_context.role_title} {job_context.description}"
    )

    # Use pgvector for efficient similarity search on preprocessed embeddings
    similar_artifacts = await PreprocessedArtifact.objects.filter(
        user_id=user_id
    ).annotate(
        vector_similarity=CosineDistance('embedding_vector', job_embedding)
    ).order_by('vector_similarity')[:max_artifacts * 2]

    # Re-rank using multi-factor scoring with preprocessed data
    ranked_artifacts = []
    for artifact in similar_artifacts:
        # Vector similarity (50% weight) - already computed efficiently
        vector_score = artifact.vector_similarity

        # Skill matching (25% weight) - using preprocessed technologies
        skill_score = self._skill_match_score_preprocessed(
            artifact.extracted_technologies, job_context.required_skills
        )

        # Role level matching (25% weight) - using dynamic assessment
        role_score = self._assess_role_alignment_dynamic(
            artifact.unified_description, job_context.seniority_level
        )

        total_score = (
            vector_score * 0.50 +
            skill_score * 0.25 +
            role_score * 0.25
        )

        ranked_artifacts.append(RankedArtifact(
            artifact=artifact,
            total_score=total_score,
            vector_similarity=vector_score,
            skill_match=skill_score,
            role_alignment=role_score
        ))

    # Sort by total score and return top artifacts
    ranked_artifacts.sort(key=lambda x: x.total_score, reverse=True)
    return ranked_artifacts[:max_artifacts]

# Skill Matching (25% weight) - Using Preprocessed Data
def _skill_match_score_preprocessed(
    self,
    extracted_technologies: List[str],
    required_skills: List[str]
) -> float:
    """Efficient skill overlap calculation using preprocessed technologies"""

    # Use preprocessed, normalized technology list
    artifact_skills = set(skill.lower() for skill in extracted_technologies)
    required_set = set(skill.lower() for skill in required_skills)

    if not required_set:
        return 0.5  # Neutral score when no explicit requirements

    # Jaccard similarity coefficient
    intersection = artifact_skills & required_set
    union = artifact_skills | required_set

    base_score = len(intersection) / len(union) if union else 0

    # Bonus for matching high-priority skills
    priority_bonus = sum(
        0.1 for skill in intersection
        if skill in self.high_priority_skills
    )

    return min(base_score + priority_bonus, 1.0)

# Role Level Matching (25% weight)
def _role_level_score(
    self,
    artifact: Artifact,
    target_seniority: str
) -> float:
    """Assess artifact appropriateness for role seniority"""

    artifact_level = self._infer_artifact_seniority(artifact)

    # Seniority mapping: junior=1, mid=2, senior=3, staff=4, principal=5
    level_map = {"junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 5}

    artifact_num = level_map.get(artifact_level, 2)
    target_num = level_map.get(target_seniority, 2)

    # Prefer artifacts at or slightly above target level
    if artifact_num == target_num:
        return 1.0
    elif artifact_num == target_num + 1:
        return 0.8
    elif artifact_num == target_num - 1:
        return 0.6
    else:
        return max(0.2, 1.0 - abs(artifact_num - target_num) * 0.2)
```

## Positive Consequences

- **Improved Relevance:** Multi-factor approach captures different types of job relevance
- **Portfolio Diversity:** Prevents over-selection of similar artifacts
- **User Understanding:** Score breakdown helps users understand selection rationale
- **Tunable Performance:** Weights can be adjusted based on user feedback and outcomes
- **Quality Consideration:** Higher-quality artifacts receive selection preference
- **Scalable Implementation:** Algorithm performance scales well with artifact count

## Negative Consequences

- **Complexity:** More complex than simple vector similarity approach
- **Parameter Tuning:** Requires ongoing optimization of scoring weights
- **Computational Overhead:** Multiple scoring factors increase processing time
- **Potential Over-Engineering:** May be more complex than needed for MVP

## Mitigation Strategies

### Performance Optimization
```python
# Caching strategy for expensive operations
@lru_cache(maxsize=1000)
async def _cached_embedding(self, text: str) -> List[float]:
    return await self.embedding_service.embed(text)

# Parallel score calculation
async def _calculate_scores_parallel(
    self,
    artifacts: List[Artifact],
    job_context: JobContext
) -> List[float]:
    tasks = [
        self._calculate_composite_score(artifact, job_context)
        for artifact in artifacts
    ]
    return await asyncio.gather(*tasks)
```

### Parameter Optimization
- **A/B Testing Framework:** Test different weight combinations with real users
- **Feedback Integration:** Adjust weights based on user selection overrides
- **Domain-Specific Tuning:** Different weights for different industries/roles

### Complexity Management
- **Modular Design:** Each scoring factor is independently testable and replaceable
- **Feature Flags:** Enable/disable scoring factors for experimentation
- **Fallback Strategy:** Revert to simple vector similarity if complex algorithm fails

## Monitoring and Success Metrics

- **Selection Accuracy:** % of selected artifacts that users keep vs override
- **User Satisfaction:** Rating of artifact selection quality (target ≥8/10)
- **Processing Speed:** Algorithm execution time (target <5 seconds)
- **Diversity Metrics:** Technology and domain distribution in selections
- **CV Performance:** Job application success rates with selected artifacts

## Implementation Phases

### Phase 1: Basic Implementation
- Vector similarity + skill matching only
- Simple diversity filtering
- Manual weight tuning

### Phase 2: Enhanced Scoring
- Add quality and recency factors
- Implement role level scoring
- A/B testing framework

### Phase 3: Optimization
- Machine learning for weight optimization
- Advanced diversity algorithms
- Performance optimization

## References

- **Information Retrieval Research:** Modern ranking algorithms in search systems
- **Portfolio Theory:** Diversification strategies adapted for artifact selection
- **User Experience Research:** Studies on selection explanation and user trust

## Related ADRs

- [ADR-016-three-bullets-per-artifact](adr-016-three-bullets-per-artifact.md)
- [ADR-002-embedding-storage-strategy](adr-002-embedding-storage-strategy.md)
- [ADR-008-llm-provider-strategy](adr-008-llm-provider-strategy.md)

