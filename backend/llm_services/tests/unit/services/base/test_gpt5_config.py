"""
Unit tests for GPT-5 configuration (ft-030 - Anti-Hallucination Improvements).
Tests task-based model configuration, reasoning_effort support, and deprecated parameter removal.

Implements ADR-045: GPT-5 Reasoning Configuration (corrected version from spec-llm.md v4.2.0)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag, override_settings
from django.contrib.auth import get_user_model
from typing import Dict, Any

from llm_services.services.base.base_service import BaseLLMService

User = get_user_model()


@tag('fast', 'unit', 'llm_services', 'gpt5')
class GPT5ConfigTestCase(TestCase):
    """Test GPT-5 configuration with reasoning_effort support"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_task_type_enum_exists(self):
        """Test that TaskType enum is defined with correct values"""
        from llm_services.services.base.config_registry import TaskType

        # Verify enum has required task types
        assert hasattr(TaskType, 'EXTRACTION')
        assert hasattr(TaskType, 'VERIFICATION')
        assert hasattr(TaskType, 'GENERATION')
        assert hasattr(TaskType, 'RANKING')

        # Verify enum values are strings
        assert isinstance(TaskType.EXTRACTION.value, str)
        assert isinstance(TaskType.VERIFICATION.value, str)

    def test_gpt5_configs_registry_exists(self):
        """Test that GPT5_CONFIGS registry is defined"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS, TaskType

        # Verify registry exists and has all task types
        assert TaskType.EXTRACTION in GPT5_CONFIGS
        assert TaskType.VERIFICATION in GPT5_CONFIGS
        assert TaskType.GENERATION in GPT5_CONFIGS
        assert TaskType.RANKING in GPT5_CONFIGS

        # Verify extraction config has reasoning_effort='high'
        extraction_config = GPT5_CONFIGS[TaskType.EXTRACTION]
        assert 'reasoning_effort' in extraction_config
        assert extraction_config['reasoning_effort'] == 'high'
        assert extraction_config['model'] == 'gpt-5'

        # Verify verification config has reasoning_effort='high'
        verification_config = GPT5_CONFIGS[TaskType.VERIFICATION]
        assert verification_config['reasoning_effort'] == 'high'
        assert verification_config['model'] == 'gpt-5'

        # Verify generation config has reasoning_effort='low'
        generation_config = GPT5_CONFIGS[TaskType.GENERATION]
        assert generation_config['reasoning_effort'] == 'low'
        assert generation_config['model'] == 'gpt-5-mini'

        # Verify ranking config
        ranking_config = GPT5_CONFIGS[TaskType.RANKING]
        assert ranking_config['model'] == 'gpt-5-nano'

    def test_deprecated_parameters_not_in_config(self):
        """Test that deprecated GPT-5 parameters are NOT in configs"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS, TaskType

        deprecated_params = ['temperature', 'top_p', 'thinking_tokens', 'reasoning']

        for task_type, config in GPT5_CONFIGS.items():
            for param in deprecated_params:
                assert param not in config, \
                    f"Deprecated parameter '{param}' should not be in {task_type.value} config"

    def test_max_completion_tokens_replaces_max_tokens(self):
        """Test that max_completion_tokens is used instead of max_tokens"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS, TaskType

        # GPT-5 uses max_completion_tokens (renamed from max_tokens)
        extraction_config = GPT5_CONFIGS[TaskType.EXTRACTION]
        assert 'max_completion_tokens' in extraction_config
        assert 'max_tokens' not in extraction_config
        assert isinstance(extraction_config['max_completion_tokens'], int)
        assert extraction_config['max_completion_tokens'] > 0

    def test_reasoning_effort_values_are_valid(self):
        """Test that reasoning_effort values are valid GPT-5 options"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS

        valid_reasoning_efforts = ['low', 'medium', 'high']

        for task_type, config in GPT5_CONFIGS.items():
            if 'reasoning_effort' in config:
                assert config['reasoning_effort'] in valid_reasoning_efforts, \
                    f"Invalid reasoning_effort value: {config['reasoning_effort']}"

    def test_base_service_supports_task_type_parameter(self):
        """Test that BaseLLMService __init__ accepts task_type parameter"""
        from llm_services.services.base.config_registry import TaskType

        # Create service with task_type
        service = BaseLLMService(task_type=TaskType.EXTRACTION)

        # Verify task_type is stored
        assert hasattr(service, 'task_type')
        assert service.task_type == TaskType.EXTRACTION

    def test_base_service_builds_config_from_task_type(self):
        """Test that BaseLLMService builds config based on task_type"""
        from llm_services.services.base.config_registry import TaskType

        # Create service with extraction task type
        service = BaseLLMService(task_type=TaskType.EXTRACTION)

        # Get LLM config for extraction task
        config = service._build_llm_config()

        # Verify config includes reasoning_effort='high'
        assert 'reasoning_effort' in config
        assert config['reasoning_effort'] == 'high'
        assert config['model'] == 'gpt-5'

        # Verify deprecated parameters are not included
        assert 'temperature' not in config
        assert 'thinking_tokens' not in config

    def test_base_service_builds_config_for_verification_task(self):
        """Test config building for verification task type"""
        from llm_services.services.base.config_registry import TaskType

        service = BaseLLMService(task_type=TaskType.VERIFICATION)
        config = service._build_llm_config()

        assert config['reasoning_effort'] == 'high'
        assert config['model'] == 'gpt-5'

    def test_base_service_builds_config_for_generation_task(self):
        """Test config building for generation task type (low reasoning effort)"""
        from llm_services.services.base.config_registry import TaskType

        service = BaseLLMService(task_type=TaskType.GENERATION)
        config = service._build_llm_config()

        assert config['reasoning_effort'] == 'low'
        assert config['model'] == 'gpt-5-mini'

    def test_base_service_defaults_to_generation_if_no_task_type(self):
        """Test that service defaults to GENERATION task type if none specified"""
        service = BaseLLMService()

        # Should default to GENERATION (most common use case)
        assert hasattr(service, 'task_type')
        from llm_services.services.base.config_registry import TaskType
        assert service.task_type == TaskType.GENERATION

    @override_settings(GPT5_REASONING_EXTRACTION='medium')
    def test_environment_variable_override_reasoning_effort(self):
        """Test that environment variables can override reasoning_effort"""
        from llm_services.services.base.config_registry import TaskType, get_task_config

        # Get config with environment override
        config = get_task_config(TaskType.EXTRACTION)

        # Should use environment override ('medium' instead of default 'high')
        assert config['reasoning_effort'] == 'medium'

    @override_settings(GPT5_MODEL_EXTRACTION='gpt-5-custom')
    def test_environment_variable_override_model(self):
        """Test that environment variables can override model selection"""
        from llm_services.services.base.config_registry import TaskType, get_task_config

        config = get_task_config(TaskType.EXTRACTION)

        # Should use environment override
        assert config['model'] == 'gpt-5-custom'

    def test_config_includes_max_completion_tokens_for_all_tasks(self):
        """Test that all task configs include max_completion_tokens"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS

        for task_type, config in GPT5_CONFIGS.items():
            assert 'max_completion_tokens' in config, \
                f"{task_type.value} config missing max_completion_tokens"
            assert config['max_completion_tokens'] > 0

    def test_reasoning_effort_not_in_ranking_config(self):
        """Test that ranking task doesn't use reasoning_effort (uses nano model)"""
        from llm_services.services.base.config_registry import GPT5_CONFIGS, TaskType

        ranking_config = GPT5_CONFIGS[TaskType.RANKING]

        # Nano model doesn't support reasoning mode
        assert 'reasoning_effort' not in ranking_config or \
               ranking_config.get('reasoning_effort') is None

        # Should use gpt-5-nano
        assert ranking_config['model'] == 'gpt-5-nano'

    def test_client_manager_uses_task_config(self):
        """Test that API calls use task-specific configuration"""
        from llm_services.services.base.config_registry import TaskType

        service = BaseLLMService(task_type=TaskType.EXTRACTION)

        # Mock the client manager's make_completion_call method
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock()

            # Simulate an LLM call
            service._prepare_llm_call()

            # Verify the call would include reasoning_effort parameter
            # (actual call testing will be in integration tests)
            config = service._build_llm_config()
            assert config['reasoning_effort'] == 'high'
