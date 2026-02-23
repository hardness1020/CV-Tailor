# ADR: Multi-Provider LLM Strategy for Artifact Processing

**File:** docs/adrs/adr-003-llm-provider-selection.md
**Status:** Draft

## Context

CV Tailor's enhanced artifact processing system requires reliable LLM services for content extraction, summarization, and semantic ranking. The system currently uses both OpenAI and Anthropic APIs with fallback logic, but this approach needs formalization for production reliability and cost optimization.

Key considerations:
- Processing volume: ~1000 artifacts/day at scale
- Content types: PDFs, GitHub repos, web profiles
- Latency requirements: <60s p95 for artifact enhancement
- Cost constraints: <$0.50 per artifact processing
- Reliability needs: 98% success rate for content processing

## Decision

Implement a **flexible multi-provider strategy** with unified API and easy model switching:

### Primary Configuration (2025)
1. **OpenAI GPT-4o** for content summarization and achievement extraction
   - Latest flagship model with superior speed and cost efficiency
   - Price: $2.50/$10 per million tokens (input/output)
2. **OpenAI text-embedding-3-small** for semantic similarity calculations
   - Most cost-effective embedding model at $0.02 per million tokens
   - 1536 dimensions, 62,500 pages per dollar
3. **Anthropic Claude Sonnet 4** as fallback for content processing
   - High-performance reasoning with $3/$15 per million tokens
   - 200K context window, superior for complex document analysis
4. **Circuit breaker pattern** with 5-failure threshold triggering 30s fallback period

### Flexible Model Configuration
```yaml
# Environment-based model switching
model_config:
  primary:
    chat_model: "gpt-4o"                    # Easy to switch to "gpt-4o-mini" or "o1"
    embedding_model: "text-embedding-3-small" # Can switch to "text-embedding-3-large"
    provider: "openai"

  fallback:
    chat_model: "claude-sonnet-4-20250514"  # Easy to switch to "claude-opus-4-1"
    provider: "anthropic"

  experimental:
    chat_model: "claude-opus-4-1-20250805"  # Most capable model for complex tasks
    provider: "anthropic"
```

## Consequences

### Positive
+ **Reliability**: 99.5%+ uptime through provider redundancy
+ **Cost efficiency**: OpenAI embeddings significantly cheaper than alternatives
+ **Performance**: GPT-4 superior quality for structured content extraction
+ **Existing integration**: Builds on current dual-provider infrastructure

### Negative
− **Complexity**: Multiple API key management and provider-specific logic
− **Consistency**: Potential output variations between providers during fallbacks
− **Cost risk**: Higher token usage if both providers used simultaneously
− **Vendor lock-in**: Heavy reliance on two specific providers

## Alternatives Considered

1. **OpenAI-only**: Simpler but single point of failure
   - Current flagship: GPT-4o ($2.50/$10 per MTok)
   - Alternative: o1 models for complex reasoning ($15/$60 per MTok)

2. **Anthropic-only**: Excellent quality but higher costs
   - Claude Opus 4.1: Most capable ($15/$75 per MTok)
   - Claude Sonnet 4: Balanced performance ($3/$15 per MTok)
   - Claude Haiku 3.5: Fastest option ($0.80/$4 per MTok)

3. **Open-source models**: Lower cost but infrastructure complexity
   - Llama 3.1, Mistral, etc. via local deployment
   - Requires significant DevOps overhead

4. **Cloud providers**: Enterprise features but vendor lock-in
   - Azure OpenAI: Enterprise compliance
   - AWS Bedrock: Multi-model access
   - Google Vertex AI: Integrated ML platform

## Implementation & Rollback Strategy

### Unified API Integration (LiteLLM)
```python
# Single codebase supporting multiple providers
from litellm import completion, embedding

# Easy model switching via configuration
response = await completion(
    model=settings.PRIMARY_CHAT_MODEL,  # "gpt-4o" or "claude-sonnet-4"
    messages=messages,
    api_key=get_api_key_for_model(settings.PRIMARY_CHAT_MODEL)
)

# Automatic fallback on failure
try:
    response = await completion(model=settings.PRIMARY_CHAT_MODEL, ...)
except Exception:
    response = await completion(model=settings.FALLBACK_CHAT_MODEL, ...)
```

### Model Migration Strategy
- **Zero-downtime switching**: Change environment variables to switch models
- **A/B testing**: Run multiple models simultaneously for quality comparison
- **Gradual rollout**: Percentage-based traffic splitting between models
- **Performance monitoring**: Automated alerts for model performance degradation

### Rollback Plan
- **Immediate**: Feature flags allow instant fallback to keyword matching
- **Model reversion**: Single environment variable change reverts to previous model
- **Provider switch**: Configuration-driven provider priority changes
- **Full rollback**: Cached summaries preserve functionality during transitions
- **Data preservation**: All enhanced content stored independently of provider choice

## Cost Analysis (2025 Pricing)

### Primary Configuration Cost per 1000 Artifacts
- **Content Processing**: 1000 artifacts × 2000 tokens avg × $2.50/MTok = $5.00
- **Embedding Generation**: 1000 artifacts × 1000 tokens avg × $0.02/MTok = $0.02
- **Total Primary Cost**: ~$5.02 per 1000 artifacts

### Fallback Configuration (if 10% fallback rate)
- **Claude Sonnet 4**: 100 artifacts × 2000 tokens × $3.00/MTok = $0.60
- **Total with Fallback**: ~$5.62 per 1000 artifacts

### Model Switching Options
```yaml
# Cost-optimized configuration
cost_optimized:
  chat_model: "gpt-4o-mini"           # $0.15/$0.60 per MTok
  embedding_model: "text-embedding-3-small"

# Performance-optimized configuration
performance_optimized:
  chat_model: "claude-opus-4-1"       # $15/$75 per MTok
  embedding_model: "text-embedding-3-large" # $0.13 per MTok

# Balanced configuration (current)
balanced:
  chat_model: "gpt-4o"               # $2.50/$10 per MTok
  embedding_model: "text-embedding-3-small" # $0.02 per MTok
```

## Links

- **TECH-SPEC**: `spec-20240924-llm-artifacts.md`
- **Feature**: `ft-llm-001-content-extraction.md`
- **Feature**: `ft-llm-002-embedding-storage.md`
- **LiteLLM Docs**: https://docs.litellm.ai/docs/providers
- **OpenAI Models**: https://platform.openai.com/docs/models
- **Anthropic Models**: https://docs.anthropic.com/en/docs/about-claude/models/overview