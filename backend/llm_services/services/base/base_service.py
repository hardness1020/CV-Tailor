"""
Base service class with common functionality for LLM services.
"""

import logging
from typing import Dict, Any, Optional
from .client_manager import APIClientManager
from .settings_manager import SettingsManager
from .task_executor import TaskExecutor
from ..infrastructure.model_registry import ModelRegistry
from ..infrastructure.model_selector import IntelligentModelSelector
from ..reliability.performance_tracker import ModelPerformanceTracker
from ..reliability.circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


class BaseLLMService:
    """
    Base class for LLM services providing common functionality:
    - Unified dependency initialization
    - Configuration management
    - Client management
    - Task execution patterns
    - Task-specific GPT-5 configuration (ft-030)
    """

    def __init__(self, task_type: Optional['TaskType'] = None):
        """
        Initialize base LLM service with optional task type for GPT-5 configuration.

        Args:
            task_type: Optional TaskType enum for task-specific configuration (ft-030).
                      Defaults to TaskType.GENERATION if not specified.
        """
        # ft-030: Store task type for configuration (import here to avoid circular dependency)
        if task_type is None:
            from .config_registry import TaskType
            task_type = TaskType.GENERATION  # Default to most common use case

        self.task_type = task_type

        # Initialize common dependencies
        self.settings_manager = SettingsManager()
        self.client_manager = APIClientManager()
        self.registry = ModelRegistry()
        self.model_selector = IntelligentModelSelector()
        self.performance_tracker = ModelPerformanceTracker()
        self.circuit_breaker = CircuitBreakerManager()

        # Initialize task executor with all dependencies
        self.task_executor = TaskExecutor(
            client_manager=self.client_manager,
            circuit_breaker=self.circuit_breaker,
            performance_tracker=self.performance_tracker,
            model_selector=self.model_selector,
            model_registry=self.registry
        )

        # Get service-specific configuration
        self.config = self._get_service_config()

        logger.debug(
            f"Initialized {self.__class__.__name__} with unified dependencies "
            f"(task_type={task_type.value if task_type else 'N/A'})"
        )

    def _get_service_config(self) -> Dict[str, Any]:
        """
        Override this method in subclasses to provide service-specific configuration.
        Base implementation returns common LLM settings.
        """
        return self.settings_manager.get_llm_config()

    async def _execute_llm_task(self,
                               task_type: str,
                               context: Dict[str, Any],
                               user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute an LLM task using the unified task executor.
        Subclasses should implement their specific task logic in _build_task_function.
        """

        # Build the task function based on task type
        task_func = self._build_task_function(task_type)

        # Execute with common patterns
        return await self.task_executor.execute_task(
            task_type=task_type,
            context=context,
            task_func=task_func,
            user_id=user_id
        )

    def _build_task_function(self, task_type: str):
        """
        Override this method in subclasses to provide task-specific implementations.
        Should return an async function that takes (model, context) and returns the result.
        """
        raise NotImplementedError("Subclasses must implement _build_task_function")

    def _build_llm_config(self) -> Dict[str, Any]:
        """
        Build LLM configuration based on task type (ft-030).

        Returns task-specific GPT-5 configuration including:
        - model: Model name (gpt-5, gpt-5-mini, gpt-5-nano)
        - reasoning_effort: Reasoning level (high, medium, low, or None)
        - max_completion_tokens: Token limit

        Deprecated parameters are automatically removed.

        Returns:
            Dict with cleaned GPT-5 configuration parameters
        """
        from .config_registry import get_task_config, validate_gpt5_parameters

        # Get task-specific config
        config = get_task_config(self.task_type)

        # Validate and clean parameters (removes deprecated ones)
        cleaned_config = validate_gpt5_parameters(config)

        logger.debug(
            f"[ft-030] Built LLM config for {self.task_type.value}: "
            f"model={cleaned_config.get('model')}, "
            f"reasoning_effort={cleaned_config.get('reasoning_effort', 'N/A')}"
        )

        return cleaned_config

    def _prepare_llm_call(self) -> Dict[str, Any]:
        """
        Prepare LLM API call parameters with task-specific configuration.

        This is a helper method that services can use when making LLM calls.
        Returns the full config that can be passed to client_manager.make_completion_call().

        Returns:
            Dict with API call parameters including model, reasoning_effort, etc.
        """
        return self._build_llm_config()

    def _validate_model_access(self, model_name: str) -> bool:
        """Validate that the service has access to use the specified model"""
        return self.client_manager.validate_model_access(model_name)

    def get_available_models(self) -> Dict[str, list]:
        """Get models available to this service"""
        return self.client_manager.get_available_models()

    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of the service and its dependencies"""
        available_models = self.get_available_models()

        return {
            'service_name': self.__class__.__name__,
            'status': 'healthy' if any(available_models.values()) else 'degraded',
            'available_models': available_models,
            'api_keys_configured': {
                provider: bool(key) for provider, key in self.client_manager.api_keys.items()
            },
            'config': self.config
        }

    async def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary for this service"""
        return await self.performance_tracker.get_model_performance_summary_async(days)

    def _build_prompt(self, prompt_type: str, **kwargs) -> str:
        """
        Helper method for building prompts. Override in subclasses.
        """
        raise NotImplementedError("Subclasses should implement _build_prompt if needed")

    def _process_response(self, response: Any, task_type: str) -> Dict[str, Any]:
        """
        Helper method for processing API responses. Override in subclasses.
        """
        raise NotImplementedError("Subclasses should implement _process_response if needed")

    async def cleanup(self):
        """
        Cleanup async resources to prevent leaks.
        Should be called when service is no longer needed.
        """
        try:
            await self.client_manager.aclose()
            logger.debug(f"Cleaned up {self.__class__.__name__} resources")
        except Exception as e:
            logger.warning(f"Error during {self.__class__.__name__} cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        await self.cleanup()
        return False