"""
Task execution wrapper with common patterns for LLM services.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, Union
from .exception_handler import ExceptionHandler

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Wrapper for executing LLM tasks with common patterns"""

    def __init__(self,
                 client_manager,
                 circuit_breaker,
                 performance_tracker,
                 model_selector,
                 model_registry):
        self.client_manager = client_manager
        self.circuit_breaker = circuit_breaker
        self.performance_tracker = performance_tracker
        self.model_selector = model_selector
        self.model_registry = model_registry
        self.exception_handler = ExceptionHandler()

    async def execute_task(self,
                          task_type: str,
                          context: Dict[str, Any],
                          task_func: Callable[..., Awaitable[Any]],
                          user_id: Optional[int] = None,
                          max_retries: int = 2) -> Dict[str, Any]:
        """
        Execute a task with common patterns:
        - Model selection
        - Circuit breaker checking
        - Time tracking
        - Error handling with fallback
        - Performance tracking
        - Cost calculation
        """

        # Select optimal model
        selected_model = self.model_selector.select_model_for_task(task_type, context)

        # Check circuit breaker
        if not await self.circuit_breaker.can_attempt_request(selected_model):
            fallback_model = self.model_selector.get_fallback_model(selected_model, task_type)
            if fallback_model:
                selected_model = fallback_model
                context['fallback_used'] = True
            else:
                return {
                    'error': 'All models unavailable due to circuit breaker',
                    'error_details': {
                        'type': 'circuit_breaker',
                        'model': selected_model
                    }
                }

        attempt = 0
        last_error = None

        while attempt <= max_retries:
            start_time = time.time()

            try:
                # Execute the actual task
                result = await task_func(selected_model, context)

                processing_time_ms = int((time.time() - start_time) * 1000)

                # Calculate cost from response
                cost = 0.0
                tokens_used = 0

                # Check for usage in both formats - object attribute or dict key
                usage = None
                if hasattr(result, 'usage'):
                    usage = result.usage
                elif isinstance(result, dict) and 'usage' in result:
                    usage = result['usage']

                if usage:
                    tokens_used = getattr(usage, 'total_tokens', usage.get('total_tokens', 0) if isinstance(usage, dict) else 0)
                    prompt_tokens = getattr(usage, 'prompt_tokens', usage.get('prompt_tokens', 0) if isinstance(usage, dict) else 0)
                    completion_tokens = getattr(usage, 'completion_tokens', usage.get('completion_tokens', 0) if isinstance(usage, dict) else 0)

                    cost = self.model_registry.calculate_cost(
                        selected_model,
                        prompt_tokens,
                        completion_tokens
                    )

                # Record success
                await self.circuit_breaker.record_success(selected_model)

                # Track performance
                await self.performance_tracker.record_task(
                    model=selected_model,
                    task_type=task_type,
                    processing_time_ms=processing_time_ms,
                    tokens_used=tokens_used,
                    cost_usd=cost,
                    success=True,
                    user_id=user_id,
                    complexity_score=self.model_selector._calculate_complexity_score(context),
                    fallback_used=context.get('fallback_used', False)
                )

                # Add processing metadata
                if isinstance(result, dict):
                    result['processing_metadata'] = {
                        'model_used': selected_model,
                        'processing_time_ms': processing_time_ms,
                        'tokens_used': tokens_used,
                        'cost_usd': float(cost),
                        'fallback_used': context.get('fallback_used', False),
                        'attempt_number': attempt + 1,
                        'selection_reason': self.model_selector.get_selection_reason(selected_model, context)
                    }

                return result

            except Exception as error:
                processing_time_ms = int((time.time() - start_time) * 1000)
                last_error = error

                # Log error with context
                self.exception_handler.log_error(
                    error, selected_model, task_type,
                    {'attempt': attempt + 1, 'context': context}
                )

                # Record failure if should trigger circuit breaker
                if self.exception_handler.should_trigger_circuit_breaker(error):
                    await self.circuit_breaker.record_failure(selected_model)

                # Track failed performance
                await self.performance_tracker.record_task(
                    model=selected_model,
                    task_type=task_type,
                    processing_time_ms=processing_time_ms,
                    tokens_used=0,
                    cost_usd=0.0,
                    success=False,
                    user_id=user_id,
                    complexity_score=self.model_selector._calculate_complexity_score(context),
                    fallback_used=context.get('fallback_used', False)
                )

                # Try fallback if appropriate and not already using fallback
                if (self.exception_handler.should_use_fallback(error) and
                    not context.get('fallback_used', False) and
                    attempt == 0):  # Only try fallback on first attempt

                    fallback_model = self.model_selector.get_fallback_model(selected_model, task_type)
                    if fallback_model and fallback_model != selected_model:
                        logger.info(f"Attempting fallback to {fallback_model} due to {type(error).__name__}")
                        selected_model = fallback_model
                        context['fallback_used'] = True
                        # Don't increment attempt counter for fallback
                        continue

                attempt += 1

        # All retries exhausted
        return self.exception_handler.create_error_response(
            last_error, selected_model, processing_time_ms
        )

