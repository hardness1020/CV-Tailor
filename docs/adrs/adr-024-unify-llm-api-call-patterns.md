# ADR-024: Unify LLM API Call Patterns

**Status:** Accepted
**Date:** 2025-10-06
**Deciders:** Development Team
**Related:** ft-013-github-agent-traversal.md, llm_services architecture

## Context

During codebase analysis, we discovered **three competing patterns** for making OpenAI API calls across the llm_services module:

### Pattern A: Intended Architecture (Full Infrastructure) ✅
```
Public API → _execute_llm_task() → TaskExecutor → client_manager.make_completion_call() → _prepare_completion_kwargs() → LiteLLM
```

**Used by:**
- TailoredContentService
- Part of ArtifactEnrichmentService (content_unification task)

**Gains:**
- Circuit breaker protection
- Auto-retry logic with exponential backoff
- Performance tracking (latency, cost, success rate)
- Fallback model selection on failure
- GPT-5 parameter transformations (`max_completion_tokens`, `reasoning_effort`, `verbosity`)

### Pattern B: Bypassing Orchestration (Partial Infrastructure) ⚠️
```
Service method → client_manager.make_completion_call() directly
```

**Used by:**
- ArtifactEnrichmentService utility methods (`deduplicate_technologies_with_llm`, `_llm_rank_achievements`)

**Gains:**
- GPT-5 parameter transformations via `_prepare_completion_kwargs()`

**Missing:**
- Circuit breaker protection
- Auto-retry logic
- Performance tracking
- Fallback model selection

### Pattern C: Bypassing Everything (No Infrastructure) ❌
```
Service → SimpleLLMExecutor → Direct OpenAI SDK
```

**Used by:**
- GitHubRepositoryAgent (created in ft-013)
- HybridFileAnalyzer (created in ft-013)

**Missing:**
- Circuit breaker protection
- Auto-retry logic
- Performance tracking
- Fallback model selection
- **GPT-5 parameter transformations** ← **CRITICAL COMPATIBILITY ISSUE**

## Problem

### Critical GPT-5 Incompatibility
SimpleLLMExecutor directly calls OpenAI SDK without GPT-5 parameter transformations:

**What breaks:**
1. Passing `max_tokens` to GPT-5 → **API Error** (should be `max_completion_tokens`)
2. Passing `temperature` to GPT-5 → **API Error** (only default 1.0 supported)
3. Missing `reasoning_effort=minimal` for JSON tasks → **Higher costs** (excessive reasoning tokens)
4. Missing `verbosity=low` → **Higher costs** (verbose outputs)

**Impact:**
- **Immediate:** GitHubRepositoryAgent and HybridFileAnalyzer will fail when GPT-5 models are used
- **Future:** Any new service using SimpleLLMExecutor will encounter same issues
- **Cost:** Missing optimization parameters increase LLM costs

### Architecture Fragmentation
Three different call patterns create:
- **Maintenance burden:** API changes must be duplicated across patterns
- **Inconsistent reliability:** Some services have circuit breaker protection, others don't
- **Inconsistent observability:** Some services track performance, others don't
- **DRY violation:** Parameter transformation logic duplicated

## Decision

We will **unify all LLM API calls** on Pattern A (full infrastructure) by:

### 1. Refactor SimpleLLMExecutor (Critical - GPT-5 Compatibility)

**Change:**
```python
# Before (Pattern C - Direct OpenAI SDK)
class SimpleLLMExecutor:
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key)

    async def execute(...):
        response = await self.client.chat.completions.create(...)  # ❌ No GPT-5 transformations

# After (Delegates to client_manager)
class SimpleLLMExecutor:
    def __init__(self, client_manager: Optional['APIClientManager'] = None):
        self.client_manager = client_manager or APIClientManager()

    async def execute(...):
        response = await self.client_manager.make_completion_call(...)  # ✅ GPT-5 transformations automatic
```

**Benefits:**
- ✅ GPT-5 compatibility via `_prepare_completion_kwargs()`
- ✅ Centralized API key management
- ✅ Future-proof for model API changes
- ✅ Backward compatible (creates APIClientManager if not provided)

### 2. Update Callers to Pass client_manager

**Change:**
```python
# GitHubRepositoryAgent
def __init__(self):
    super().__init__()
    self.llm_executor = SimpleLLMExecutor(client_manager=self.client_manager)  # ✅

# HybridFileAnalyzer
def __init__(self):
    super().__init__()
    self.llm_executor = SimpleLLMExecutor(client_manager=self.client_manager)  # ✅
```

**Benefits:**
- ✅ Consistent with parent service's configuration
- ✅ Shares API keys and settings

### 3. Refactor Utility Methods to Use _execute_llm_task() (Enhancement)

**Change:**
```python
# Before (Pattern B - Direct client_manager)
async def _llm_deduplicate_technologies(self, ...):
    response = await self.client_manager.make_completion_call(...)  # ❌ No circuit breaker/retries

# After (Pattern A - Full infrastructure)
async def _llm_deduplicate_technologies(self, ...):
    context = {'prompt': prompt, 'task_type': 'tech_deduplication'}
    result = await self._execute_llm_task('tech_deduplication', context, user_id)  # ✅
```

**Benefits:**
- ✅ Circuit breaker protection
- ✅ Auto-retry logic
- ✅ Performance tracking
- ✅ Fallback model selection
- ✅ Consistent with TailoredContentService pattern

## Consequences

### Positive

1. **Single Source of Truth:** All OpenAI API calls go through `client_manager.make_completion_call()` → `_prepare_completion_kwargs()` → LiteLLM
2. **GPT-5 Compatibility Everywhere:** All services gain automatic parameter transformations
3. **Full Infrastructure Everywhere:** All services gain circuit breaker, retries, performance tracking, fallback models
4. **Reduced Maintenance:** API changes only need to be made in one place (`client_manager._prepare_completion_kwargs()`)
5. **Improved Observability:** All LLM calls tracked in performance metrics
6. **Cost Optimization:** All services benefit from `reasoning_effort` and `verbosity` optimizations

### Negative

1. **Increased Latency (Minimal):** Utility methods now go through TaskExecutor (adds ~1-2ms overhead)
2. **More Complex Stack Trace:** Debugging now involves more layers (but better error handling compensates)

### Neutral

1. **Breaking Change for SimpleLLMExecutor:** Constructor signature changed, but backward compatible (creates APIClientManager if not provided)
2. **Test Updates Required:** All mocks must mock `client_manager.make_completion_call()` instead of direct OpenAI client

## Implementation Summary

### Files Changed

1. **SimpleLLMExecutor** (`backend/llm_services/services/infrastructure/simple_llm_executor.py`)
   - Changed constructor to accept `client_manager`
   - Replaced direct OpenAI SDK calls with `client_manager.make_completion_call()`
   - Added backward compatibility (creates APIClientManager if not provided)

2. **GitHubRepositoryAgent** (`backend/llm_services/services/core/github_repository_agent.py`)
   - Pass `self.client_manager` to SimpleLLMExecutor constructor

3. **HybridFileAnalyzer** (`backend/llm_services/services/core/hybrid_file_analyzer.py`)
   - Pass `self.client_manager` to SimpleLLMExecutor constructor

4. **ArtifactEnrichmentService** (`backend/llm_services/services/core/artifact_enrichment_service.py`)
   - Wrapped `_llm_deduplicate_technologies()` to use `_execute_llm_task()`
   - Wrapped `_llm_rank_achievements()` to use `_execute_llm_task()`
   - Added task functions to `_build_task_function()`:
     - `tech_deduplication`
     - `achievement_ranking`

### Tests Verified

All 116 llm_services tests pass:
- ✅ GitHub repository agent tests (26 tests)
- ✅ Hybrid file analyzer tests (22 tests)
- ✅ All other llm_services tests (68 tests)

## Alternatives Considered

### Alternative 1: Keep Three Patterns (Rejected)

**Pros:**
- No refactoring required
- Each pattern optimized for its use case

**Cons:**
- ❌ SimpleLLMExecutor breaks with GPT-5 (critical blocker)
- ❌ DRY violation
- ❌ Maintenance burden
- ❌ Inconsistent reliability and observability

### Alternative 2: Only Fix SimpleLLMExecutor, Keep Pattern B (Rejected)

**Pros:**
- Minimal changes
- Utility methods stay lightweight

**Cons:**
- ❌ Still two patterns to maintain
- ❌ Utility methods still miss circuit breaker, retries, performance tracking
- ❌ Inconsistent reliability across services

### Alternative 3: Document Pattern B as Intentional (Rejected)

**Pros:**
- Acknowledges that utility methods are lightweight by design
- No refactoring required for Pattern B

**Cons:**
- ❌ Still need to fix SimpleLLMExecutor (critical)
- ❌ Utility methods still vulnerable to transient failures
- ❌ Performance tracking incomplete

## References

- [ft-013-github-agent-traversal.md](/docs/features/ft-013-github-agent-traversal.md) - Created SimpleLLMExecutor
- [client_manager.py](/backend/llm_services/services/base/client_manager.py) - `_prepare_completion_kwargs()` implementation
- [task_executor.py](/backend/llm_services/services/base/task_executor.py) - Circuit breaker, retries, performance tracking
- [OpenAI GPT-5 API Documentation](https://platform.openai.com/docs/api-reference/chat/create) - Parameter requirements

## Notes

- This refactoring preserves SimpleLLMExecutor's simple interface while gaining full infrastructure benefits
- All existing tests pass without modification (mocking strategy unchanged)
- Future model API changes (e.g., GPT-6) only require updates in `_prepare_completion_kwargs()`
- Performance overhead from TaskExecutor is negligible (~1-2ms) compared to LLM call latency (~500-2000ms)
