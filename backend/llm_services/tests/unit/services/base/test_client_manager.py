"""
Unit tests for APIClientManager with litellm integration.
"""

from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, override_settings, tag
from llm_services.services.base.client_manager import APIClientManager


@tag('fast', 'unit', 'llm_services')
class APIClientManagerTestCase(TestCase):
    """Test suite for APIClientManager with litellm-only implementation"""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = APIClientManager()

    @patch('llm_services.services.base.settings_manager.SettingsManager.get_api_keys')
    @patch('llm_services.services.base.client_manager.acompletion')
    async def test_litellm_completion_call(self, mock_acompletion, mock_get_api_keys):
        """Test that completion calls use litellm exclusively."""
        # Setup API key mock
        mock_get_api_keys.return_value = {'openai': 'test-openai-key'}

        # Recreate manager with mocked API keys
        self.manager = APIClientManager()

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_acompletion.return_value = mock_response

        model = "gpt-5"
        messages = [{"role": "user", "content": "Test"}]

        result = await self.manager.make_completion_call(model, messages, max_tokens=100)

        # Verify litellm was called with correct parameters
        mock_acompletion.assert_called_once()
        call_args = mock_acompletion.call_args
        self.assertEqual(call_args.kwargs['model'], model)
        self.assertEqual(call_args.kwargs['messages'], messages)
        self.assertEqual(call_args.kwargs['api_key'], 'test-openai-key')

    @patch('llm_services.services.base.settings_manager.SettingsManager.get_api_keys')
    @patch('llm_services.services.base.client_manager.aembedding', new_callable=AsyncMock)
    async def test_litellm_embedding_call(self, mock_embedding, mock_get_api_keys):
        """Test that embedding calls use litellm exclusively."""
        # Setup API key mock
        mock_get_api_keys.return_value = {'openai': 'test-openai-key'}

        # Recreate manager with mocked API keys
        self.manager = APIClientManager()

        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_embedding.return_value = mock_response

        model = "text-embedding-3-small"
        input_text = "Test text"

        result = await self.manager.make_embedding_call(model, input_text)

        # Verify litellm embedding was called
        mock_embedding.assert_called_once()
        call_args = mock_embedding.call_args
        self.assertEqual(call_args.kwargs['model'], model)
        self.assertEqual(call_args.kwargs['input'], input_text)
        self.assertEqual(call_args.kwargs['api_key'], 'test-openai-key')

    @override_settings(OPENAI_API_KEY='test-key')
    @patch('llm_services.services.base.client_manager.acompletion')
    async def test_gpt5_parameter_transformation(self, mock_acompletion):
        """Test GPT-5 parameter transformation (max_tokens → max_completion_tokens)."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test"))]
        mock_acompletion.return_value = mock_response

        # Call with max_tokens (should be transformed to max_completion_tokens for GPT-5)
        await self.manager.make_completion_call(
            "gpt-5",
            [{"role": "user", "content": "Test"}],
            max_tokens=500,
            temperature=0.7
        )

        # Verify transformation occurred
        call_args = mock_acompletion.call_args.kwargs
        self.assertIn('max_completion_tokens', call_args)
        self.assertEqual(call_args['max_completion_tokens'], 500)
        self.assertNotIn('max_tokens', call_args)
        self.assertNotIn('temperature', call_args)  # GPT-5 doesn't support temperature

    @override_settings(OPENAI_API_KEY='test-key')
    def test_no_openai_client_fallback(self):
        """Test that there is NO fallback to direct OpenAI client."""
        # Should not have _clients dict or OpenAI clients
        self.assertFalse(hasattr(self.manager, '_clients') and self.manager._clients.get('openai'))

    def test_litellm_required_import(self):
        """Test that litellm is a required import, not optional."""
        # This test verifies litellm is imported without try/except
        from llm_services.services.base import client_manager
        import inspect

        # Get source code of the module
        source = inspect.getsource(client_manager)

        # Should have direct import, not try/except
        self.assertIn('from litellm import', source)
        # Should NOT have HAS_LITELLM flag
        self.assertNotIn('HAS_LITELLM', source)

    @override_settings(OPENAI_API_KEY='test-key')
    def test_available_models_openai_only(self):
        """Test that available models only include OpenAI GPT-5 models."""
        available = self.manager.get_available_models()

        # Should have GPT-5 models
        self.assertIn('gpt-5', available['chat_models'])
        self.assertIn('gpt-5-mini', available['chat_models'])
        self.assertIn('gpt-5-nano', available['chat_models'])

        # Should have embedding model
        self.assertIn('text-embedding-3-small', available['embedding_models'])

        # Should NOT have Claude models
        for chat_model in available.get('chat_models', []):
            self.assertNotIn('claude', chat_model.lower())

    @patch('llm_services.services.base.settings_manager.SettingsManager.get_api_keys')
    def test_get_api_key_gpt5_models(self, mock_get_api_keys):
        """Test API key retrieval for GPT-5 models."""
        # Setup API key mock
        mock_get_api_keys.return_value = {'openai': 'test-key'}

        # Recreate manager with mocked API keys
        manager = APIClientManager()

        # GPT-5 models should return API key
        self.assertEqual(manager.get_api_key('gpt-5'), 'test-key')
        self.assertEqual(manager.get_api_key('gpt-5-mini'), 'test-key')
        self.assertEqual(manager.get_api_key('gpt-5-nano'), 'test-key')
        self.assertEqual(manager.get_api_key('text-embedding-3-small'), 'test-key')

    @override_settings(OPENAI_API_KEY='test-key')
    def test_validate_model_access(self):
        """Test model access validation."""
        # Should have access to GPT-5 models
        self.assertTrue(self.manager.validate_model_access('gpt-5'))
        self.assertTrue(self.manager.validate_model_access('gpt-5-mini'))

    @override_settings(OPENAI_API_KEY='test-key')
    @patch('llm_services.services.base.client_manager.completion')
    def test_sync_completion_call(self, mock_completion):
        """Test synchronous completion call using litellm."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Sync response"))]
        mock_completion.return_value = mock_response

        result = self.manager.make_completion_call_sync(
            "gpt-5",
            [{"role": "user", "content": "Test"}],
            max_tokens=100
        )

        # Verify litellm completion (sync) was called
        mock_completion.assert_called_once()
        self.assertEqual(mock_completion.call_args.kwargs['model'], 'gpt-5')
