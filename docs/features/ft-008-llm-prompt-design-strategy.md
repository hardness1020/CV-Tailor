# Feature — 008 llm-prompt-design-strategy

**File:** docs/features/ft-008-llm-prompt-design-strategy.md
**Owner:** ML/Backend Team
**TECH-SPECs:** `spec-api.md` (v2.0), `spec-llm.md` (v1.0)
**Related ADRs:** [ADR-014-llm-prompt-design-strategy](../adrs/adr-014-llm-prompt-design-strategy.md)

## Existing Implementation Analysis

**Similar Features:**
- `llm_services/services/core/tailored_content_service.py` - Existing prompt-based content generation
- `generation/services/bullet_generation_service.py` - Bullet generation with prompts (613 lines)
- `llm_services/services/base/task_executor.py` - Retry and timeout patterns for LLM calls

**Reusable Components:**
- `llm_services/services/infrastructure/model_registry.py` - Model configurations and metadata
- `llm_services/services/infrastructure/model_selector.py` - Model selection with fallbacks
- `llm_services/services/reliability/performance_tracker.py` - Cost and latency tracking
- `llm_services/services/base/task_executor.py` - Retry logic with exponential backoff

**Patterns to Follow:**
- Template-based prompt management from tailored_content_service
- Version control for prompts (A/B testing capability)
- Performance tracking and cost monitoring
- Circuit breaker for API fault tolerance
- Few-shot learning with dynamic example selection

**Code to Refactor:**
- Consolidate prompt templates into centralized prompt registry
- Extract prompt rendering logic into dedicated service

**Dependencies:**
- `llm_services.services.core.TailoredContentService` (prompt patterns)
- `llm_services.services.infrastructure.ModelSelector` (model selection)
- `llm_services.services.reliability.CircuitBreaker` (API fault tolerance)
- `llm_services.services.reliability.PerformanceTracker` (cost/latency monitoring)

## Architecture Conformance

**Layer Assignment:**
- Prompt templates in `llm_services/prompts/` (configuration layer)
- Prompt rendering service in `llm_services/services/core/prompt_service.py` (core layer)
- Template management in `llm_services/services/infrastructure/prompt_registry.py` (infrastructure layer)

**Pattern Compliance:**
- ✅ Follows llm_services layered architecture
- ✅ Version-controlled templates for A/B testing
- ✅ Performance tracking built-in
- ✅ Circuit breaker for resilience
- ✅ Few-shot learning with dynamic examples

**Dependencies:**
- `llm_services.services.base.BaseService` (inheritance)
- `llm_services.services.infrastructure.ModelSelector` (composition)
- `llm_services.services.reliability.CircuitBreaker` (composition)
- `llm_services.services.reliability.PerformanceTracker` (composition)
- Template engine (Jinja2 or similar)

## Acceptance Criteria

- [ ] Structured template-based prompting system consistently generates high-quality bullet points
- [ ] Prompts include dynamic few-shot examples selected based on artifact and job context
- [ ] Template system supports role-specific enhancements (technical, management, startup contexts)
- [ ] Prompt token usage optimized to ≤4000 tokens per request while maintaining quality
- [ ] JSON response parsing with fallback handling for malformed LLM outputs
- [ ] Version-controlled prompt templates enable A/B testing and rollback capabilities
- [ ] Multi-source evidence integration in prompts (GitHub, documents, presentations)
- [ ] Response validation ensures exactly 3 bullets with proper structure and metadata
- [ ] Template rendering performance ≤500ms for prompt assembly
- [ ] Error recovery mechanisms handle LLM failures gracefully
- [ ] Prompt effectiveness measured through quality scores and user satisfaction
- [ ] Examples database maintained with high-quality bullet point samples

## Design Changes

### Prompt Template System
**New template architecture:**
```python
# Base prompt structure
BULLET_GENERATION_TEMPLATE = """
TASK: Generate exactly 3 professional CV bullet points for the given artifact, optimized for the target job role.

CONTEXT:
Job Role: {{job_context.role_title}}
Company: {{job_context.company_name}}
Key Requirements: {{job_context.key_requirements|join(", ")}}
Priority Keywords: {{job_context.priority_keywords|join(", ")}}

ARTIFACT:
Title: {{artifact.title}}
Description: {{artifact.description}}
Technologies: {{artifact.technologies|join(", ")}}
Timeline: {{artifact.start_date}} - {{artifact.end_date}}

MULTI-SOURCE EVIDENCE:
{% if artifact.github_analysis %}
GitHub Code ({{artifact.github_analysis.total_repos}} repos):
- Languages: {{artifact.github_analysis.languages|join(", ")}}
- Project Scale: {{artifact.github_analysis.lines_of_code}} LOC
- Commit Activity: {{artifact.github_analysis.commit_count}} commits
{% endif %}

{% if artifact.document_insights %}
Documentation ({{artifact.document_insights.total_documents}} docs):
- Types: {{artifact.document_insights.document_types|join(", ")}}
- Key Achievements: {{artifact.document_insights.achievements|join("; ")}}
{% endif %}

{% if artifact.media_insights %}
Presentations/Demos ({{artifact.media_insights.total_files}} files):
- {{artifact.media_insights.presentations|length}} presentations
- {{artifact.media_insights.demos|length}} demos
{% endif %}

ROLE-SPECIFIC ENHANCEMENT:
{{role_enhancement}}

EXAMPLES:
{{examples}}

OUTPUT FORMAT (JSON):
{
  "bullet_points": [
    {
      "text": "Action verb + specific achievement + quantified impact",
      "type": "achievement|technical|impact",
      "keywords": ["relevant", "keywords"],
      "metrics": {"type": "value"},
      "confidence_score": 0.0-1.0
    }
  ],
  "generation_metadata": {
    "primary_focus": "brief description",
    "keyword_matches": ["matched", "keywords"],
    "difficulty_level": "simple|moderate|complex"
  }
}
"""

# Role-specific enhancements
ROLE_ENHANCEMENTS = {
    "technical": """
TECHNICAL FOCUS:
- Emphasize specific technologies, frameworks, methodologies
- Include system scale, performance metrics, technical complexity
- Highlight problem-solving and optimization achievements
- Focus on technical leadership and architecture decisions
""",
    "management": """
LEADERSHIP FOCUS:
- Emphasize team size, budget responsibility, stakeholder management
- Include project scope, timeline achievements, business impact
- Highlight strategic decision-making and process improvements
- Focus on cross-functional collaboration and communication
""",
    "startup": """
STARTUP ENVIRONMENT FOCUS:
- Emphasize versatility, rapid execution, scrappy problem-solving
- Include growth metrics, user acquisition, scaling challenges
- Highlight ownership, initiative, wearing multiple hats
- Focus on direct business impact and revenue contribution
"""
}
```

### Dynamic Example Selection
```python
class ExampleDatabase:
    """Curated examples for few-shot learning"""

    def __init__(self):
        self.examples = {
            "technical": {
                "react": [
                    {
                        "artifact_type": "frontend_project",
                        "context": "Senior Frontend Developer",
                        "bullets": [
                            "Developed responsive React dashboard serving 50k+ daily users with 99.9% uptime",
                            "Implemented component library using TypeScript and Storybook, reducing development time by 30%",
                            "Optimized bundle size by 40% through code splitting and lazy loading strategies"
                        ]
                    }
                ],
                "backend": [
                    {
                        "artifact_type": "api_project",
                        "context": "Senior Backend Engineer",
                        "bullets": [
                            "Built scalable microservices architecture handling 1M+ API requests daily",
                            "Designed event-driven system using Kafka and Redis for real-time data processing",
                            "Reduced database query time by 60% through optimization and caching strategies"
                        ]
                    }
                ],
                "fullstack": [
                    {
                        "artifact_type": "fullstack_project",
                        "context": "Full-Stack Developer",
                        "bullets": [
                            "Led end-to-end development of e-commerce platform generating $2M+ annual revenue",
                            "Integrated React frontend with Node.js backend and PostgreSQL database architecture",
                            "Implemented automated CI/CD pipeline reducing deployment time from 2 hours to 15 minutes"
                        ]
                    }
                ]
            },
            "management": {
                "team_lead": [
                    {
                        "artifact_type": "leadership_project",
                        "context": "Engineering Manager",
                        "bullets": [
                            "Managed cross-functional team of 12 engineers delivering platform used by 100k+ users",
                            "Established agile development processes reducing delivery time by 35%",
                            "Mentored 5 junior developers resulting in 100% retention and 3 promotions"
                        ]
                    }
                ]
            }
        }

    def select_relevant_examples(
        self,
        artifact: Artifact,
        job_context: JobContext,
        count: int = 2
    ) -> List[Dict]:
        """Select most relevant examples for given context"""

        # Match by technology stack
        tech_matches = self._find_examples_by_technology(
            artifact.technologies, job_context.role_category
        )

        # Match by role level and type
        role_matches = self._find_examples_by_role(
            job_context.role_title, job_context.seniority_level
        )

        # Combine and rank by relevance
        all_examples = tech_matches + role_matches
        ranked_examples = self._rank_examples(all_examples, artifact, job_context)

        return ranked_examples[:count]
```

### Template Management System
```python
class PromptTemplateManager:
    """Version-controlled prompt template system"""

    def __init__(self):
        self.template_versions = {}
        self.active_experiments = {}
        self.template_performance = {}

    def register_template_version(
        self,
        template_name: str,
        version: str,
        template_content: str,
        metadata: Dict = None
    ) -> None:
        """Register new template version for A/B testing"""

        template_key = (template_name, version)
        self.template_versions[template_key] = {
            "content": template_content,
            "metadata": metadata or {},
            "created_at": datetime.now(),
            "active": False
        }

    def get_template_for_request(
        self,
        template_name: str,
        user_id: str,
        artifact_context: Dict
    ) -> Tuple[str, str]:
        """Get template version based on A/B test assignment"""

        # Check if user is in A/B test
        experiment_config = self.active_experiments.get(template_name)
        if experiment_config:
            version = self._assign_ab_test_version(user_id, experiment_config)
        else:
            version = self._get_default_version(template_name)

        template_key = (template_name, version)
        template_data = self.template_versions[template_key]

        return template_data["content"], version

    def track_template_performance(
        self,
        template_name: str,
        version: str,
        performance_metrics: Dict
    ) -> None:
        """Track template performance for optimization"""

        key = (template_name, version)
        if key not in self.template_performance:
            self.template_performance[key] = []

        self.template_performance[key].append({
            "metrics": performance_metrics,
            "timestamp": datetime.now()
        })
```

### Response Validation System
```python
class BulletResponseValidator:
    """Comprehensive response validation and error recovery"""

    def __init__(self):
        self.validation_schema = {
            "bullet_points": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["text", "type", "confidence_score"],
                    "properties": {
                        "text": {"type": "string", "minLength": 40, "maxLength": 150},
                        "type": {"enum": ["achievement", "technical", "impact"]},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        }

    async def validate_and_parse_response(
        self,
        llm_response: str,
        artifact: Artifact,
        job_context: JobContext
    ) -> ValidationResult:
        """Validate LLM response with fallback parsing"""

        try:
            # Try JSON parsing first
            response_data = json.loads(llm_response.strip())
            validation_result = self._validate_json_structure(response_data)

            if validation_result.valid:
                # Additional content quality validation
                quality_scores = await self._validate_content_quality(
                    response_data["bullet_points"], artifact, job_context
                )
                return ValidationResult(
                    valid=True,
                    data=response_data,
                    quality_scores=quality_scores
                )

        except json.JSONDecodeError:
            # Fallback: extract bullets from unstructured text
            extracted_bullets = await self._extract_bullets_from_text(llm_response)
            if len(extracted_bullets) == 3:
                return ValidationResult(
                    valid=True,
                    data={"bullet_points": extracted_bullets},
                    fallback_parsing=True
                )

        # If all validation fails, attempt correction
        return await self._attempt_response_correction(
            llm_response, artifact, job_context
        )

    async def _validate_content_quality(
        self,
        bullets: List[Dict],
        artifact: Artifact,
        job_context: JobContext
    ) -> List[float]:
        """Validate bullet point content quality"""

        quality_scores = []
        for bullet in bullets:
            score = 0.0

            # Length validation (0.2 weight)
            text_length = len(bullet["text"])
            if 40 <= text_length <= 150:
                score += 0.2

            # Action verb validation (0.2 weight)
            if self._starts_with_action_verb(bullet["text"]):
                score += 0.2

            # Keyword relevance (0.3 weight)
            keyword_score = self._calculate_keyword_relevance(
                bullet["text"], job_context.priority_keywords
            )
            score += keyword_score * 0.3

            # Specificity check (0.2 weight)
            if self._contains_specific_details(bullet["text"]):
                score += 0.2

            # Generic content penalty (0.1 weight)
            if not self._is_generic_content(bullet["text"]):
                score += 0.1

            quality_scores.append(min(score, 1.0))

        return quality_scores
```

## Test & Eval Plan

### Unit Tests
- Template rendering with various artifact and job contexts
- Example selection algorithm accuracy and relevance
- JSON response parsing and validation logic
- Fallback parsing for malformed responses
- Performance testing for prompt assembly speed

### Integration Tests
- End-to-end bullet generation with real LLM APIs
- A/B testing framework integration and user assignment
- Template version management and rollback procedures
- Multi-source evidence integration accuracy
- Error recovery mechanisms under various failure scenarios

### AI Evaluation Metrics
**Prompt Effectiveness:**
- Generation success rate: ≥95% for structured JSON responses
- Content quality score: ≥0.8 average across all bullets
- User satisfaction rating: ≥8/10 for generated bullet relevance
- Token efficiency: ≤4000 tokens average per generation request

**Template Performance:**
- Response parsing success: ≥98% without fallback parsing needed
- Template rendering speed: ≤500ms for complex artifacts
- A/B test statistical significance within 1000 samples
- Example relevance score: ≥0.7 for selected few-shot examples

### Golden Test Cases
```python
# Test case: Senior Software Engineer with complex project
test_prompt_input = {
    "artifact": {
        "title": "Microservices E-commerce Platform",
        "technologies": ["React", "Node.js", "PostgreSQL", "AWS", "Docker"],
        "github_analysis": {
            "total_repos": 5,
            "languages": ["JavaScript", "TypeScript", "Python"],
            "lines_of_code": 50000,
            "commit_count": 2500
        },
        "document_insights": {
            "achievements": ["40% performance improvement", "99.9% uptime"],
            "document_types": ["technical_spec", "deployment_guide"]
        }
    },
    "job_context": {
        "role_title": "Senior Full-Stack Developer",
        "required_skills": ["React", "Node.js", "PostgreSQL", "AWS"],
        "priority_keywords": ["microservices", "scalability", "performance"]
    }
}

expected_response_quality = {
    "bullet_count": 3,
    "avg_quality_score": 0.85,
    "keyword_coverage": 0.8,  # 80% of priority keywords included
    "structure_compliance": 1.0,  # Perfect structure adherence
    "token_usage": 3500  # Under 4000 token limit
}
```

### A/B Testing Framework
```python
AB_EXPERIMENTS = {
    "enhanced_examples_vs_basic": {
        "control": {
            "template": "basic_structured_template_v1",
            "examples_count": 1,
            "role_enhancement": False
        },
        "experiment": {
            "template": "enhanced_examples_template_v2",
            "examples_count": 2,
            "role_enhancement": True
        },
        "traffic_split": 0.3,
        "success_metrics": [
            "user_satisfaction_rating",
            "content_quality_score",
            "generation_success_rate",
            "token_efficiency"
        ],
        "sample_size": 1000
    }
}
```

## Telemetry & Metrics

### Prompt Performance
**Dashboards:**
- Generation success rates by template version and artifact type
- Average response quality scores and distribution
- Token usage optimization trends and cost analysis
- Template rendering performance and bottlenecks

**Key Metrics:**
- Prompt assembly time: target ≤500ms (P95)
- LLM response time: target ≤8 seconds (P95)
- JSON parsing success: target ≥98%
- Content quality score: target ≥0.8 average

### Template Analytics
```python
# Prometheus metrics
prompt_generation_duration = Histogram(
    'prompt_generation_duration_seconds',
    'Time to assemble prompts',
    ['template_version', 'artifact_complexity']
)

llm_response_quality = Histogram(
    'llm_response_quality_score',
    'Quality scores for generated content',
    ['template_version', 'job_category']
)

token_usage = Histogram(
    'prompt_token_usage_total',
    'Total tokens used per generation request',
    ['template_version', 'evidence_sources']
)
```

### Quality Monitoring
- User satisfaction ratings for generated bullets
- Content quality score distributions by template version
- Keyword relevance and ATS optimization effectiveness
- A/B test performance comparison and statistical significance

**Alerts:**
- Generation success rate <90% (P1 alert)
- Average quality score <0.7 (P2 alert)
- Token usage >4500 average (P2 alert)
- Template rendering time >1 second (P1 alert)

## Edge Cases & Risks

### Template Management
**Risk:** Template updates break existing generation workflows
**Mitigation:** Version control with gradual rollout, automated regression testing, quick rollback capabilities

**Risk:** A/B test results inconclusive due to small sample sizes
**Mitigation:** Statistical power analysis, adaptive sample size adjustment, confidence interval monitoring

### LLM Response Quality
**Risk:** LLM generates malformed JSON responses frequently
**Mitigation:** Robust fallback parsing, response correction prompts, multiple provider fallbacks

**Risk:** Generated bullets consistently poor quality for specific domains
**Mitigation:** Domain-specific example curation, specialized template variants, user feedback integration

### Performance Issues
**Risk:** Prompt assembly becomes bottleneck under high load
**Mitigation:** Template caching, async processing, performance profiling and optimization

**Risk:** Token costs escalate due to prompt bloat
**Mitigation:** Token counting validation, prompt compression techniques, cost monitoring alerts

### Content Accuracy
**Risk:** Multi-source evidence integration creates contradictory information
**Mitigation:** Evidence source reliability scoring, conflict detection, source priority ranking

**Risk:** Examples database becomes outdated or biased
**Mitigation:** Regular example auditing, diversity validation, user contribution system

### System Reliability
**Risk:** Template version conflicts during concurrent requests
**Mitigation:** Atomic template updates, request-level version locking, consistency validation

**Risk:** Example selection algorithm bias towards certain artifact types
**Mitigation:** Selection fairness testing, balanced example distribution, algorithmic bias detection