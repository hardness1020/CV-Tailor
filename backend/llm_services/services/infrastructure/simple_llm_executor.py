"""
Simple LLM Executor Service

Lightweight execution helper for agent services that need direct LLM calls
without the full base class pattern complexity.

Created: Stage H refactor (ft-013)
Version: 1.1.0 - Refactored to use client_manager for GPT-5 compatibility
"""

import logging
from typing import Dict, Optional, TYPE_CHECKING

from llm_services.services.infrastructure.model_selector import IntelligentModelSelector

if TYPE_CHECKING:
    from llm_services.services.base.client_manager import APIClientManager

logger = logging.getLogger(__name__)


class SimpleLLMExecutor:
    """
    Lightweight LLM execution service for agent workflows.

    Delegates to APIClientManager for unified API call handling, gaining:
    - GPT-5 parameter transformations (max_completion_tokens, reasoning_effort, verbosity)
    - Centralized API key management
    - Future-proof for model API changes

    Features:
    - Automatic model configuration via ModelSelector
    - Real cost calculation based on model pricing
    - Error handling with fallback options
    - Token usage tracking

    Example:
        from llm_services.services.base.client_manager import APIClientManager

        client_manager = APIClientManager()
        executor = SimpleLLMExecutor(client_manager=client_manager)
        result = await executor.execute(
            prompt="Analyze this code...",
            model_name="gpt-5-mini",
            max_tokens=500
        )
        print(result['content'])
        print(f"Cost: ${result['cost']:.6f}")
    """

    def __init__(self, client_manager: Optional['APIClientManager'] = None):
        """
        Initialize executor with APIClientManager.

        Args:
            client_manager: APIClientManager instance. If None, creates a new one.

        Note:
            Passing client_manager is recommended for consistency with parent service's
            configuration and API key management.
        """
        if client_manager is None:
            # Backward compatibility: create new client_manager if not provided
            from llm_services.services.base.client_manager import APIClientManager
            self.client_manager = APIClientManager()
            logger.debug("SimpleLLMExecutor created new APIClientManager (backward compatibility)")
        else:
            self.client_manager = client_manager

        self.model_selector = IntelligentModelSelector()
        logger.info("SimpleLLMExecutor initialized with client_manager")

    async def execute(
        self,
        prompt: str,
        model_name: str = 'gpt-5-mini',
        max_tokens: int = 500,
        temperature: float = 0.3,
        system_message: Optional[str] = None
    ) -> Dict:
        """
        Execute LLM task with given prompt and parameters.

        Args:
            prompt: The user prompt/question to send to the LLM
            model_name: Model identifier (e.g., 'gpt-5', 'gpt-5-mini')
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            system_message: Optional system message for chat context

        Returns:
            Dict containing:
                - content (str): LLM response text
                - cost (float): Estimated cost in USD
                - tokens (int): Total tokens used (prompt + completion)
                - input_tokens (int): Prompt tokens
                - output_tokens (int): Completion tokens

        Raises:
            Exception: If API call fails
            ValueError: If model_name not recognized
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            # Get model configuration
            model_config = self.model_selector.registry.get_model_config(model_name)
            if not model_config:
                raise ValueError(f"Model '{model_name}' not found in registry")

            logger.debug(
                f"Executing LLM task: model={model_name}, max_tokens={max_tokens}, "
                f"temperature={temperature}"
            )

            # Build messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Make API call via client_manager (gains GPT-5 transformations automatically)
            response = await self.client_manager.make_completion_call(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract usage stats
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else (input_tokens + output_tokens)

            # Calculate real cost
            cost = self._calculate_cost(
                model_config=model_config,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            content = response.choices[0].message.content

            # Validate content is not empty
            if content is None or (isinstance(content, str) and not content.strip()):
                logger.warning(
                    f"[SimpleLLMExecutor] LLM returned empty content! "
                    f"model={model_name}, input_tokens={input_tokens}, output_tokens={output_tokens}. "
                    f"This may indicate content filtering, API issues, or model refusal."
                )
                # Return empty string rather than None to prevent downstream errors
                content = ""

            logger.info(
                f"LLM task completed: model={model_name}, tokens={total_tokens}, "
                f"cost=${cost:.6f}, content_length={len(content) if content else 0}"
            )

            return {
                'content': content,
                'cost': cost,
                'tokens': total_tokens,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens
            }

        except Exception as e:
            logger.error(f"LLM execution error: {e}")
            raise

    def _calculate_cost(
        self,
        model_config: Dict,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate real cost based on model pricing.

        Args:
            model_config: Model configuration from registry
            input_tokens: Number of prompt tokens
            output_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        # Get pricing from model config (costs are per million tokens in registry)
        cost_per_mtok_input = model_config.get('cost_input', 0.0)
        cost_per_mtok_output = model_config.get('cost_output', 0.0)

        # Calculate cost (convert from MTok to actual tokens)
        input_cost = (input_tokens / 1_000_000.0) * cost_per_mtok_input
        output_cost = (output_tokens / 1_000_000.0) * cost_per_mtok_output
        total_cost = input_cost + output_cost

        return total_cost
