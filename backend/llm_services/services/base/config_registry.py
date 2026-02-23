"""
GPT-5 Configuration Registry (ft-030 - Anti-Hallucination Improvements).

Centralized configuration for GPT-5 models with task-specific reasoning effort settings.
Implements ADR-045 (corrected version from spec-llm.md v4.2.0).

Key corrections from ADR-045:
- Uses `reasoning_effort` instead of hallucinated `reasoning` and `thinking_tokens` parameters
- Uses `max_completion_tokens` instead of deprecated `max_tokens`
- Removes deprecated GPT-5 parameters (temperature, top_p, etc.)
- Supports environment variable overrides for flexibility
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """
    LLM task types with different reasoning requirements.

    EXTRACTION: Content extraction from documents (high reasoning needed)
    VERIFICATION: Fact-checking and claim verification (high reasoning needed)
    GENERATION: Content generation for CVs/cover letters (low reasoning sufficient)
    RANKING: Relevance scoring and ranking (simple task, nano model)
    """
    EXTRACTION = "extraction"
    VERIFICATION = "verification"
    GENERATION = "generation"
    RANKING = "ranking"


# GPT-5 Model Configuration Registry
# Maps task types to optimal model and reasoning effort settings
GPT5_CONFIGS: Dict[TaskType, Dict[str, Any]] = {
    TaskType.EXTRACTION: {
        'model': 'gpt-5',
        'reasoning_effort': 'high',  # Complex extraction requires deep reasoning
        'max_completion_tokens': 2000,  # Renamed from max_tokens in GPT-5
        'description': 'Extract structured content from documents with high accuracy'
    },

    TaskType.VERIFICATION: {
        'model': 'gpt-5',
        'reasoning_effort': 'high',  # Fact-checking requires careful analysis
        'max_completion_tokens': 1500,
        'description': 'Verify claims against source evidence with chain-of-thought'
    },

    TaskType.GENERATION: {
        'model': 'gpt-5-mini',  # Cheaper model sufficient for generation
        'reasoning_effort': 'low',  # Generation doesn't need deep reasoning
        'max_completion_tokens': 1000,
        'description': 'Generate CV bullets and cover letter content'
    },

    TaskType.RANKING: {
        'model': 'gpt-5-nano',  # Simplest model for ranking
        'max_completion_tokens': 500,
        'description': 'Rank artifacts by relevance to job description'
        # Note: gpt-5-nano doesn't support reasoning mode
    }
}


def get_task_config(task_type: TaskType) -> Dict[str, Any]:
    """
    Get configuration for a specific task type with environment variable overrides.

    Environment Variables (optional overrides):
    - GPT5_REASONING_{TASK_TYPE}: Override reasoning_effort (e.g., GPT5_REASONING_EXTRACTION=medium)
    - GPT5_MODEL_{TASK_TYPE}: Override model (e.g., GPT5_MODEL_EXTRACTION=gpt-5-custom)

    Args:
        task_type: The TaskType enum value

    Returns:
        Dict with model configuration including reasoning_effort, max_completion_tokens, etc.

    Example:
        >>> config = get_task_config(TaskType.EXTRACTION)
        >>> config['reasoning_effort']
        'high'
        >>> config['model']
        'gpt-5'
    """
    # Get base config from registry
    if task_type not in GPT5_CONFIGS:
        logger.warning(f"Unknown task type: {task_type}, defaulting to GENERATION config")
        task_type = TaskType.GENERATION

    config = GPT5_CONFIGS[task_type].copy()

    # Check for environment variable overrides
    task_name = task_type.value.upper()

    # Override reasoning_effort if specified
    reasoning_env_key = f'GPT5_REASONING_{task_name}'
    if hasattr(settings, reasoning_env_key):
        override_reasoning = getattr(settings, reasoning_env_key)
        config['reasoning_effort'] = override_reasoning
        logger.info(
            f"[ft-030] Overriding reasoning_effort for {task_type.value}: "
            f"{config.get('reasoning_effort', 'N/A')} -> {override_reasoning}"
        )

    # Override model if specified
    model_env_key = f'GPT5_MODEL_{task_name}'
    if hasattr(settings, model_env_key):
        override_model = getattr(settings, model_env_key)
        config['model'] = override_model
        logger.info(
            f"[ft-030] Overriding model for {task_type.value}: "
            f"{GPT5_CONFIGS[task_type]['model']} -> {override_model}"
        )

    return config


def validate_gpt5_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean GPT-5 parameters, removing deprecated ones.

    Deprecated GPT-5 parameters (will be removed):
    - temperature (not supported in GPT-5)
    - top_p (not supported in GPT-5)
    - thinking_tokens (hallucinated parameter from incorrect ADR-045)
    - reasoning (hallucinated boolean parameter)
    - max_tokens (renamed to max_completion_tokens)

    Args:
        params: Raw parameters dict

    Returns:
        Cleaned parameters dict with only valid GPT-5 parameters
    """
    deprecated_params = ['temperature', 'top_p', 'thinking_tokens', 'reasoning', 'max_tokens']

    cleaned_params = params.copy()

    for deprecated in deprecated_params:
        if deprecated in cleaned_params:
            value = cleaned_params.pop(deprecated)
            logger.warning(
                f"[ft-030] Removed deprecated GPT-5 parameter: {deprecated}={value}. "
                f"See spec-llm.md v4.2.0 for corrected GPT-5 API spec."
            )

    # Validate reasoning_effort if present
    if 'reasoning_effort' in cleaned_params:
        valid_efforts = ['low', 'medium', 'high']
        effort = cleaned_params['reasoning_effort']
        if effort not in valid_efforts:
            logger.error(
                f"[ft-030] Invalid reasoning_effort: {effort}. "
                f"Must be one of {valid_efforts}. Defaulting to 'medium'."
            )
            cleaned_params['reasoning_effort'] = 'medium'

    # Ensure max_completion_tokens is used (not max_tokens)
    if 'max_tokens' in params and 'max_completion_tokens' not in cleaned_params:
        cleaned_params['max_completion_tokens'] = params['max_tokens']
        logger.info(
            "[ft-030] Converted max_tokens to max_completion_tokens for GPT-5 compatibility"
        )

    return cleaned_params


def get_model_cost_multiplier(task_type: TaskType) -> float:
    """
    Get cost multiplier for task type.

    Reasoning mode (reasoning_effort='high') uses approximately 4x tokens:
    - Input tokens: counted normally
    - Output tokens: counted normally
    - Reasoning tokens: counted at 1:1 ratio (hidden from user)
    - Total multiplier: ~4x for high reasoning tasks

    Returns:
        Cost multiplier for the task type
    """
    config = GPT5_CONFIGS.get(task_type, {})
    reasoning_effort = config.get('reasoning_effort', 'low')

    multipliers = {
        'high': 4.0,    # High reasoning uses ~4x tokens
        'medium': 2.5,  # Medium reasoning uses ~2.5x tokens
        'low': 1.2,     # Low reasoning uses minimal extra tokens
        None: 1.0       # No reasoning mode (nano model)
    }

    return multipliers.get(reasoning_effort, 1.0)
