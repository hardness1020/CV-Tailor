# Feature — 002 CV Generation System

**File:** docs/features/ft-002-cv-generation.md
**Owner:** ML/Backend Team
**TECH-SPECs:** `spec-20250923-llm.md`, `spec-20250923-api.md`, `spec-20250923-frontend.md`

## Acceptance Criteria

### Job Description Processing
- [ ] Parse job descriptions from text input with ≥95% accuracy for standard formats
- [ ] Extract structured data: role title, company info, required skills, nice-to-have skills, responsibilities
- [ ] Identify company values and culture signals from job posting content
- [ ] Handle job descriptions in multiple formats: plain text, HTML, PDF paste
- [ ] Normalize extracted skills against taxonomy (e.g., "React.js" → "React", "Node" → "Node.js")
- [ ] Cache parsed job descriptions to avoid re-processing identical content

### Artifact-to-Job Matching
- [ ] Rank user artifacts by relevance to job requirements using AI scoring (0-10 scale)
- [ ] Identify skill gaps between user profile and job requirements
- [ ] Match artifacts to specific job responsibilities and requirements
- [ ] Provide explanation for relevance scores to help users understand matching logic
- [ ] Support filtering artifacts by label/role type before generation
- [ ] Handle edge case where user has no relevant artifacts (graceful messaging)

### CV Content Generation
- [ ] Generate professional summary (2-3 sentences) highlighting most relevant experience
- [ ] Create tailored achievement bullets with quantified metrics where available
- [ ] Prioritize skills mentioned in job description while maintaining authenticity
- [ ] Generate role-appropriate content tone (technical for engineering, business-focused for PM roles)
- [ ] Include evidence references that can be linked to supporting materials
- [ ] Maintain consistent formatting and professional language throughout

### Quality and Performance
- [ ] CV generation completes within 30 seconds end-to-end (P95)
- [ ] Generated content achieves ≥8/10 average user rating
- [ ] Content passes ATS keyword matching for target job description
- [ ] Generated CVs are 1-2 pages in length (user-configurable)
- [ ] No hallucinated information - all content grounded in user artifacts
- [ ] Graceful handling of LLM API failures with meaningful error messages

## Design Changes

### API Endpoints
```
POST /api/v1/generate/cv
Headers: Authorization: Bearer <token>
Body: {
  job_description: string,
  company_name: string,
  role_title: string,
  label_ids: number[], // Optional filter by artifact labels
  template_id: number, // Optional CV template
  custom_sections: { // Optional additional sections
    include_publications: boolean,
    include_certifications: boolean,
    include_volunteer: boolean
  },
  generation_preferences: {
    tone: "professional" | "technical" | "creative",
    length: "concise" | "detailed",
    focus_areas: string[] // e.g., ["leadership", "technical_skills"]
  }
}

Response: 202 {
  generation_id: string,
  status: "processing",
  estimated_completion_time: timestamp,
  job_description_hash: string
}

GET /api/v1/generate/cv/{generation_id}
Response: 200 {
  id: string,
  status: "processing" | "completed" | "failed",
  progress_percentage: number,
  content: {
    professional_summary: string,
    key_skills: string[],
    experience: [
      {
        title: string,
        organization: string,
        duration: string,
        achievements: string[],
        technologies_used: string[],
        evidence_references: string[]
      }
    ],
    projects: [
      {
        name: string,
        description: string,
        technologies: string[],
        evidence_url: string,
        impact_metrics: string
      }
    ],
    education: object[],
    certifications: object[]
  },
  metadata: {
    artifacts_used: number[],
    skill_match_score: number, // 0-10
    missing_skills: string[],
    generation_time: number,
    model_used: string
  },
  created_at: timestamp,
  completed_at: timestamp
}
```

### Database Schema Updates
```sql
-- Generated documents table
CREATE TABLE generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES auth_user(id) ON DELETE CASCADE,
    document_type VARCHAR(20) DEFAULT 'cv', -- cv, cover_letter
    job_description_hash VARCHAR(64) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'processing',
    progress_percentage INTEGER DEFAULT 0,
    error_message TEXT,
    artifacts_used INTEGER[] DEFAULT '{}',
    model_version VARCHAR(50),
    generation_time_ms INTEGER,
    user_rating INTEGER, -- 1-10
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '90 days')
);

-- Job description cache
CREATE TABLE job_descriptions (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    raw_content TEXT NOT NULL,
    parsed_data JSONB,
    company_name VARCHAR(255),
    role_title VARCHAR(255),
    parsing_confidence REAL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Generation quality tracking
CREATE TABLE generation_feedback (
    id SERIAL PRIMARY KEY,
    generation_id UUID REFERENCES generated_documents(id),
    feedback_type VARCHAR(50), -- rating, edit, complaint
    feedback_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### LLM Prompt Templates
```python
CV_GENERATION_PROMPT = """
You are a professional CV writer specializing in creating targeted, ATS-optimized resumes.

Job Requirements:
Company: {{company_name}}
Role: {{role_title}}
Key Requirements: {{key_requirements}}
Nice-to-Have: {{nice_to_have_skills}}
Company Values: {{company_values}}

User Background:
{% for artifact in ranked_artifacts[:5] %}
Artifact: {{artifact.title}}
Description: {{artifact.description}}
Technologies: {{artifact.technologies|join(", ")}}
Impact/Metrics: {{artifact.achievements}}
Evidence: {{artifact.evidence_links|length}} supporting links
Relevance Score: {{artifact.relevance_score}}/10
{% endfor %}

Generate a professional CV focusing on the most relevant experience for this specific role.

Requirements:
1. Professional summary (2-3 sentences)
2. Key skills section (prioritize job requirements)
3. Professional experience with quantified achievements
4. Projects section highlighting relevant work
5. Use active voice and strong action verbs
6. Include specific metrics and impacts where available
7. Tailor language to match job requirements
8. Maintain authenticity - no fabricated information

Output Format: JSON with sections: professional_summary, key_skills, experience, projects
"""

JOB_PARSING_PROMPT = """
Parse this job description and extract structured information:

{{job_description}}

Extract:
1. Role title and seniority level
2. Company information and industry
3. Must-have skills and technologies
4. Nice-to-have skills
5. Key responsibilities (top 5)
6. Company values/culture keywords
7. Experience requirements (years, education)

Output as JSON with confidence scores for each extraction.
"""
```

### Frontend Components
```tsx
// CV Generation Flow
<CVGenerationWizard>
  <JobDescriptionStep onNext={handleJobInput} />
  <ArtifactSelectionStep artifacts={userArtifacts} onNext={handleArtifactFilter} />
  <PreferencesStep onNext={handlePreferences} />
  <GenerationStep onComplete={handleGenerationComplete} />
</CVGenerationWizard>

// Real-time generation progress
<GenerationProgress
  generationId={currentGeneration.id}
  onComplete={handleComplete}
  showDetails={true}
/>

// CV Preview and editing
<CVPreview
  content={generatedCV}
  onEdit={handleEdit}
  onExport={handleExport}
  onRating={handleRating}
/>
```

## Test & Eval Plan

### Unit Tests
- [ ] Job description parsing accuracy across various formats
- [ ] Skill matching algorithm with known artifact-job pairs
- [ ] Content generation quality with golden examples
- [ ] Template rendering with different data inputs
- [ ] Error handling for LLM API failures
- [ ] Caching behavior for duplicate job descriptions

### Integration Tests
- [ ] End-to-end CV generation workflow
- [ ] Multi-provider LLM failover scenarios
- [ ] Database transaction integrity during generation
- [ ] Concurrent generation handling (multiple users)
- [ ] Performance under load (100 simultaneous generations)

### AI Evaluation Framework
- [ ] Golden dataset of 100 job description + artifact + expected CV triplets
- [ ] Automated quality scoring using evaluation LLM
- [ ] A/B testing framework for prompt variations
- [ ] Regression testing for model updates
- [ ] Bias detection in generated content

### Quality Metrics
- **Content Relevance**: ≥85% of generated content should be relevant to job requirements
- **Skill Coverage**: ≥90% of user's relevant skills mentioned appropriately
- **Achievement Quality**: ≥80% of achievements include quantified metrics
- **ATS Compatibility**: ≥90% keyword match with job description
- **Authenticity**: 0% fabricated information (verified against artifacts)

### Performance Benchmarks
- **Generation Time**: P95 ≤30s, P50 ≤15s
- **API Response Time**: Generation initiation ≤2s
- **Memory Usage**: ≤512MB per generation process
- **Token Efficiency**: ≤8,000 tokens per CV generation average
- **Cache Hit Rate**: ≥60% for job description parsing

## Telemetry & Metrics to Watch

### User Experience Metrics
- **Generation Success Rate**: Target ≥95%
- **User Satisfaction**: Average rating ≥8/10
- **Completion Rate**: % of users who complete generation after starting
- **Edit Rate**: % of users who modify generated content
- **Regeneration Rate**: % of users who generate multiple versions

### Content Quality Metrics
- **Relevance Score**: AI-assessed content relevance to job requirements
- **Skill Match Accuracy**: % of job-relevant skills properly included
- **Achievement Quantification**: % of bullets with metrics vs vague claims
- **Hallucination Rate**: % of content not grounded in user artifacts
- **ATS Score**: Estimated ATS compatibility rating

### System Performance Metrics
- **Generation Latency**: End-to-end completion time distribution
- **LLM API Performance**: Response times and error rates by provider
- **Queue Depth**: Background job backlog for generation tasks
- **Cost per Generation**: Token usage and API costs
- **Error Rate**: Failed generations by error type

### Business Intelligence
- **Feature Adoption**: % of users who use CV generation
- **Retention Impact**: User retention after first CV generation
- **Premium Conversion**: Upgrade rate post-generation
- **Export Conversion**: % of generations that lead to document export

## Rollout/Canary & Rollback

### Rollout Strategy
**Phase 1 (5% Beta Users - 2 weeks)**
- Limited to power users with extensive artifact libraries
- Enhanced logging and manual quality review
- Daily feedback collection and iteration
- Maximum 3 generations per user per day

**Phase 2 (25% Users - 1 week)**
- Expand to broader user base
- A/B testing of different prompt strategies
- Automated quality monitoring implementation
- Remove daily generation limits

**Phase 3 (100% Users)**
- Full rollout with optimized prompts
- Real-time quality monitoring
- Cost optimization based on usage patterns

### Feature Flags
- `feature.cv_generation.enabled` - Master switch
- `feature.generation.gpt4_enabled` - Premium model access
- `feature.generation.multiple_providers` - Multi-provider routing
- `feature.generation.real_time_feedback` - Live generation progress
- `feature.generation.advanced_templates` - Additional CV formats

### Rollback Plan
**Critical Rollback Triggers**:
- Generation success rate <85% for >30 minutes
- Average user rating drops below 6/10
- Generation time P95 exceeds 60 seconds
- LLM API costs exceed 150% of budget
- Hallucination rate exceeds 5%

**Rollback Steps**:
1. Disable new generation requests via feature flag
2. Complete in-progress generations
3. Display maintenance message to users
4. Switch to simpler template-based generation as fallback
5. Debug and fix in development environment
6. Gradual re-enablement with enhanced monitoring

## Edge Cases & Risks

### Content Quality Risks
- **Hallucination**: LLM generates false information not in user artifacts
  - *Mitigation*: Strict grounding prompts, post-generation validation
- **Bias**: Generated content shows demographic or cultural bias
  - *Mitigation*: Bias detection in evaluation framework, diverse training examples
- **Inconsistency**: Multiple generations for same input produce very different results
  - *Mitigation*: Consistent prompt templates, temperature optimization

### Technical Risks
- **LLM Provider Outages**: Primary provider unavailable during peak usage
  - *Mitigation*: Multi-provider failover, graceful degradation
- **Performance Degradation**: High load causes generation timeouts
  - *Mitigation*: Auto-scaling, queue management, load balancing
- **Cost Explosion**: Unexpected usage patterns drive up LLM API costs
  - *Mitigation*: Usage monitoring, rate limiting, cost alerts

### User Experience Risks
- **Poor Job Description Input**: Users provide incomplete or unclear job descriptions
  - *Mitigation*: Input validation, guided prompts, example templates
- **Insufficient Artifacts**: Users with minimal artifacts get poor CV generation
  - *Mitigation*: Artifact sufficiency check, onboarding guidance
- **Over-reliance**: Users don't review/edit generated content before use
  - *Mitigation*: Prominent edit suggestions, quality disclaimers

### Business Risks
- **Quality Reputation**: Poor CV generation quality damages platform reputation
  - *Mitigation*: Conservative quality thresholds, user education
- **Legal Issues**: Generated content includes copyrighted or inappropriate material
  - *Mitigation*: Content filtering, terms of service, user responsibility disclaimers

## Dependencies

### External Services
- OpenAI API for primary CV generation
- Anthropic Claude API for fallback generation
- Embedding service for semantic similarity
- Skills taxonomy database for normalization

### Internal Components
- Artifact upload and management system (ft-001)
- User authentication and profile management
- Celery task queue for async processing
- Redis caching for job description and artifact data
- PostgreSQL for generation storage and retrieval

### Team Dependencies
- ML team for prompt engineering and evaluation
- Frontend team for generation UI and preview components
- Backend team for API integration and data management
- QA team for quality assurance and user testing