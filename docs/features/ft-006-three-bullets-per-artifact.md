# Feature — 006 three-bullets-per-artifact

**File:** docs/features/ft-006-three-bullets-per-artifact.md
**Owner:** ML/Backend Team
**TECH-SPECs:** `spec-api.md` (v2.0), `spec-llm.md` (v1.0), `spec-frontend.md` (v2.0)
**Related ADRs:** [ADR-016-three-bullets-per-artifact](../adrs/adr-016-three-bullets-per-artifact.md)

## Existing Implementation Analysis

**Similar Features:**
- `generation/services/bullet_generation_service.py` - Existing bullet generation logic (613 lines)
- `generation/services/bullet_validation_service.py` - Multi-criteria quality validation (495 lines)
- `llm_services/services/core/tailored_content_service.py` - LLM-based content generation pattern

**Reusable Components:**
- `llm_services/services/reliability/circuit_breaker.py` - For LLM API fault tolerance
- `llm_services/services/infrastructure/model_selector.py` - Model selection with fallbacks
- `llm_services/services/base/task_executor.py` - Retry logic and timeout handling
- `generation/models.py` - BulletPoint and BulletGenerationJob models already exist

**Patterns to Follow:**
- Service layer pattern: Following llm_services architecture (base → core → infrastructure → reliability)
- Extracted business logic from views into service classes (ADR-018)
- Retry logic with exponential backoff from task_executor
- Quality validation pipeline with multi-criteria scoring

**Code Already Implemented:**
- ✅ BulletPoint model with structured hierarchy
- ✅ BulletGenerationJob for tracking generation requests
- ✅ Service layer extracted from views (ft-006 completed)
- ✅ Validation logic with quality scoring

**Dependencies:**
- `llm_services.services.base.TaskExecutor` (retry logic)
- `llm_services.services.reliability.CircuitBreaker` (API fault tolerance)
- `llm_services.services.infrastructure.ModelSelector` (model selection)
- `generation.models.BulletPoint` (data model)
- `generation.models.BulletGenerationJob` (job tracking)

## Architecture Conformance

**Layer Assignment:**
- New services in `generation/services/` (business logic layer)
  - `bullet_generation_service.py` - Orchestration with retry logic (613 lines)
  - `bullet_validation_service.py` - Quality validation (495 lines)
- API endpoints in `generation/views.py` (interface layer)
- Models in `generation/models.py` (data layer)

**Pattern Compliance:**
- ✅ Follows service layer extraction pattern (ADR-018)
- ✅ Uses circuit breaker for external LLM calls
- ✅ Implements retry logic via task executor pattern
- ✅ Multi-criteria validation following llm_services patterns
- ✅ Async processing via Celery for long-running operations

**Dependencies:**
- `llm_services.services.base.BaseService` (inheritance for service classes)
- `llm_services.services.reliability.CircuitBreaker` (composition for API calls)
- `llm_services.services.infrastructure.ModelSelector` (composition for model selection)
- `generation.models.BulletPoint` (data access)
- `generation.models.BulletGenerationJob` (job tracking)

**Test Coverage:**
- 89.6% coverage in generation/ app
- Unit tests for service logic
- Integration tests for end-to-end flows

## Acceptance Criteria

- [ ] CV generation produces exactly 3 bullet points per selected artifact
- [ ] Bullet points follow structured hierarchy: Primary achievement, Technical detail, Impact/Results
- [ ] Each bullet point is 60-150 characters for optimal readability
- [ ] LLM generation consistently returns exactly 3 bullets (≥95% success rate)
- [ ] Validation prevents generic/padded content with quality scoring
- [ ] Bullet points are non-redundant (≤80% semantic similarity between bullets)
- [ ] Generation includes structured metadata (type, keywords, confidence)
- [ ] Failed generation attempts provide meaningful error messages
- [ ] Template system supports consistent formatting across CV formats
- [ ] User can preview and approve generated bullets before final CV creation
- [ ] Bullets are optimized for ATS parsing with relevant keywords
- [ ] Quality metrics track user satisfaction and content relevance

## Design Changes

### API Endpoints
**New endpoints:**
```python
# Bullet generation
POST /api/v1/cv/artifacts/{id}/generate-bullets/  # Generate 3 bullets
GET /api/v1/cv/artifacts/{id}/bullets/preview/    # Preview generated bullets
POST /api/v1/cv/artifacts/{id}/bullets/approve/   # Approve bullets
POST /api/v1/cv/bullets/batch-generate/           # Generate for multiple artifacts

# Quality validation
POST /api/v1/cv/bullets/validate/                 # Validate bullet quality
POST /api/v1/cv/bullets/feedback/                 # User quality feedback
```

### Data Models
```python
class BulletPoint(models.Model):
    """Individual bullet point with metadata"""
    artifact = models.ForeignKey('Artifact', on_delete=models.CASCADE)
    cv_generation = models.ForeignKey('CVGeneration', on_delete=models.CASCADE)
    position = models.IntegerField()  # 1, 2, or 3
    text = models.CharField(max_length=150)
    bullet_type = models.CharField(
        max_length=20,
        choices=[
            ('achievement', 'Primary Achievement'),
            ('technical', 'Technical Detail'),
            ('impact', 'Impact/Results')
        ]
    )
    keywords = models.JSONField(default=list)  # ATS keywords
    metrics = models.JSONField(default=dict)   # Quantified data
    confidence_score = models.FloatField()
    user_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class BulletGenerationJob(models.Model):
    """Track bullet generation requests"""
    artifact = models.ForeignKey('Artifact', on_delete=models.CASCADE)
    job_context = models.JSONField()  # Job requirements, keywords
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('needs_review', 'Needs Review')
        ]
    )
    generation_attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    processing_duration = models.IntegerField()  # milliseconds
```

### UI Changes
**CV Generation Interface:**
- Three-bullet preview cards with structured layout
- Quality indicators for each bullet (confidence scores, keyword matches)
- Edit/approve interface for individual bullets
- Regeneration option with refined prompts

**New Components:**
- `<BulletPointCard />` - Individual bullet display with metadata
- `<ThreeBulletLayout />` - Structured three-bullet container
- `<BulletQualityIndicator />` - Visual quality scoring
- `<BulletEditModal />` - In-line editing interface

### Validation System
```python
class BulletPointValidator:
    """Comprehensive bullet point validation"""

    def validate_three_bullet_structure(self, bullets: List[BulletPoint]) -> ValidationResult:
        """Ensure exactly 3 bullets with proper structure"""
        if len(bullets) != 3:
            return ValidationResult(False, f"Expected 3 bullets, got {len(bullets)}")

        # Validate bullet hierarchy
        expected_types = ['achievement', 'technical', 'impact']
        for i, bullet in enumerate(bullets):
            if bullet.bullet_type != expected_types[i]:
                return ValidationResult(False, f"Bullet {i+1} should be {expected_types[i]}")

        return ValidationResult(True, "Structure valid")

    def validate_content_quality(self, bullet: BulletPoint) -> float:
        """Score bullet quality (0-1)"""
        score = 0.0

        # Length validation (0.2 weight)
        if 40 <= len(bullet.text) <= 150:
            score += 0.2

        # Action verb check (0.2 weight)
        if self._starts_with_action_verb(bullet.text):
            score += 0.2

        # Quantified metrics (0.3 weight)
        if bullet.metrics or self._contains_numbers(bullet.text):
            score += 0.3

        # Keyword relevance (0.2 weight)
        score += self._calculate_keyword_score(bullet) * 0.2

        # Generic content penalty (0.1 weight)
        if not self._is_generic_content(bullet.text):
            score += 0.1

        return min(score, 1.0)
```

## Test & Eval Plan

### Unit Tests
- Bullet point generation with various artifact types and job contexts
- Validation logic for three-bullet structure and content quality
- Semantic similarity detection for redundancy prevention
- Content hierarchy enforcement (achievement → technical → impact)
- Error handling for malformed LLM responses

### Integration Tests
- End-to-end bullet generation from artifact selection to final approval
- Multi-artifact bullet generation consistency
- User feedback integration and quality score updates
- ATS keyword optimization validation
- Template rendering with generated bullets

### AI Evaluation Metrics
**Generation Quality:**
- Exactly 3 bullets produced: ≥95% success rate
- User satisfaction rating: ≥8/10 for bullet relevance and quality
- Content hierarchy adherence: ≥90% proper structure (achievement/technical/impact)
- Keyword optimization score: ≥0.7 average ATS relevance

**Content Standards:**
- Generic content rate: ≤5% of bullets flagged as generic
- Redundancy rate: ≤10% of bullet sets with high similarity (>80%)
- Length compliance: ≥95% of bullets within 40-150 character range
- Action verb usage: ≥90% of bullets start with strong action verbs

### Golden Test Cases
```python
# Test case: Senior Software Engineer position
test_artifact = {
    "title": "E-commerce Platform Development",
    "description": "Led team developing microservices architecture",
    "technologies": ["React", "Node.js", "AWS", "PostgreSQL"],
    "achievements": ["Increased performance by 40%", "Managed team of 6"]
}

expected_bullets = [
    {
        "type": "achievement",
        "text": "Led development of microservices platform serving 100k+ daily users with 99.9% uptime",
        "keywords": ["microservices", "platform", "led", "development"]
    },
    {
        "type": "technical",
        "text": "Built scalable architecture using React, Node.js, and AWS with PostgreSQL database",
        "keywords": ["React", "Node.js", "AWS", "PostgreSQL", "architecture"]
    },
    {
        "type": "impact",
        "text": "Improved system performance by 40% while managing cross-functional team of 6 engineers",
        "keywords": ["performance", "improvement", "team management"]
    }
]
```

### A/B Testing Framework
- Compare 3-bullet vs variable bullet count (2-5) for user preference
- Test different bullet hierarchy orders for effectiveness
- Evaluate structured vs unstructured bullet generation prompts
- Measure ATS parsing success rates across different bullet formats

## Telemetry & Metrics

### Generation Performance
**Dashboards:**
- Bullet generation success rate (target ≥95%)
- Average generation time per artifact (target ≤10 seconds)
- User approval rate for generated bullets (target ≥80%)
- Regeneration request frequency (target ≤15%)

**Quality Metrics:**
- Content quality score distribution (target median ≥0.8)
- Keyword relevance scores by job category
- User satisfaction ratings (target ≥8/10)
- Generic content detection rate (target ≤5%)

### System Reliability
**Alerts:**
- Generation success rate <90% (P1 alert)
- Average quality score <0.7 (P2 alert)
- User approval rate <70% (P2 alert)
- Generation timeout rate >5% (P1 alert)

### Usage Analytics
```python
# Tracking metrics
bullet_generation_duration = Histogram(
    'bullet_generation_duration_seconds',
    'Time to generate 3 bullets',
    ['artifact_type', 'job_category']
)

bullet_quality_score = Histogram(
    'bullet_quality_score',
    'Quality scores for generated bullets',
    ['position', 'bullet_type']
)

user_approval_rate = Counter(
    'bullet_user_actions_total',
    'User actions on generated bullets',
    ['action']  # approved, edited, regenerated, rejected
)
```

## Edge Cases & Risks

### Generation Failures
**Risk:** LLM returns fewer or more than 3 bullets
**Mitigation:** Strict prompt constraints, response validation, automatic regeneration up to 3 attempts

**Risk:** Generated bullets are too generic or repetitive
**Mitigation:** Content quality scoring, semantic similarity detection, user feedback training

**Risk:** Bullets exceed character limits or are too short
**Mitigation:** Length validation in prompts, automatic truncation/expansion with user approval

### Content Quality Issues
**Risk:** Bullets lack quantified achievements or metrics
**Mitigation:** Enhanced prompts emphasizing metrics, artifact preprocessing to extract quantified data

**Risk:** Poor keyword optimization for ATS systems
**Mitigation:** Job-specific keyword injection, ATS testing framework, keyword relevance scoring

### User Experience Concerns
**Risk:** Users consistently reject generated bullets
**Mitigation:** A/B testing different generation approaches, user feedback integration, manual override options

**Risk:** Bullets don't reflect artifact's true value
**Mitigation:** Improved artifact preprocessing, user validation workflow, evidence linking

### System Performance
**Risk:** Generation timeouts during peak usage
**Mitigation:** Async processing, queue management, caching frequently generated patterns

**Risk:** LLM API rate limits affecting generation speed
**Mitigation:** Multiple provider fallbacks, request batching, intelligent retry mechanisms