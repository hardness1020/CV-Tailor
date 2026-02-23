"""
Unified API client management for LLM services using LiteLLM.
"""

import logging
from typing import Dict, Any, Union
from litellm import completion, acompletion, aembedding
from .settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class APIClientManager:
    """Centralized API client management using LiteLLM for unified access"""

    def __init__(self):
        self.settings_manager = SettingsManager()
        self.api_keys = self.settings_manager.get_api_keys()

    def get_api_key(self, model_name: str) -> str:
        """Get API key for specific model (OpenAI only)"""
        if model_name.startswith(('gpt-', 'text-embedding-')):
            return self.api_keys.get('openai', '')
        return ''

    def _prepare_completion_kwargs(self, model: str, kwargs: dict) -> dict:
        """Transform kwargs for model-specific parameter requirements

        GPT-5 models (released August 2025) have specific requirements:
        - Use max_completion_tokens instead of max_tokens
        - Support reasoning_effort: minimal/low/medium/high (controls thinking tokens)
        - Support verbosity: low/medium/high (controls output length)
        - For JSON tasks, use minimal reasoning to avoid excessive reasoning tokens
        """
        prepared_kwargs = kwargs.copy()

        # GPT-5 specific transformations and optimizations
        if model.startswith('gpt-5'):
            # Transform max_tokens -> max_completion_tokens
            if 'max_tokens' in prepared_kwargs:
                prepared_kwargs['max_completion_tokens'] = prepared_kwargs.pop('max_tokens')
                logger.debug(f"Transformed max_tokens -> max_completion_tokens for {model}")

            # Remove temperature parameter (GPT-5 only supports default value of 1.0)
            if 'temperature' in prepared_kwargs:
                temp_value = prepared_kwargs.pop('temperature')
                logger.debug(f"Removed temperature={temp_value} for {model} (only default 1.0 supported)")

            # For JSON output tasks, use minimal reasoning to get direct responses
            if 'response_format' in prepared_kwargs and 'reasoning_effort' not in prepared_kwargs:
                prepared_kwargs['reasoning_effort'] = 'minimal'
                logger.debug(f"Set reasoning_effort=minimal for {model} JSON task")

            # Set low verbosity for concise outputs (unless overridden)
            if 'verbosity' not in prepared_kwargs:
                prepared_kwargs['verbosity'] = 'low'
                logger.debug(f"Set verbosity=low for {model}")

        return prepared_kwargs

    async def make_completion_call(self,
                                 model: str,
                                 messages: list,
                                 **kwargs) -> Any:
        """Make completion API call using LiteLLM"""

        # Transform parameters for model-specific requirements (GPT-5 reasoning, etc.)
        prepared_kwargs = self._prepare_completion_kwargs(model, kwargs)

        logger.debug(f"Making completion call to model {model} with kwargs: {prepared_kwargs}")

        return await acompletion(
            model=model,
            messages=messages,
            api_key=self.get_api_key(model),
            **prepared_kwargs
        )

    def make_completion_call_sync(self,
                                model: str,
                                messages: list,
                                **kwargs) -> Any:
        """Make synchronous completion API call using LiteLLM"""

        # Transform parameters for model-specific requirements
        prepared_kwargs = self._prepare_completion_kwargs(model, kwargs)

        return completion(
            model=model,
            messages=messages,
            api_key=self.get_api_key(model),
            **prepared_kwargs
        )

    async def make_embedding_call(self,
                                model: str,
                                input_text: Union[str, list],
                                **kwargs) -> Any:
        """Make embedding API call using LiteLLM (async)"""

        return await aembedding(
            model=model,
            input=input_text,
            api_key=self.get_api_key(model),
            **kwargs
        )

    def validate_model_access(self, model: str) -> bool:
        """Validate that we have access to use the specified model"""
        api_key = self.get_api_key(model)
        return bool(api_key)

    def get_available_models(self) -> Dict[str, list]:
        """Get list of available models based on configured API keys (OpenAI only)"""
        available = {
            'chat_models': [],
            'embedding_models': []
        }

        if self.api_keys.get('openai'):
            available['chat_models'].extend(['gpt-5', 'gpt-5-mini', 'gpt-5-nano'])
            available['embedding_models'].extend(['text-embedding-3-small'])

        return available

    async def aclose(self):
        """
        Cleanup async resources.

        This is a no-op for LiteLLM as it manages its own connection pooling.
        Provided to satisfy the async cleanup protocol expected by BaseLLMService.
        """
        # LiteLLM handles its own connection pooling and cleanup
        # No explicit cleanup needed here
        pass
