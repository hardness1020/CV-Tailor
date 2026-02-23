# Feature — 012 GPT-5 Model Migration & Model Registry Simplification

**Feature ID:** ft-012
**Title:** Migrate to GPT-5 and Standardize Model Selection
**Status:** In Progress
**Priority:** P1 (Core Enhancement)
**Owner:** Backend Team
**Target Date:** 2025-10-12
**Sprint:** LLM Enhancement Sprint 3

## Overview

Migrate from GPT-4o family to GPT-5 family as the primary chat models, remove Anthropic provider entirely, remove deprecated models (gpt-3.5-turbo, text-embedding-ada-002, text-embedding-3-large, Claude models), and simplify the model registry from 7+ models to 3 active models (3 GPT-5 variants + 1 embedding). This reduces complexity, improves performance with OpenAI's latest reasoning models, eliminates multi-provider overhead, and maintains flexibility across cost/balanced/quality strategies.

**Goals:**
- Adopt GPT-5 (gpt-5, gpt-5-mini, gpt-5-nano) for improved reasoning and coding
- Remove Anthropic provider entirely (Claude Sonnet, Claude Opus)
- Remove deprecated OpenAI models to reduce technical debt
- Simplify model selection logic and fallback chains (single provider)
- Use text-embedding-3-small as the single embedding model (remove text-embedding-3-large)
- Remove anthropic and langchain-anthropic dependencies
- Ensure backward compatibility with existing tests and workflows

## Links

- **ADR:** [adr-022-gpt5-model-migration.md](../adrs/adr-022-gpt5-model-migration.md)
- **TECH-SPECs:** `docs/specs/spec-llm.md` (will need v2.0 update for contract changes)
- **Related Features:**
  - [ft-llm-003-flexible-model-selection.md](./ft-llm-003-flexible-model-selection.md) (base architecture)
  - [ft-llm-001-content-extraction.md](./ft-llm-001-content-extraction.md) (uses model registry)
  - [ft-llm-002-embedding-storage.md](./ft-llm-002-embedding-storage.md) (embedding models)

## Existing Implementation Analysis

### Current Architecture (from Stage B Discovery)

**Files Affected (28 total):**
1. **Model Registry & Selection:**
   - `llm_services/services/infrastructure/model_registry.py` (270 lines) - Core model definitions
   - `llm_services/services/infrastructure/model_selector.py` (434 lines) - Selection logic
   - `llm_services/services/base/settings_manager.py` (82 lines) - Config management
   - `cv_tailor/settings.py` - Django settings with MODEL_STRATEGIES

2. **Services Using Models:**
   - `llm_services/services/core/tailored_content_service.py` - CV generation
   - `llm_services/services/core/evidence_content_extractor.py` - Content extraction
   - `llm_services/services/core/artifact_enrichment_service.py` - Artifact processing
   - `llm_services/services/core/embedding_service.py` - Vector embeddings
   - `generation/services/bullet_generation_service.py` - Bullet generation

3. **Test Files (23 files referencing model names):**
   - `llm_services/tests/unit/services/infrastructure/test_model_registry.py`
   - `llm_services/tests/unit/services/infrastructure/test_model_selector.py`
   - `llm_services/tests/unit/services/core/test_tailored_content_service.py`
   - `llm_services/tests/integration/test_real_pdf_enrichment.py`
   - `generation/tests/test_services.py`
   - + 18 more test files

### Reusable Patterns

**✅ Keep These Patterns:**
- Circuit breaker for fault tolerance (llm_services/services/reliability/circuit_breaker.py)
- Task executor with retries (llm_services/services/base/task_executor.py)
- Model selection by complexity scoring (model_selector.py:135-181)
- Fallback chains (model_registry.py:188-218)
- Cost tracking (model_registry.py:171-185)

**❌ Remove These Deprecated/Unnecessary Models:**
- `gpt-4o`, `gpt-4o-mini` (superseded by GPT-5)
- `gpt-3.5-turbo` (marked deprecated, no longer used)
- `text-embedding-ada-002` (inferior to text-embedding-3-small)
- `text-embedding-3-large` (unnecessary complexity, text-embedding-3-small sufficient)
- `claude-sonnet-4-20250514` (Anthropic provider removed)
- `claude-opus-4-1-20250805` (Anthropic provider removed)

**🔄 Update These:**
- Default model references in tests (28 files)
- Fallback chains to use GPT-5 family
- Strategy configurations in settings.py

### Dependencies

**Internal:**
- Circuit breaker (llm_services/services/reliability/circuit_breaker.py) ✓
- Task executor (llm_services/services/base/task_executor.py) ✓
- Performance tracker (llm_services/services/reliability/performance_tracker.py) ✓

**External:**
- OpenAI Python SDK (requires GPT-5 support - already available)
- LiteLLM library (requires GPT-5 model mappings - check compatibility)

**Database:**
- No schema changes required (model names are strings in JSONB fields)

## Architecture Conformance

### Layer Assignment

**No new layers** - Updates existing infrastructure layer components:
- `llm_services/services/infrastructure/model_registry.py` (infrastructure layer) ✓
- `llm_services/services/infrastructure/model_selector.py` (infrastructure layer) ✓
- `llm_services/services/base/settings_manager.py` (base layer) ✓

### Pattern Compliance

**✅ Follows Existing Patterns:**
- Model registry as single source of truth
- Strategy-based configuration (cost/balanced/quality)
- Fallback chains for reliability
- Cost calculation and budget enforcement
- Performance tracking integration

**✅ Maintains Interfaces:**
- `ModelRegistry.get_model_config()` - No signature changes
- `IntelligentModelSelector.select_model_for_task()` - No signature changes
- `SettingsManager.get_model_selection_config()` - No signature changes

**✅ Backward Compatibility:**
- Existing services continue to use same APIs
- Circuit breaker fallback logic unchanged
- Performance tracking schema unchanged

## Acceptance Criteria

### Functional Requirements
- [ ] GPT-5 models (gpt-5, gpt-5-mini, gpt-5-nano) available in model registry
- [ ] Deprecated models removed (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, text-embedding-ada-002, text-embedding-3-large)
- [ ] Claude models removed (claude-sonnet-4-20250514, claude-opus-4-1-20250805)
- [ ] Anthropic client and API key management removed
- [ ] Default strategy uses gpt-5 for job parsing and CV generation
- [ ] Cost-optimized strategy uses gpt-5-mini
- [ ] Quality-optimized strategy uses gpt-5 (previously used Claude Opus)
- [ ] Single embedding model: text-embedding-3-small (all strategies use same model)
- [ ] Fallback chains updated: gpt-5 → gpt-5-mini → gpt-5-nano (OpenAI only)

### Quality & Performance
- [ ] All existing tests pass with GPT-5 models (after test updates)
- [ ] CV generation quality maintained or improved (manual review of 10 samples)
- [ ] Response time ≤ 2s p95 for balanced strategy
- [ ] Circuit breaker activates correctly on GPT-5 failures
- [ ] Cost tracking accurate for GPT-5 models

### Testing Requirements
- [ ] Unit tests updated with new model names
- [ ] Integration tests run successfully with GPT-5
- [ ] Cost calculation tests verify GPT-5 pricing
- [ ] Fallback chain tests verify gpt-5 → gpt-5-mini → gpt-5-nano
- [ ] Model selector tests verify GPT-5 selection logic

### Documentation & Compliance
- [ ] Model registry docstrings updated
- [ ] ADR marked as "Accepted"
- [ ] SPEC updated to v2.0 (contract change for model names)
- [ ] No references to deprecated models in active code paths
- [ ] Environment variable docs updated (if new vars added)

## Design Changes

### Model Registry Changes

**Before (5 chat + 3 embedding = 8 total):**
```python
"chat_models": {
    "gpt-4o": {...},
    "gpt-4o-mini": {...},
    "gpt-3.5-turbo": {...},  # deprecated
    "claude-sonnet-4-20250514": {...},
    "claude-opus-4-1-20250805": {...}
},
"embedding_models": {
    "text-embedding-3-small": {...},
    "text-embedding-3-large": {...},
    "text-embedding-ada-002": {...}  # deprecated
}
```

**After (3 chat + 1 embedding = 3 total, OpenAI only):**
```python
"chat_models": {
    "gpt-5": {
        "provider": "openai",
        "cost_input": 0.003,     # $3.00 per MTok (estimated)
        "cost_output": 0.012,    # $12.00 per MTok (estimated)
        "context_window": 128000,
        "max_tokens": 16384,
        "strengths": ["reasoning", "coding", "agentic_tasks"],
        "best_for": ["general", "complex_reasoning"],
        "quality_tier": "high",
        "speed_rank": 1
    },
    "gpt-5-mini": {
        "provider": "openai",
        "cost_input": 0.0002,    # $0.20 per MTok (estimated)
        "cost_output": 0.0008,   # $0.80 per MTok (estimated)
        "context_window": 128000,
        "max_tokens": 16384,
        "strengths": ["cost_efficiency", "speed"],
        "best_for": ["simple_tasks", "high_volume"],
        "quality_tier": "medium",
        "speed_rank": 1
    },
    "gpt-5-nano": {
        "provider": "openai",
        "cost_input": 0.0001,    # $0.10 per MTok (estimated)
        "cost_output": 0.0004,   # $0.40 per MTok (estimated)
        "context_window": 128000,
        "max_tokens": 8192,
        "strengths": ["ultra_cost_efficiency", "ultra_fast"],
        "best_for": ["ultra_simple_tasks", "extreme_volume"],
        "quality_tier": "basic",
        "speed_rank": 1
    }
},
"embedding_models": {
    "text-embedding-3-small": {
        "provider": "openai",
        "cost": 0.00002,        # $0.02 per MTok
        "dimensions": 1536,
        "max_input_tokens": 8191,
        "mteb_score": 62.3,
        "best_for": ["all_use_cases"],  # Single model for simplicity
        "quality_tier": "standard"
    }
    # text-embedding-3-large REMOVED (unnecessary complexity)
    # text-embedding-ada-002 REMOVED (deprecated)
}
```

### Strategy Configuration Changes

**Before:**
```python
MODEL_STRATEGIES = {
    'balanced': {
        'job_parsing_model': 'gpt-4o',
        'cv_generation_model': 'gpt-4o',
        'embedding_model': 'text-embedding-3-small'
    }
}
```

**After:**
```python
MODEL_STRATEGIES = {
    'balanced': {
        'job_parsing_model': 'gpt-5',
        'cv_generation_model': 'gpt-5',
        'embedding_model': 'text-embedding-3-small'
    },
    'cost_optimized': {
        'job_parsing_model': 'gpt-5-mini',
        'cv_generation_model': 'gpt-5-mini',
        'embedding_model': 'text-embedding-3-small'
    },
    'quality_optimized': {
        'job_parsing_model': 'gpt-5',
        'cv_generation_model': 'gpt-5',
        'embedding_model': 'text-embedding-3-small'  # Same for all strategies
    }
}
```

### Fallback Chain Changes

**Before:**
```python
"chat_models": {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
},
"embedding_models": {
    "openai": ["text-embedding-3-small", "text-embedding-ada-002"]
}
```

**After:**
```python
"chat_models": {
    "openai": ["gpt-5", "gpt-5-mini", "gpt-5-nano"]  # Single provider only
},
"embedding_models": {
    "openai": ["text-embedding-3-small"]  # Single model, no fallback needed
}
```

## Test & Eval Plan

### Unit Tests (Phase 1)

**Model Registry Tests:**
```python
# test_model_registry.py
def test_gpt5_model_config():
    """Verify GPT-5 models are in registry"""
    assert ModelRegistry.get_model_config("gpt-5") is not None
    assert ModelRegistry.get_model_config("gpt-5-mini") is not None
    assert ModelRegistry.get_model_config("gpt-5-nano") is not None

def test_deprecated_models_removed():
    """Verify deprecated models are gone"""
    all_chat = ModelRegistry.MODELS["chat_models"]
    all_embedding = ModelRegistry.MODELS["embedding_models"]

    active_chat = {k: v for k, v in all_chat.items() if not v.get("deprecated")}
    active_embedding = {k: v for k, v in all_embedding.items() if not v.get("deprecated")}

    assert "gpt-4o" not in active_chat
    assert "gpt-3.5-turbo" not in active_chat
    assert "text-embedding-3-large" not in active_embedding
    assert "text-embedding-ada-002" not in active_embedding

def test_fallback_chain_gpt5():
    """Verify GPT-5 fallback chain"""
    fallback = ModelRegistry.get_fallback_model("gpt-5")
    assert fallback == "gpt-5-mini"

    fallback2 = ModelRegistry.get_fallback_model("gpt-5-mini")
    assert fallback2 == "gpt-5-nano"
```

**Model Selector Tests:**
```python
# test_model_selector.py
def test_select_gpt5_for_balanced_strategy():
    """Verify gpt-5 selected for balanced strategy"""
    selector = IntelligentModelSelector()
    # Override strategy to balanced
    selector.strategy_config = {'job_parsing_model': 'gpt-5'}

    model = selector.select_model_for_task('job_parsing', {
        'job_description': 'Software Engineer role...'
    })
    assert model == 'gpt-5'

def test_select_gpt5_mini_for_cost_optimized():
    """Verify gpt-5-mini selected for cost strategy"""
    selector = IntelligentModelSelector()
    selector.strategy_config = {'job_parsing_model': 'gpt-5-mini'}

    model = selector.select_model_for_task('job_parsing', {
        'job_description': 'Short job'
    })
    assert model == 'gpt-5-mini'
```

### Integration Tests (Phase 2)

**Real API Tests (with FORCE_REAL_API_TESTS=true):**
```python
# test_real_gpt5_integration.py
@pytest.mark.skipif(not os.getenv('FORCE_REAL_API_TESTS'), reason="Real API test")
def test_gpt5_cv_generation():
    """Test real GPT-5 API for CV generation"""
    service = TailoredContentService()
    result = service.generate_tailored_content(
        job_data={'raw_content': 'Software Engineer at Tech Co'},
        artifacts=[{'title': 'Web App', 'content': 'Built React app'}]
    )

    assert result['model_used'] == 'gpt-5'
    assert 'content' in result
    assert result['cost_usd'] > 0
```

**Circuit Breaker Fallback:**
```python
def test_circuit_breaker_fallback_to_gpt5_mini():
    """Verify circuit breaker falls back to gpt-5-mini"""
    # Simulate gpt-5 failures
    with patch('openai.ChatCompletion.create') as mock:
        mock.side_effect = [Exception("Rate limit")] * 5  # Trigger circuit breaker

        # Should fall back to gpt-5-mini
        service = TailoredContentService()
        result = service.generate_content(...)

        assert result['model_used'] == 'gpt-5-mini'
```

### Manual Quality Testing (Phase 3)

**Test Cases:**
1. Generate 10 CVs with gpt-5 (balanced strategy)
2. Generate 10 CVs with gpt-5-mini (cost-optimized strategy)
3. Compare quality against baseline (historical GPT-4o samples)
4. Evaluate on dimensions:
   - Relevance to job description (1-5 scale)
   - Writing quality (1-5 scale)
   - Bullet point specificity (1-5 scale)
   - Overall coherence (1-5 scale)

**Success Criteria:**
- GPT-5 average quality ≥ GPT-4o baseline
- No regressions in content structure
- Acceptable cost per generation (<$0.20 for balanced)

## Telemetry & Metrics

### Key Metrics to Track

**Performance Metrics:**
- GPT-5 avg response time (target: <2s p95)
- GPT-5-mini avg response time (target: <1s p95)
- GPT-5-nano avg response time (target: <0.5s p95)

**Cost Metrics:**
- Cost per CV generation (by strategy)
- Daily/monthly GPT-5 spend
- Cost comparison: GPT-5 vs GPT-4o baseline

**Quality Metrics:**
- Quality score average (target: >0.85 for balanced)
- User satisfaction scores (if available)
- Circuit breaker activation rate (<1% expected)

**Reliability Metrics:**
- GPT-5 success rate (target: >99%)
- Fallback usage rate (<5% expected)
- Error rate by model

### Dashboards

**Model Performance Dashboard:**
```
- GPT-5 usage: [count] generations, [cost] USD
- Avg quality score: [0.87]
- Avg response time: [1.2s]
- Success rate: [99.2%]

- GPT-5-mini usage: [count] generations, [cost] USD
- Avg quality score: [0.82]
- Avg response time: [0.8s]
- Success rate: [99.5%]
```

**Alerting Thresholds:**
- GPT-5 error rate >5% (critical)
- GPT-5 response time >5s p95 (warning)
- Daily cost >$100 (budget alert)
- Quality score <0.80 (quality regression alert)

## Edge Cases & Risks

### Edge Cases

1. **GPT-5 API Unavailable:**
   - Circuit breaker activates after 5 failures
   - Falls back to gpt-5-mini
   - If all OpenAI models fail, fall back to Claude

2. **Very Long Job Descriptions (>50k tokens):**
   - Model selector should prefer Claude (200k context)
   - If gpt-5 is selected, may hit token limit
   - Mitigation: Add token counting before selection

3. **Cost Budget Exceeded:**
   - System should switch to gpt-5-nano automatically
   - Alert admin when 80% budget utilized
   - Graceful degradation to cheaper models

4. **Model Deprecation by OpenAI:**
   - Keep Claude models as provider diversity
   - Fallback chain ensures alternatives exist
   - Monitor OpenAI announcements for deprecation notices

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPT-5 pricing higher than estimated | High | High | Research pricing before implementation; budget alerts |
| GPT-5 API differs from GPT-4 | Medium | High | Test API compatibility in Phase 1; use LiteLLM wrapper |
| Quality regression vs GPT-4o | Low | High | Manual quality testing; revert if quality drops |
| Performance degradation | Low | Medium | Monitor response times; use circuit breaker |
| Test suite breaks | High | Low | Update tests systematically; run full suite before merge |

## Implementation Plan

### Phase 1: Research & Validation (Day 1)
**Before any code changes:**
- [ ] Research GPT-5 API pricing (OpenAI documentation)
- [ ] Test GPT-5 API compatibility with current LiteLLM version
- [ ] Run sample CV generation with gpt-5 to verify quality
- [ ] Confirm gpt-5-mini and gpt-5-nano availability
- [ ] Update cost estimates in ADR if pricing differs

### Phase 2: Write Tests (Day 2 - TDD Red Phase)
**Write failing tests first:**
- [ ] Update test_model_registry.py with GPT-5 expectations
- [ ] Update test_model_selector.py for GPT-5 selection logic
- [ ] Write integration test for GPT-5 API calls
- [ ] Write fallback chain tests
- [ ] Run tests - should fail (models don't exist yet)

### Phase 3: Implementation (Day 3-4 - TDD Green Phase)
**Make tests pass:**
- [ ] Update model_registry.py with GPT-5 models
- [ ] Remove deprecated models from registry
- [ ] Update fallback chains to GPT-5 family
- [ ] Update settings_manager.py defaults
- [ ] Update model_selector.py selection logic
- [ ] Update cv_tailor/settings.py MODEL_STRATEGIES
- [ ] Run tests - should pass

### Phase 4: Test Updates (Day 4-5 - TDD Green Phase)
**Update remaining tests:**
- [ ] Update all test fixtures referencing old models (28 files)
- [ ] Update mock responses for GPT-5
- [ ] Update cost calculation tests
- [ ] Run full test suite - should pass

### Phase 5: Manual Testing (Day 5 - Validation)
**Quality assurance:**
- [ ] Generate 10 sample CVs with gpt-5
- [ ] Generate 10 sample CVs with gpt-5-mini
- [ ] Compare quality against GPT-4o baseline
- [ ] Test circuit breaker fallback manually
- [ ] Verify cost tracking accuracy

### Phase 6: Documentation & Deployment (Day 6)
**Finalize:**
- [ ] Mark ADR as "Accepted"
- [ ] Update SPEC to v2.0 (model contract change)
- [ ] Update API documentation if needed
- [ ] Create PR with all changes
- [ ] Deploy to staging environment
- [ ] Monitor metrics for 24 hours
- [ ] Deploy to production

## Rollback Plan

**If GPT-5 causes issues post-deployment:**

### Immediate Rollback (Hot Fix)
1. Set environment variable: `MODEL_SELECTION_STRATEGY=legacy_gpt4o`
2. Restart backend services
3. Circuit breaker will handle ongoing failures

### Partial Rollback (Strategy-Level)
1. Revert `settings.py` MODEL_STRATEGIES to use gpt-4o
2. Keep GPT-5 models in registry but not as defaults
3. Monitor for 24 hours

### Full Rollback (Code Revert)
1. Revert Git commit for this feature
2. Re-add deprecated models temporarily
3. Update tests back to old model names
4. Redeploy previous version

**No database migrations required** - model names are strings in JSONB fields.

## Success Metrics

### Technical Metrics
- ✅ All 100+ tests pass with GPT-5 models
- ✅ Zero circuit breaker activations in first 24 hours
- ✅ Response time <2s p95 for balanced strategy
- ✅ Cost per generation within budget (<$0.20 for balanced)
- ✅ Model registry has 4 active models total (3 chat + 1 embedding)

### Quality Metrics
- ✅ GPT-5 quality score ≥0.85 average
- ✅ Manual review: no quality regressions vs GPT-4o
- ✅ User satisfaction maintained (if measured)

### Business Metrics
- ✅ 30% cost reduction for cost-optimized strategy (gpt-5-nano)
- ✅ Simplified architecture (fewer models to maintain)
- ✅ Future-proof with latest OpenAI models

## Future Enhancements

### Next Iterations
- **GPT-5 with Reasoning Mode:** Explore gpt-5-reasoning for complex CV analysis
- **Cost Optimization:** Fine-tune model selection based on real cost data
- **A/B Testing:** Compare GPT-5 vs Claude for specific use cases
- **Custom Fine-tuning:** Train GPT-5 on CV-specific data for better quality

### Related Features
- **ft-llm-004:** Multi-model ensembles (combine GPT-5 + Claude)
- **ft-llm-005:** User preference for model selection
- **ft-llm-006:** Advanced cost budgeting per user/team
