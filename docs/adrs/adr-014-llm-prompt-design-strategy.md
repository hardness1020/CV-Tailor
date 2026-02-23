# ADR — LLM Prompt Design Strategy for CV Generation

**Status:** Draft
**Date:** 2025-09-27
**Deciders:** Engineering, ML Team
**Technical Story:** Design optimal prompting strategy for generating 3 bullet points per artifact

## Context and Problem Statement

The CV generation system requires a prompting strategy that consistently produces high-quality, job-relevant bullet points. We need to decide between different prompting approaches that balance generation quality, consistency, processing speed, and token efficiency while ensuring ATS optimization and user satisfaction.

## Decision Drivers

- **Output Consistency:** Must reliably generate exactly 3 bullet points per artifact
- **Quality Standards:** Bullet points must be professional, specific, and achievement-focused
- **Token Efficiency:** Minimize LLM API costs while maintaining quality
- **Processing Speed:** Target ≤30 seconds per artifact for responsive UX
- **Job Relevance:** Bullet points must be tailored to specific job requirements
- **ATS Optimization:** Include relevant keywords for ATS parsing
- **Error Handling:** Graceful handling of malformed or insufficient LLM responses
- **Maintainability:** Prompts should be version-controlled and easily updated

## Considered Options

### Option A: Single Comprehensive Prompt
- **Approach:** One large prompt containing all context and requirements
- **Pros:** Simple implementation, single API call, all context available
- **Cons:** Large token usage, complex prompt management, harder to debug

### Option B: Multi-Step Prompting Chain
- **Approach:** Sequential prompts: analyze → extract → generate → optimize
- **Pros:** Better quality control, easier debugging, modular optimization
- **Cons:** Multiple API calls, increased latency, higher token costs

### Option C: Structured Template-Based Prompting (Recommended)
- **Approach:** Single prompt with structured templates and explicit constraints
- **Pros:** Balanced token usage, high consistency, maintainable, reliable output
- **Cons:** Requires careful template design, less flexible than multi-step

### Option D: Few-Shot Learning with Examples
- **Approach:** Include 3-5 high-quality examples in each prompt
- **Pros:** Better output quality, learns from examples, consistent style
- **Cons:** Higher token usage, requires curating quality examples

## Decision Outcome

**Chosen Option: Option C - Structured Template-Based Prompting with Few-Shot Enhancement**

### Rationale

1. **Optimal Balance:** Combines consistency of templates with quality of few-shot learning
2. **Token Efficiency:** More efficient than multi-step, includes selective examples
3. **Maintainable:** Template structure enables version control and A/B testing
4. **Reliable Output:** Structured constraints ensure consistent 3-bullet format
5. **Quality Assurance:** Examples guide LLM toward professional, achievement-focused content

### Prompt Architecture

```python
# Base Prompt Template Structure
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
{% if artifact.metrics %}
Quantified Results: {{artifact.metrics}}
{% endif %}
Timeline: {{artifact.start_date}} - {{artifact.end_date}}

MULTI-SOURCE EVIDENCE:
{% if artifact.github_analysis.total_repos > 0 %}
GitHub Code ({{artifact.github_analysis.total_repos}} repos):
- Languages: {{artifact.github_analysis.languages|join(", ")}}
- Project Scale: {{artifact.github_analysis.project_scale|length}} repos with size data
- Commit Activity: {{artifact.github_analysis.commit_activity|length}} active repos
{% endif %}

{% if artifact.document_insights.total_documents > 0 %}
Documentation ({{artifact.document_insights.total_documents}} docs):
- Types: {{artifact.document_insights.document_types|join(", ")}}
- Key Achievements: {{artifact.document_insights.achievements_mentioned|join("; ")}}
{% endif %}

{% if artifact.media_insights.total_media_files > 0 %}
Presentations/Demos ({{artifact.media_insights.total_media_files}} files):
- {{artifact.media_insights.presentations|length}} presentations
- {{artifact.media_insights.demos|length}} demos
- {{artifact.media_insights.interviews|length}} talks/interviews
{% endif %}

BULLET POINT REQUIREMENTS:
- Generate exactly 3 bullet points
- Length: 40-150 characters per bullet
- Start with strong action verbs (developed, implemented, optimized, led, etc.)
- Include quantified metrics when possible
- Emphasize job-relevant skills and technologies
- Use achievement-focused language (impact, results, improvements)
- Ensure ATS keyword optimization
- Avoid generic statements or redundancy
- Leverage multi-source evidence (GitHub code, documents, presentations) to demonstrate depth
- Prioritize concrete evidence from data sources over general descriptions

BULLET POINT STRUCTURE:
1. Primary Achievement: Most significant accomplishment or responsibility
2. Technical/Skills Detail: Technologies, methodologies, or skills demonstrated
3. Impact/Results: Quantified outcomes, improvements, or business value

EXAMPLES OF HIGH-QUALITY BULLET POINTS (leveraging multi-source evidence):
• Developed microservices architecture serving 2M+ users with 99.9% uptime using Node.js and AWS [GitHub: 5 repos, 2000+ commits]
• Implemented automated CI/CD pipeline reducing deployment time by 70% [PDF documentation + demo video evidence]
• Led cross-functional team of 8 engineers delivering feature 2 weeks ahead of schedule [presentation slides + GitHub collaboration data]

• Optimized database queries improving API response times by 45% [GitHub code changes + performance metrics from documents]
• Built React component library adopted by 12+ teams, reducing development time by 30% [GitHub package + usage documentation]
• Presented system architecture at 3 conferences reaching 500+ engineers [video recordings + conference papers]

OUTPUT FORMAT (JSON):
{
  "bullet_points": [
    {
      "text": "Action verb + specific achievement/responsibility + quantified impact/scope",
      "type": "achievement|responsibility|skill_demonstration",
      "keywords": ["relevant", "job", "keywords"],
      "metrics": {"type": "value", "improvement": "percentage"},
      "confidence_score": 0.0-1.0
    }
  ],
  "generation_metadata": {
    "primary_focus": "brief description of artifact's main value",
    "keyword_matches": ["matched", "keywords"],
    "difficulty_level": "simple|moderate|complex"
  }
}

GENERATE BULLET POINTS FOR THIS ARTIFACT:
"""

# Specialized Prompts for Different Scenarios
TECHNICAL_ROLE_ENHANCEMENT = """
TECHNICAL FOCUS AREAS:
- Emphasize specific technologies, frameworks, and methodologies
- Include system scale, performance metrics, and technical complexity
- Highlight problem-solving and optimization achievements
- Focus on technical leadership and architecture decisions
"""

MANAGEMENT_ROLE_ENHANCEMENT = """
LEADERSHIP FOCUS AREAS:
- Emphasize team size, budget responsibility, and stakeholder management
- Include project scope, timeline achievements, and business impact
- Highlight strategic decision-making and process improvements
- Focus on cross-functional collaboration and communication
"""

STARTUP_CONTEXT_ENHANCEMENT = """
STARTUP ENVIRONMENT FOCUS:
- Emphasize versatility, rapid execution, and scrappy problem-solving
- Include growth metrics, user acquisition, and scaling challenges
- Highlight ownership, initiative, and wearing multiple hats
- Focus on direct business impact and revenue contribution
"""
```

### Dynamic Prompt Assembly

```python
class BulletPointPromptBuilder:
    def __init__(self):
        self.base_template = Environment(loader=BaseLoader()).from_string(
            BULLET_GENERATION_TEMPLATE
        )
        self.role_enhancements = {
            "technical": TECHNICAL_ROLE_ENHANCEMENT,
            "management": MANAGEMENT_ROLE_ENHANCEMENT,
            "startup": STARTUP_CONTEXT_ENHANCEMENT
        }

    async def build_prompt(
        self,
        artifact: Artifact,
        job_context: JobContext
    ) -> str:
        """Build optimized prompt for specific artifact and job context"""

        # Determine role type for enhancement
        role_type = self._classify_role_type(job_context)

        # Select relevant examples based on role and artifact type
        examples = self._select_relevant_examples(artifact, job_context, count=2)

        # Build context with enhancements
        prompt_context = {
            "artifact": artifact,
            "job_context": job_context,
            "role_enhancement": self.role_enhancements.get(role_type, ""),
            "examples": examples,
            "priority_keywords": self._extract_priority_keywords(job_context)
        }

        return self.base_template.render(**prompt_context)

    def _select_relevant_examples(
        self,
        artifact: Artifact,
        job_context: JobContext,
        count: int = 2
    ) -> List[str]:
        """Select most relevant examples based on artifact and job context"""

        # Match examples by technology stack
        tech_matches = self._find_examples_by_tech(
            artifact.technologies, self.example_database
        )

        # Match examples by role type
        role_matches = self._find_examples_by_role(
            job_context.role_title, self.example_database
        )

        # Combine and rank examples
        all_matches = tech_matches + role_matches
        ranked_examples = self._rank_examples_by_relevance(
            all_matches, artifact, job_context
        )

        return ranked_examples[:count]

    async def _validate_prompt_length(self, prompt: str) -> bool:
        """Ensure prompt fits within token limits"""
        token_count = await self.tokenizer.count_tokens(prompt)

        # Reserve tokens for response (3 bullets × ~50 tokens = ~150 tokens)
        max_prompt_tokens = 4000 - 150  # For GPT-4 turbo

        if token_count > max_prompt_tokens:
            logger.warning(f"Prompt too long: {token_count} tokens")
            return False

        return True
```

### Response Parsing and Validation

```python
class BulletPointResponseParser:
    def __init__(self):
        self.bullet_schema = BulletPointSchema()

    async def parse_and_validate(
        self,
        llm_response: str,
        artifact: Artifact,
        job_context: JobContext
    ) -> ParsedBulletResponse:
        """Parse LLM response and validate bullet points"""

        try:
            # Parse JSON response
            response_data = json.loads(llm_response)
            bullet_points = response_data.get("bullet_points", [])

            # Validate structure
            if len(bullet_points) != 3:
                raise ValidationError(f"Expected 3 bullets, got {len(bullet_points)}")

            # Validate each bullet point
            validated_bullets = []
            for i, bullet_data in enumerate(bullet_points):
                validated_bullet = await self._validate_bullet_point(
                    bullet_data, artifact, job_context, position=i
                )
                validated_bullets.append(validated_bullet)

            return ParsedBulletResponse(
                bullet_points=validated_bullets,
                metadata=response_data.get("generation_metadata", {}),
                validation_score=self._calculate_validation_score(validated_bullets)
            )

        except json.JSONDecodeError as e:
            # Fallback: extract bullets from unstructured response
            return await self._extract_bullets_from_text(llm_response)

    async def _validate_bullet_point(
        self,
        bullet_data: Dict,
        artifact: Artifact,
        job_context: JobContext,
        position: int
    ) -> ValidatedBulletPoint:
        """Comprehensive bullet point validation"""

        bullet_text = bullet_data.get("text", "").strip()

        # Length validation
        if not (40 <= len(bullet_text) <= 150):
            raise ValidationError(f"Bullet {position + 1} length invalid: {len(bullet_text)}")

        # Action verb validation
        if not self._starts_with_action_verb(bullet_text):
            logger.warning(f"Bullet {position + 1} doesn't start with action verb")

        # Keyword relevance validation
        keyword_score = self._calculate_keyword_relevance(
            bullet_text, job_context.priority_keywords
        )

        # Content quality validation
        quality_score = self._assess_content_quality(bullet_text)

        return ValidatedBulletPoint(
            text=bullet_text,
            type=bullet_data.get("type", "responsibility"),
            keywords=bullet_data.get("keywords", []),
            metrics=bullet_data.get("metrics", {}),
            keyword_score=keyword_score,
            quality_score=quality_score,
            validation_passed=keyword_score >= 0.3 and quality_score >= 0.7
        )
```

## Positive Consequences

- **High Consistency:** Structured templates ensure reliable 3-bullet output
- **Quality Control:** Multiple validation layers ensure professional content
- **Token Efficiency:** Optimized prompts balance context with cost
- **Maintainability:** Template-based approach enables easy updates and A/B testing
- **Role Adaptation:** Dynamic enhancements tailor prompts to specific job types
- **Error Recovery:** Robust parsing handles malformed LLM responses

## Negative Consequences

- **Template Complexity:** Requires careful design and maintenance of prompt templates
- **Limited Creativity:** Structured approach may constrain LLM creativity
- **Example Curation:** Requires ongoing maintenance of high-quality example database
- **Validation Overhead:** Multiple validation steps add processing complexity

## Mitigation Strategies

### Template Management
```python
# Version-controlled prompt templates
class PromptVersionManager:
    def __init__(self):
        self.template_versions = {}
        self.active_versions = {}

    def register_template_version(
        self,
        template_name: str,
        version: str,
        template_content: str
    ):
        """Register new template version for A/B testing"""
        self.template_versions[(template_name, version)] = template_content

    async def get_template_for_user(
        self,
        template_name: str,
        user_id: str
    ) -> str:
        """Get template version based on user assignment"""
        # A/B test assignment logic
        version = await self._get_user_template_version(template_name, user_id)
        return self.template_versions[(template_name, version)]
```

### Fallback Strategies
- **Simple Template Fallback:** If complex prompt fails, use simplified version
- **Rule-Based Generation:** Backup bullet generation using templates and rules
- **Quality Recovery:** If validation fails, attempt correction prompts

### Performance Optimization
- **Prompt Caching:** Cache similar prompts to reduce token usage
- **Batch Processing:** Process multiple artifacts in single requests when possible
- **Async Processing:** Parallelize prompt building and response parsing

## Monitoring and Success Metrics

- **Generation Success Rate:** ≥95% successful 3-bullet generation
- **Quality Scores:** ≥8/10 average user rating for bullet quality
- **Token Efficiency:** <3000 tokens average per artifact processing
- **Processing Speed:** <10 seconds per artifact generation
- **Validation Pass Rate:** ≥90% of bullets pass all validation checks

## A/B Testing Framework

```python
# Template A/B testing configuration
AB_TEST_CONFIGS = {
    "bullet_generation_v1_vs_v2": {
        "control_template": "structured_template_v1",
        "experiment_template": "enhanced_examples_v2",
        "traffic_split": 0.2,  # 20% to experiment
        "success_metrics": [
            "user_rating",
            "bullet_quality_score",
            "keyword_relevance"
        ]
    }
}
```

## References

- **Prompt Engineering Research:** Best practices for structured LLM prompting
- **Few-Shot Learning Studies:** Effectiveness of examples in prompt design
- **Token Optimization Research:** Strategies for efficient LLM API usage

## Related ADRs

- [ADR-016-three-bullets-per-artifact](adr-016-three-bullets-per-artifact.md)
- [ADR-013-artifact-selection-algorithm](adr-013-artifact-selection-algorithm.md)
- [ADR-008-llm-provider-strategy](adr-008-llm-provider-strategy.md)

