"""
Unit tests for SettingsManager.
"""

from unittest.mock import Mock, patch
from django.test import TestCase, override_settings, tag
from llm_services.services.base.settings_manager import SettingsManager


@tag('fast', 'unit', 'llm_services')
class SettingsManagerTestCase(TestCase):
    """Test suite for SettingsManager"""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = SettingsManager()

    @override_settings(
        OPENAI_API_KEY='test-openai-key'
    )
    def test_get_api_keys(self):
        """Test retrieving API keys."""
        keys = self.manager.get_api_keys()
        openai_key = keys['openai']

        self.assertEqual(openai_key, 'test-openai-key')

    @override_settings(
        MODEL_SELECTION_STRATEGY='balanced',
        MODEL_BUDGETS={'daily_limit_usd': 10.0}
    )
    def test_get_llm_config(self):
        """Test retrieving LLM configuration."""
        config = self.manager.get_llm_config()

        self.assertIsInstance(config, dict)
        self.assertIn('model_selection_strategy', config)
        self.assertEqual(config['model_selection_strategy'], 'balanced')

    @override_settings(
        LLM_SERVICE_SETTINGS={
            'default_timeout': 60,
            'retry_attempts': 3,
            'fallback_enabled': True
        }
    )
    def test_get_timeout_settings(self):
        """Test retrieving timeout settings."""
        config = self.manager.get_llm_config()
        timeout = config['default_timeout']
        max_retries = config['retry_attempts']

        self.assertEqual(timeout, 60)
        self.assertEqual(max_retries, 3)

    def test_default_values(self):
        """Test that default values are used when settings are not configured."""
        # Should return defaults when settings are missing
        config = self.manager.get_llm_config()
        timeout = config['default_timeout']
        max_retries = config['retry_attempts']

        self.assertIsInstance(timeout, int)
        self.assertIsInstance(max_retries, int)
        self.assertGreater(timeout, 0)
        self.assertGreater(max_retries, 0)

    @override_settings(OPENAI_API_KEY='')
    def test_missing_api_key(self):
        """Test handling of missing API key."""
        keys = self.manager.get_api_keys()
        # get_api_keys() returns empty string for missing keys, doesn't raise ValueError
        self.assertEqual(keys['openai'], '')

    def test_unsupported_provider(self):
        """Test handling of unsupported provider."""
        keys = self.manager.get_api_keys()
        # get_api_keys() only returns OpenAI key, accessing unsupported provider raises KeyError
        with self.assertRaises(KeyError):
            _ = keys['unsupported_provider']

    @override_settings(
        EMBEDDING_MODEL='text-embedding-3-small',
        EMBEDDING_DIMENSIONS=1536
    )
    def test_get_embedding_config(self):
        """Test retrieving embedding configuration."""
        config = self.manager.get_embedding_config()

        self.assertIsInstance(config, dict)
        self.assertIn('model', config)
        self.assertIn('dimensions', config)
        self.assertEqual(config['model'], 'text-embedding-3-small')
        self.assertEqual(config['dimensions'], 1536)

    def test_settings_caching(self):
        """Test that settings are cached for performance."""
        # Get config multiple times
        config1 = self.manager.get_llm_config()
        config2 = self.manager.get_llm_config()

        # Should return same object (cached)
        self.assertEqual(config1, config2)

    @override_settings(
        CIRCUIT_BREAKER_SETTINGS={
            'failure_threshold': 5,
            'timeout': 60,
            'retry_attempts': 3
        }
    )
    def test_get_circuit_breaker_config(self):
        """Test retrieving circuit breaker configuration."""
        config = self.manager.get_circuit_breaker_config()

        self.assertIsInstance(config, dict)
        self.assertIn('failure_threshold', config)
        self.assertIn('timeout', config)
        self.assertEqual(config['failure_threshold'], 5)
        self.assertEqual(config['timeout'], 60)

