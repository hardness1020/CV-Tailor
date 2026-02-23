# ADR: Migrate to GPT-5 and Standardize Model Selection

**File:** `docs/adrs/adr-022-gpt5-model-migration.md`
**Status:** Accepted
**Date:** 2025-10-05
**Last Updated:** 2025-10-05

## Context

The LLM landscape has evolved significantly with OpenAI's release of GPT-5 in August 2025. Our current model registry includes multiple legacy models (GPT-4o, GPT-4o-mini, GPT-3.5-turbo, text-embedding-ada-002) that create complexity and maintenance overhead.

**Current State:**
- **Chat Models:** gpt-4o, gpt-4o-mini, Claude models, gpt-3.5-turbo (deprecated)
- **Embedding Models:** text-embedding-3-small (default), text-embedding-3-large, text-embedding-ada-002 (deprecated)
- Multiple fallback chains and strategy configurations across 4+ models
- Test suites reference outdated model names

**Problems:**
1. **Model Fragmentation:** 7+ models in registry creates cognitive overhead
2. **Deprecated Models:** gpt-3.5-turbo and text-embedding-ada-002 marked deprecated but still in fallback chains
3. **Suboptimal Performance:** GPT-5 offers better reasoning, coding, and agentic capabilities than GPT-4o
4. **Cost Uncertainty:** Pricing structure for GPT-5 needs to be incorporated into budget optimization

**Requirements:**
- Maintain flexibility for different use cases (cost-optimized, balanced, quality-optimized)
- Keep embedding model stable (text-embedding-3-small working well)
- Remove redundant models to simplify codebase
- Ensure smooth migration path with fallback safety

## Decision

**Adopt GPT-5 as the primary chat model family, standardize on text-embedding-3-small for embeddings, and remove Anthropic provider entirely for a simplified OpenAI-only architecture.**

### Model Configuration

**Chat Models (3 tiers - OpenAI only):**
1. **gpt-5** - Primary model for balanced performance (replaces gpt-4o)
2. **gpt-5-mini** - Cost-optimized model (replaces gpt-4o-mini)
3. **gpt-5-nano** - Ultra-cost-optimized for simple tasks (new addition)

**Embedding Models (1 model):**
1. **text-embedding-3-small** - Single standard embedding model for all use cases

**Removed Models:**
- ❌ gpt-4o, gpt-4o-mini (superseded by GPT-5 family)
- ❌ gpt-3.5-turbo (deprecated, no longer needed)
- ❌ text-embedding-ada-002 (deprecated, inferior performance)
- ❌ text-embedding-3-large (unnecessary complexity, text-embedding-3-small sufficient)
- ❌ claude-sonnet-4-20250514 (Anthropic provider removed for simplification)
- ❌ claude-opus-4-1-20250805 (Anthropic provider removed for simplification)

### Strategy Mappings

**Cost-Optimized:**
- Job parsing: `gpt-5-mini`
- CV generation: `gpt-5-mini`
- Embedding: `text-embedding-3-small`

**Balanced (default):**
- Job parsing: `gpt-5`
- CV generation: `gpt-5`
- Embedding: `text-embedding-3-small`

**Quality-Optimized:**
- Job parsing: `gpt-5`
- CV generation: `gpt-5`
- Embedding: `text-embedding-3-small`

### Fallback Chains

**OpenAI Chat:** `gpt-5` → `gpt-5-mini` → `gpt-5-nano`
**Embedding:** `text-embedding-3-small` only (no fallback - highly reliable single model)

**Note:** Single provider architecture (OpenAI only) provides simplicity while maintaining resilience through fallback chain.

## Consequences

### Positive (+)

1. **Improved Performance:** GPT-5 offers better reasoning, coding quality, and agentic capabilities
2. **Simplified Architecture:** Reducing from 7+ models to 3 active models (3 GPT-5 variants, 1 embedding)
3. **Cleaner Codebase:** Remove deprecated model references, Anthropic client code, simplify test fixtures
4. **Future-Proof:** GPT-5 is OpenAI's latest model family, will receive ongoing support
5. **Better Cost Control:** gpt-5-nano provides new ultra-cheap tier for simple tasks
6. **Maintained Flexibility:** Still support 3 optimization strategies (cost/balanced/quality)
7. **Single Embedding Model:** No embedding model selection complexity, text-embedding-3-small works for all cases
8. **Single Provider:** No multi-provider complexity, unified API client management
9. **Reduced Dependencies:** Remove anthropic and langchain-anthropic packages from dependencies

### Negative (-)

1. **Migration Effort:** Need to update model_registry, model_selector, settings, client_manager, and 40+ files
2. **Cost Unknown:** GPT-5 pricing not yet documented in our analysis (need to research)
3. **Performance Baseline Reset:** Need to re-establish performance benchmarks and quality thresholds
4. **API Compatibility Risk:** GPT-5 may have different API parameters or behaviors (need testing)
5. **Existing Metrics Invalidation:** Historical performance data tied to GPT-4o becomes less relevant
6. **Loss of Provider Diversity:** Single point of failure if OpenAI experiences outages
7. **Quality Trade-off:** May lose Claude's creative writing strengths (though GPT-5 expected to be sufficient)

### Risks

1. **Breaking Changes:** If GPT-5 API differs from GPT-4 API, could cause runtime errors
2. **Cost Overruns:** If GPT-5 is significantly more expensive, could exceed budget
3. **Quality Regression:** If GPT-5 performs worse on specific CV generation tasks
4. **Rate Limiting:** New model may have different rate limits or quotas

## Alternatives Considered

### Alternative 1: Keep GPT-4o as Primary, Add GPT-5 as Optional
- **Pros:** Lower risk, gradual migration, maintain existing baselines
- **Cons:** Continues model fragmentation, delays inevitable migration, misses GPT-5 improvements
- **Rejected:** Delays the inevitable and adds more models instead of simplifying

### Alternative 2: Keep text-embedding-3-large for Premium Use Cases
- **Pros:** Higher quality embeddings (3072 dimensions vs 1536), better MTEB scores (64.6 vs 62.3)
- **Cons:** 6.5x more expensive, minimal quality difference in practice, adds complexity
- **Rejected:** text-embedding-3-small is sufficient for CV similarity matching, cost savings significant

### Alternative 3: Remove All Non-OpenAI Models
- **Pros:** Maximum simplification, single provider, reduced code complexity, easier maintenance
- **Cons:** Loses Claude's strengths in creative writing, reduces provider diversity, single point of failure
- **✅ ACCEPTED:** Simplification benefits outweigh diversity concerns; GPT-5 quality sufficient for all use cases; OpenAI fallback chain provides adequate reliability

### Alternative 4: Migrate to Claude as Primary
- **Pros:** Claude Opus has premium quality, proven performance in our tests
- **Cons:** More expensive, slower, OpenAI has stronger developer ecosystem
- **Rejected:** Cost and speed trade-offs not justified for general use cases

### Alternative 5: Keep All Models "Just in Case"
- **Pros:** Maximum flexibility, no migration needed
- **Cons:** Technical debt accumulates, test maintenance burden, unclear model selection logic
- **Rejected:** Goes against the goal of removing redundant models

## Rollback Plan

If GPT-5 migration causes issues:

1. **Immediate Rollback (Circuit Breaker):**
   - Circuit breaker will automatically fall back to gpt-5-mini if gpt-5 fails repeatedly
   - Manual override: Set `MODEL_SELECTION_STRATEGY=legacy_gpt4o` in environment

2. **Partial Rollback (Strategy-Level):**
   - Revert specific strategies to GPT-4o while keeping GPT-5 available
   - Update settings.py MODEL_STRATEGIES to use legacy models

3. **Full Rollback (Code-Level):**
   - Revert commits related to this ADR
   - Restore model_registry.py to include GPT-4o models
   - Re-enable deprecated models temporarily

4. **Data Migration:**
   - No database schema changes, so no data migration needed
   - Performance tracking will have mixed GPT-4o/GPT-5 data during transition

## Implementation Plan

### Phase 1: Research & Validation (Before Implementation)
- [ ] Research GPT-5 pricing and update cost estimates
- [ ] Test GPT-5 API compatibility with existing code
- [ ] Run sample CV generations to validate quality
- [ ] Confirm rate limits and quotas for GPT-5

### Phase 2: Code Updates (Stage G)
- [ ] Update `model_registry.py` with GPT-5 models and remove deprecated models
- [ ] Update `settings_manager.py` default strategies
- [ ] Update `model_selector.py` selection logic and fallback chains
- [ ] Update `cv_tailor/settings.py` MODEL_STRATEGIES
- [ ] Update test fixtures and expected model names (28 files)

### Phase 3: Testing & Validation (Stage F-H)
- [ ] Write tests for GPT-5 model selection
- [ ] Update integration tests to use GPT-5
- [ ] Run full test suite to catch regressions
- [ ] Test circuit breaker fallback behavior
- [ ] Validate cost tracking for GPT-5 usage

### Phase 4: Monitoring (Stage J-K)
- [ ] Monitor GPT-5 performance metrics (latency, cost, quality)
- [ ] Compare GPT-5 vs GPT-4o performance on real workloads
- [ ] Adjust selection logic if needed based on data
- [ ] Update documentation and runbooks

## Success Criteria

1. ✅ All tests pass with GPT-5 as default model
2. ✅ No increase in error rates or circuit breaker activations
3. ✅ CV generation quality maintained or improved (subjective review)
4. ✅ Cost per generation within acceptable range (define after pricing research)
5. ✅ Model registry has 4 active models total: 3 chat + 1 embedding (down from 7+)
6. ✅ Zero references to deprecated models in active code paths

## Links

- **TECH-SPEC:** `docs/specs/spec-llm.md` (will need version update)
- **FEATURES:** `docs/features/ft-llm-003-flexible-model-selection.md`
- **Related ADRs:**
  - `adr-003-llm-provider-selection.md` (original provider strategy)
  - `adr-008-llm-provider-strategy.md` (updated provider strategy)
- **Implementation Tracking:** TBD (will reference PR when created)
