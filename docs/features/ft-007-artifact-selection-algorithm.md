# Feature — 007 artifact-selection-algorithm

**File:** docs/features/ft-007-artifact-selection-algorithm.md
**Owner:** ML/Backend Team
**TECH-SPECs:** `spec-api.md` (v2.0), `spec-llm.md` (v1.0), `spec-system.md` (v1.0)
**Related ADRs:** [ADR-013-artifact-selection-algorithm](../adrs/adr-013-artifact-selection-algorithm.md)

## Existing Implementation Analysis

**Similar Features:**
- `llm_services/services/core/embedding_service.py` - Vector embedding generation and similarity search
- `llm_services/services/core/artifact_ranking_service.py` - Semantic relevance ranking using pgvector
- `artifacts/services/artifact_service.py` - Artifact CRUD and filtering operations

**Reusable Components:**
- `llm_services/services/core/embedding_service.py` - Reuse for vector similarity search
- `llm_services/services/infrastructure/model_selector.py` - Model selection for embeddings
- Database: pgvector extension already enabled for similarity search
- `llm_services/services/reliability/circuit_breaker.py` - API fault tolerance

**Patterns to Follow:**
- Service layer pattern from llm_services (base → core → infrastructure → reliability)
- Vector similarity search using pgvector (already implemented in embedding_service)
- Multi-factor scoring combining semantic + metadata signals
- Caching strategy for frequently accessed embeddings

**Code to Refactor:**
- None (new feature building on existing embedding infrastructure)

**Dependencies:**
- `llm_services.services.core.EmbeddingService` (vector embeddings)
- `llm_services.services.core.ArtifactRankingService` (semantic ranking)
- `artifacts.models.Artifact` (data model)
- PostgreSQL with pgvector extension (infrastructure)

## Architecture Conformance

**Layer Assignment:**
- New service in `llm_services/services/core/dynamic_artifact_selector.py` (core layer)
- API endpoints in `generation/views.py` (interface layer)
- Data models in `artifacts/models.py` (data layer)

**Pattern Compliance:**
- ✅ Follows llm_services service structure
- ✅ Uses pgvector for similarity search (existing infrastructure)
- ✅ Multi-factor scoring pattern (semantic + metadata)
- ✅ Caching for performance optimization
- ✅ Circuit breaker for external API calls

**Dependencies:**
- `llm_services.services.core.EmbeddingService` (composition)
- `llm_services.services.core.ArtifactRankingService` (composition)
- `llm_services.services.infrastructure.ModelSelector` (composition)
- `artifacts.models.Artifact` (data access)
- pgvector extension (database infrastructure)

## Acceptance Criteria

- [ ] Intelligently selects 6-8 most relevant artifacts from user's portfolio for each CV
- [ ] Selection completes within 5 seconds using preprocessed artifact embeddings
- [ ] Multi-factor scoring combines vector similarity (50%), skill matching (25%), and role level appropriateness (25%)
- [ ] Diversity filtering prevents over-selection of similar artifacts (same tech stack/domain)
- [ ] Selection explanations show users why artifacts were chosen/rejected
- [ ] Algorithm handles 1-100+ artifacts per user efficiently using pgvector similarity search
- [ ] User can override selections with manual artifact choices
- [ ] Selection quality measured by user retention rate (≥80% of selected artifacts kept)
- [ ] Performance scales to 1000+ concurrent users without degradation
- [ ] A/B testing framework enables algorithm tuning and optimization
- [ ] Fallback mechanisms handle edge cases (insufficient artifacts, processing failures)
- [ ] Integration with preprocessing pipeline for real-time embedding updates

## Design Changes

### API Endpoints
**New endpoints:**
```python
# Artifact selection
POST /api/v1/cv/select-artifacts/               # Select artifacts for job
GET /api/v1/cv/selection/{id}/explanation/      # Selection rationale
POST /api/v1/cv/selection/{id}/override/        # User overrides
GET /api/v1/cv/selection/preview/               # Preview selection

# Selection analytics
GET /api/v1/analytics/artifact-selection/       # Selection performance metrics
POST /api/v1/analytics/selection-feedback/      # User feedback on selections
```

### Database Schema Changes
```sql
-- Artifact selection tracking
CREATE TABLE artifact_selections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    job_context_hash VARCHAR(64), -- Hash of job requirements for caching
    selected_artifacts JSONB, -- Array of artifact IDs with scores
    selection_metadata JSONB, -- Algorithm version, parameters used
    user_overrides JSONB, -- Manual additions/removals
    selection_timestamp TIMESTAMP DEFAULT NOW(),
    generation_duration_ms INTEGER
);

-- Selection feedback for algorithm improvement
CREATE TABLE selection_feedback (
    id SERIAL PRIMARY KEY,
    artifact_selection_id INTEGER REFERENCES artifact_selections(id),
    artifact_id INTEGER REFERENCES artifacts(id),
    feedback_type VARCHAR(20) CHECK (feedback_type IN ('kept', 'removed', 'added')),
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 10),
    feedback_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance analytics
CREATE TABLE selection_performance_metrics (
    id SERIAL PRIMARY KEY,
    algorithm_version VARCHAR(20),
    date DATE,
    total_selections INTEGER,
    avg_duration_ms FLOAT,
    user_satisfaction_rating FLOAT,
    artifact_retention_rate FLOAT,
    override_rate FLOAT
);

-- Indexes for performance
CREATE INDEX idx_artifact_selections_user_job ON artifact_selections (user_id, job_context_hash);
CREATE INDEX idx_selection_feedback_artifact ON selection_feedback (artifact_id, feedback_type);
```

### Core Selection Algorithm
```python
class ArtifactSelector:
    """Multi-factor artifact selection with diversity filtering"""

    def __init__(self):
        self.scoring_weights = {
            "vector_similarity": 0.50,
            "skill_match": 0.25,
            "role_level_match": 0.25
        }
        self.diversity_config = {
            "max_tech_overlap": 0.6,  # Max 60% artifacts with same primary tech
            "max_domain_overlap": 0.5, # Max 50% artifacts from same domain
            "complementary_bonus": 0.05 # Bonus for complementary skills
        }

    async def select_artifacts(
        self,
        user_id: int,
        job_context: JobContext,
        max_artifacts: int = 8
    ) -> ArtifactSelectionResult:
        """Main selection algorithm with caching and optimization"""

        # Check cache for similar job contexts
        cached_selection = await self._check_selection_cache(user_id, job_context)
        if cached_selection:
            return cached_selection

        # Get user's preprocessed artifacts with embeddings
        user_artifacts = await PreprocessedArtifact.objects.filter(
            user_id=user_id
        ).select_related('artifact').all()

        if len(user_artifacts) <= max_artifacts:
            # Return all artifacts if user has few
            return await self._create_selection_result(user_artifacts, job_context, "all_artifacts")

        # Step 1: Fast vector similarity pre-filtering using pgvector
        job_embedding = await self._get_job_embedding(job_context)
        top_candidates = await self._vector_similarity_prefilter(
            user_artifacts, job_embedding, limit=max_artifacts * 2
        )

        # Step 2: Multi-factor scoring
        scored_artifacts = []
        for artifact in top_candidates:
            composite_score = await self._calculate_composite_score(artifact, job_context)
            scored_artifacts.append((artifact, composite_score))

        # Step 3: Diversity filtering
        diverse_selection = self._apply_diversity_filtering(
            scored_artifacts, job_context, max_artifacts
        )

        # Step 4: Create selection result with explanations
        return await self._create_selection_result(diverse_selection, job_context, "algorithm")

    async def _vector_similarity_prefilter(
        self,
        artifacts: List[PreprocessedArtifact],
        job_embedding: List[float],
        limit: int
    ) -> List[PreprocessedArtifact]:
        """Fast pgvector similarity search for initial filtering"""

        similar_artifacts = await PreprocessedArtifact.objects.filter(
            id__in=[a.id for a in artifacts]
        ).annotate(
            similarity=CosineDistance('embedding_vector', job_embedding)
        ).order_by('similarity')[:limit]

        return similar_artifacts

    def _apply_diversity_filtering(
        self,
        scored_artifacts: List[Tuple[PreprocessedArtifact, float]],
        job_context: JobContext,
        max_count: int
    ) -> List[Tuple[PreprocessedArtifact, float]]:
        """Ensure portfolio diversity in final selection"""

        selected = []
        tech_counts = defaultdict(int)
        domain_counts = defaultdict(int)
        total_artifacts = len([a for a, _ in scored_artifacts])

        # Sort by score for greedy selection
        candidates = sorted(scored_artifacts, key=lambda x: x[1], reverse=True)

        for artifact, score in candidates:
            if len(selected) >= max_count:
                break

            # Calculate diversity penalties
            primary_tech = self._get_primary_technology(artifact)
            domain = self._get_artifact_domain(artifact)

            tech_ratio = tech_counts[primary_tech] / max(len(selected), 1)
            domain_ratio = domain_counts[domain] / max(len(selected), 1)

            # Apply diversity constraints
            if (tech_ratio > self.diversity_config["max_tech_overlap"] or
                domain_ratio > self.diversity_config["max_domain_overlap"]):
                # Skip if would violate diversity
                continue

            # Apply complementary skill bonus
            adjusted_score = score
            if self._has_complementary_skills(artifact, selected, job_context):
                adjusted_score += self.diversity_config["complementary_bonus"]

            selected.append((artifact, adjusted_score))
            tech_counts[primary_tech] += 1
            domain_counts[domain] += 1

        return selected
```

### Selection Explanation System
```python
class SelectionExplainer:
    """Generate human-readable explanations for selection decisions"""

    def explain_selection(
        self,
        selected: List[RankedArtifact],
        rejected: List[RankedArtifact],
        job_context: JobContext
    ) -> SelectionExplanation:
        """Create comprehensive selection explanation"""

        return SelectionExplanation(
            selected_rationale=[
                self._explain_artifact_selection(artifact, job_context)
                for artifact in selected
            ],
            rejected_rationale=[
                self._explain_artifact_rejection(artifact, job_context)
                for artifact in rejected[:5]  # Top 5 rejected
            ],
            diversity_analysis=self._analyze_portfolio_diversity(selected),
            missing_skills=self._identify_missing_skills(selected, job_context),
            overall_strategy=self._describe_selection_strategy(selected, job_context)
        )

    def _explain_artifact_selection(
        self,
        artifact: RankedArtifact,
        job_context: JobContext
    ) -> str:
        """Generate explanation for why artifact was selected"""

        reasons = []

        # Vector similarity reasoning
        if artifact.vector_similarity > 0.8:
            reasons.append(f"Very relevant to {job_context.role_title} role (similarity: {artifact.vector_similarity:.1%})")
        elif artifact.vector_similarity > 0.6:
            reasons.append(f"Good match for {job_context.role_title} requirements")

        # Skill matching reasoning
        matching_skills = set(artifact.technologies) & set(job_context.required_skills)
        if matching_skills:
            reasons.append(f"Contains required skills: {', '.join(list(matching_skills)[:3])}")

        # Role level reasoning
        if artifact.role_alignment > 0.8:
            reasons.append(f"Appropriate for {job_context.seniority_level} level position")

        return "; ".join(reasons)
```

## Test & Eval Plan

### Unit Tests
- Multi-factor scoring algorithm with known inputs and expected outputs
- Diversity filtering logic with various artifact portfolios
- Vector similarity calculations using pgvector
- Cache hit/miss scenarios for performance optimization
- Selection explanation generation accuracy

### Integration Tests
- End-to-end selection with real user portfolios (10-50 artifacts)
- Performance testing with 100+ artifacts per user
- Concurrent selection requests from multiple users
- Database query optimization and index usage validation
- A/B testing framework integration

### Performance Benchmarks
**Selection Speed:**
- P95 selection time ≤5 seconds for portfolios up to 100 artifacts
- P99 selection time ≤10 seconds under normal load
- Support 100 concurrent selections without degradation
- Database query count ≤10 per selection operation

**Selection Quality:**
- User retention rate ≥80% for selected artifacts
- User satisfaction rating ≥8/10 for selection relevance
- Override rate ≤20% (users manually changing selections)
- Diversity score ≥0.7 (balanced technology and domain distribution)

### Golden Test Cases
```python
# Test case: Senior Full-Stack Developer with diverse portfolio
test_user_portfolio = [
    {"tech": ["React", "Node.js"], "domain": "E-commerce", "level": "senior"},
    {"tech": ["Python", "Django"], "domain": "Healthcare", "level": "mid"},
    {"tech": ["React", "TypeScript"], "domain": "Finance", "level": "senior"},
    {"tech": ["Vue.js", "Express"], "domain": "E-commerce", "level": "junior"},
    {"tech": ["Python", "FastAPI"], "domain": "AI/ML", "level": "senior"},
    # ... 15 more artifacts
]

target_job = {
    "title": "Senior Full-Stack Developer",
    "required_skills": ["React", "Node.js", "TypeScript", "Python"],
    "domain": "Fintech",
    "seniority": "senior"
}

expected_selection_criteria = {
    "selected_count": 8,
    "react_artifacts": 2,  # Max 25% overlap
    "senior_level_artifacts": 6,  # 75% appropriate level
    "diversity_domains": 3,  # At least 3 different domains
    "required_skill_coverage": 0.9  # 90% of required skills covered
}
```

### A/B Testing Framework
```python
AB_TEST_CONFIGS = {
    "selection_algorithm_v1_vs_v2": {
        "control": {
            "algorithm": "multi_factor_v1",
            "weights": {"similarity": 0.5, "skills": 0.25, "level": 0.25}
        },
        "experiment": {
            "algorithm": "enhanced_diversity_v2",
            "weights": {"similarity": 0.4, "skills": 0.3, "level": 0.2, "diversity": 0.1}
        },
        "traffic_split": 0.2,
        "success_metrics": ["user_retention_rate", "satisfaction_rating", "override_rate"]
    }
}
```

## Telemetry & Metrics

### Selection Performance
**Dashboards:**
- Selection success rate and duration distribution
- User artifact retention rates by algorithm version
- Override frequency and patterns analysis
- Portfolio diversity scores and technology distribution

**Key Metrics:**
- Average selection time: target ≤3 seconds (P50), ≤5 seconds (P95)
- User satisfaction: target ≥8/10 average rating
- Artifact retention: target ≥80% of selected artifacts kept by users
- Override rate: target ≤20% of selections manually modified

### Algorithm Performance
```python
# Prometheus metrics
selection_duration = Histogram(
    'artifact_selection_duration_seconds',
    'Time to select artifacts',
    ['algorithm_version', 'portfolio_size_bucket']
)

user_satisfaction = Histogram(
    'artifact_selection_satisfaction_score',
    'User satisfaction with selections',
    ['job_category', 'portfolio_size_bucket']
)

artifact_retention_rate = Histogram(
    'artifact_retention_rate',
    'Percentage of selected artifacts kept by users',
    ['algorithm_version', 'selection_size']
)
```

### Quality Metrics
- Selection diversity scores (technology and domain distribution)
- Skill coverage completeness vs job requirements
- Role level appropriateness accuracy
- Cache hit rates for performance optimization

**Alerts:**
- Selection success rate <95% (P1 alert)
- Average selection time >5 seconds (P2 alert)
- User satisfaction <7/10 (P2 alert)
- Override rate >30% (P1 alert)

## Edge Cases & Risks

### Portfolio Size Variations
**Risk:** Users with very few artifacts (≤5) don't get optimal selection
**Mitigation:** Return all artifacts with quality scoring, provide guidance for portfolio expansion

**Risk:** Users with very large portfolios (100+) experience slow selection
**Mitigation:** Efficient vector pre-filtering, pagination, background caching of frequent job types

### Data Quality Issues
**Risk:** Poor quality preprocessed artifacts lead to bad selections
**Mitigation:** Quality scoring integration, fallback to user-provided descriptions, confidence thresholds

**Risk:** Outdated or irrelevant artifacts selected for modern roles
**Mitigation:** Recency weighting, technology relevance scoring, user feedback integration

### Algorithm Fairness
**Risk:** Algorithm bias towards certain types of artifacts or technologies
**Mitigation:** Fairness testing across different user demographics, bias detection metrics

**Risk:** Over-optimization for specific job categories at expense of others
**Mitigation:** Cross-category performance monitoring, balanced training data

### System Reliability
**Risk:** Vector database performance degradation under load
**Mitigation:** Read replicas, query result caching, graceful degradation to simpler algorithms

**Risk:** Selection cache invalidation causing performance issues
**Mitigation:** Smart cache warming, incremental updates, cache hit rate monitoring

### User Experience
**Risk:** Users don't understand why certain artifacts were selected/rejected
**Mitigation:** Detailed selection explanations, educational tooltips, transparency in algorithm logic

**Risk:** Algorithm selections consistently poor for specific user types
**Mitigation:** User feedback loops, personalization learning, manual override analytics