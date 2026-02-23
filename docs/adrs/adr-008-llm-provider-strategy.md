# ADR: Multi-Provider LLM Strategy with OpenAI Primary and Anthropic Fallback

**File:** docs/adrs/adr-008-llm-provider-strategy.md
**Status:** Draft

## Context

The CV Auto-Tailor system requires reliable access to Large Language Models for:
- Job description parsing and requirements extraction
- Skill matching and relevance scoring between artifacts and job requirements
- CV content generation with tailored achievements and professional summaries
- Cover letter generation with company-specific personalization

Critical requirements:
- **Reliability**: ≥99.5% availability for generation requests
- **Quality**: ≥8/10 user rating for generated content
- **Performance**: ≤30s end-to-end CV generation
- **Cost Control**: Manageable token costs at scale (10,000+ users)
- **Vendor Risk**: No single point of failure for business-critical functionality

The main strategic options are:
1. Single provider (OpenAI only)
2. Multi-provider with primary/fallback (OpenAI + Anthropic)
3. Multi-provider with task-specific routing
4. Open-source models with cloud inference

## Decision

Implement a **multi-provider strategy** with **OpenAI as primary** and **Anthropic Claude as fallback**, using task-specific model selection and automatic failover.

### Primary Configuration
- **CV Generation**: OpenAI GPT-4 (quality-focused)
- **Cover Letter Generation**: OpenAI GPT-3.5-turbo (cost-optimized)
- **Job Description Parsing**: OpenAI GPT-3.5-turbo (structured output)
- **Skill Matching**: OpenAI text-embedding-ada-002 + GPT-3.5-turbo

### Fallback Configuration
- **All Tasks**: Anthropic Claude-3-haiku (cost-effective) with Claude-3-sonnet for complex CV generation

## Consequences

### Positive
+ **High Availability**: Redundant providers reduce single point of failure risk
+ **Cost Optimization**: Task-specific model selection balances quality and cost
+ **Quality Assurance**: Multiple models allow A/B testing and quality comparison
+ **Vendor Leverage**: Reduces dependency on single provider for pricing negotiations
+ **Performance Flexibility**: Can route traffic based on current provider performance
+ **Compliance Options**: Different providers may have different data residency options

### Negative
- **Complexity**: Multi-provider abstraction layer increases system complexity
- **Cost Overhead**: Need to maintain accounts and credits with multiple providers
- **Consistency Risk**: Different models may produce slightly different outputs
- **Integration Maintenance**: Must keep up with API changes from multiple providers
- **Testing Burden**: Quality assurance across multiple model combinations

## Alternatives

### Single Provider (OpenAI Only)
**Pros**: Simpler integration, consistent outputs, single vendor relationship
**Cons**: Single point of failure, vendor lock-in, limited negotiating power
**Verdict**: Too risky for business-critical application

### Open Source Models (Llama, Mistral)
**Pros**: No vendor lock-in, potentially lower costs at scale, full control
**Cons**: Infrastructure complexity, model updating burden, potentially lower quality
**Verdict**: Not suitable for MVP; consider for Phase 2 cost optimization

### Claude Primary Strategy
**Pros**: Excellent reasoning capabilities, competitive pricing
**Cons**: Smaller scale than OpenAI, fewer model options, less ecosystem support
**Verdict**: Better as fallback than primary due to market position

## Implementation Details

### Provider Abstraction Layer
```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse

    @abstractmethod
    async def embed(self, text: str) -> List[float]

# Routing Logic
class ModelRouter:
    def select_provider(self, task_type: str, fallback: bool = False) -> LLMProvider:
        if fallback:
            return self.anthropic_provider
        return self.openai_provider
```

### Failover Strategy
1. **Circuit Breaker**: Open circuit after 5 consecutive failures
2. **Timeout Handling**: 30s timeout with automatic fallback
3. **Health Monitoring**: Regular health checks on provider endpoints
4. **Gradual Recovery**: Slowly restore traffic to recovered provider

### Cost Management
- **Token Tracking**: Monitor usage per task type and user
- **Rate Limiting**: Prevent runaway costs with per-user limits
- **Cost Alerts**: Automated alerts at 80% of monthly budget
- **Model Selection**: Automatic downgrade to cheaper models if budget threshold exceeded

## Rollback Plan

If multi-provider strategy proves too complex or unreliable:

1. **Phase 1**: Disable fallback routing, use OpenAI only with enhanced monitoring
2. **Phase 2**: If OpenAI issues persist, switch to Anthropic Claude as primary
3. **Phase 3**: Consider API-compatible open source alternatives (OpenRouter, Together AI)

**Trigger Criteria**:
- Combined error rate >2% due to provider switching logic
- Inconsistent output quality affecting user satisfaction <7/10
- Provider integration costs >20% of development time

## Risk Mitigation

### Vendor Lock-in Prevention
- **Standardized Prompts**: Provider-agnostic prompt templates
- **Output Normalization**: Consistent response parsing across providers
- **Data Portability**: All training data and prompts stored independently

### Quality Consistency
- **Golden Dataset**: Shared evaluation set across all providers
- **A/B Testing**: Continuous quality comparison between providers
- **Output Validation**: Consistency checks between primary and fallback outputs

### Cost Control
- **Budget Monitoring**: Real-time cost tracking with automated cutoffs
- **Model Optimization**: Regular evaluation of cost/quality trade-offs
- **Caching Strategy**: Aggressive caching to reduce redundant API calls

## Links

- **PRD**: `prd-20250923.md` - LLM quality and performance requirements
- **TECH-SPECs**: `spec-20250923-llm.md`, `spec-20250923-system.md` - LLM integration architecture
- **Related ADRs**: `adr-005-backend-framework.md` - Django integration affects LLM client implementation