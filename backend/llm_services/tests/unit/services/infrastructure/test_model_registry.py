"""
Unit tests for Model Registry (infrastructure layer).
"""

from django.test import TestCase, tag

from llm_services.services.infrastructure.model_registry import ModelRegistry


@tag('fast', 'unit', 'llm_services')
class ModelRegistryTestCase(TestCase):
    def setUp(self):
        self.registry = ModelRegistry()

    def test_get_model_config(self):
        """Test getting model configuration"""
        config = self.registry.get_model_config('gpt-5')

        self.assertIsInstance(config, dict)
        self.assertIn('provider', config)
        self.assertIn('context_window', config)
        self.assertIn('cost_input', config)
        self.assertEqual(config['provider'], 'openai')

    def test_gpt5_models_available(self):
        """Test that GPT-5 models are in registry"""
        gpt5_config = self.registry.get_model_config('gpt-5')
        gpt5_mini_config = self.registry.get_model_config('gpt-5-mini')
        gpt5_nano_config = self.registry.get_model_config('gpt-5-nano')

        self.assertIsNotNone(gpt5_config, "gpt-5 should be in registry")
        self.assertIsNotNone(gpt5_mini_config, "gpt-5-mini should be in registry")
        self.assertIsNotNone(gpt5_nano_config, "gpt-5-nano should be in registry")

        # Verify they're OpenAI models
        self.assertEqual(gpt5_config['provider'], 'openai')
        self.assertEqual(gpt5_mini_config['provider'], 'openai')
        self.assertEqual(gpt5_nano_config['provider'], 'openai')

    def test_deprecated_models_removed(self):
        """Test that deprecated models are removed from active models"""
        all_chat = self.registry.MODELS["chat_models"]
        all_embedding = self.registry.MODELS["embedding_models"]

        # Filter out deprecated models
        active_chat = {k: v for k, v in all_chat.items() if not v.get("deprecated", False)}
        active_embedding = {k: v for k, v in all_embedding.items() if not v.get("deprecated", False)}

        # GPT-4o models should be removed
        self.assertNotIn("gpt-4o", active_chat, "gpt-4o should be removed")
        self.assertNotIn("gpt-4o-mini", active_chat, "gpt-4o-mini should be removed")
        self.assertNotIn("gpt-3.5-turbo", active_chat, "gpt-3.5-turbo should be removed")

        # Embedding models
        self.assertNotIn("text-embedding-3-large", active_embedding, "text-embedding-3-large should be removed")
        self.assertNotIn("text-embedding-ada-002", active_embedding, "text-embedding-ada-002 should be removed")

        # text-embedding-3-small should be the only embedding model
        self.assertIn("text-embedding-3-small", active_embedding, "text-embedding-3-small should exist")
        self.assertEqual(len(active_embedding), 1, "Should have exactly 1 embedding model")

    def test_anthropic_models_removed(self):
        """Test that all Anthropic/Claude models are removed (OpenAI-only architecture)"""
        all_chat = self.registry.MODELS["chat_models"]

        # Claude models should not exist in registry at all
        self.assertNotIn("claude-sonnet-4-20250514", all_chat, "claude-sonnet-4 should be completely removed")
        self.assertNotIn("claude-opus-4-1-20250805", all_chat, "claude-opus-4 should be completely removed")

        # Verify no Anthropic provider in any active model
        active_chat = {k: v for k, v in all_chat.items() if not v.get("deprecated", False)}
        for model_name, config in active_chat.items():
            self.assertNotEqual(config.get('provider'), 'anthropic',
                              f"Model {model_name} should not use Anthropic provider")

        # Verify only OpenAI provider exists for chat models
        providers = set(config.get('provider') for config in active_chat.values())
        self.assertEqual(providers, {'openai'}, "Only OpenAI provider should exist for chat models")

    def test_embedding_model_single(self):
        """Test that only text-embedding-3-small exists as embedding model"""
        all_embedding = self.registry.MODELS["embedding_models"]
        active_embedding = {k: v for k, v in all_embedding.items() if not v.get("deprecated", False)}

        self.assertIn("text-embedding-3-small", active_embedding)
        self.assertEqual(len(active_embedding), 1, "Should have exactly one embedding model")

    def test_get_models_by_criteria(self):
        """Test filtering models by criteria"""
        models = self.registry.get_models_by_criteria(
            model_type='chat_models',
            max_cost_per_1k_tokens=0.001
        )

        self.assertIsInstance(models, dict)
        self.assertTrue(len(models) > 0)

        # Verify all returned models meet criteria
        for model_name, config in models.items():
            self.assertLessEqual(config['cost_input'], 0.001)

    def test_get_model_stats(self):
        """Test getting model statistics"""
        stats = self.registry.get_model_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_chat_models', stats)
        self.assertIn('total_embedding_models', stats)
        self.assertIn('providers', stats)

        # Verify we have expected models
        self.assertGreater(stats['total_chat_models'], 0)
        self.assertEqual(stats['total_embedding_models'], 1, "Should have exactly 1 embedding model")
        self.assertIn('openai', stats['providers'])

    def test_gpt5_fallback_chain(self):
        """Test GPT-5 fallback chain"""
        # gpt-5 should fall back to gpt-5-mini
        fallback1 = self.registry.get_fallback_model('gpt-5', 'chat_models')
        self.assertEqual(fallback1, 'gpt-5-mini', "gpt-5 should fall back to gpt-5-mini")

        # gpt-5-mini should fall back to gpt-5-nano
        fallback2 = self.registry.get_fallback_model('gpt-5-mini', 'chat_models')
        self.assertEqual(fallback2, 'gpt-5-nano', "gpt-5-mini should fall back to gpt-5-nano")

    def test_model_count_reduced(self):
        """Test that total active models are reduced to 4 (3 chat + 1 embedding)"""
        all_chat = self.registry.MODELS["chat_models"]
        all_embedding = self.registry.MODELS["embedding_models"]

        # Filter active models (excluding deprecated and Claude models for OpenAI count)
        active_chat = {k: v for k, v in all_chat.items() if not v.get("deprecated", False)}
        active_embedding = {k: v for k, v in all_embedding.items() if not v.get("deprecated", False)}

        openai_chat = {k: v for k, v in active_chat.items() if v.get('provider') == 'openai'}

        # Should have 3 OpenAI chat models (gpt-5, gpt-5-mini, gpt-5-nano)
        self.assertEqual(len(openai_chat), 3, "Should have 3 OpenAI chat models")

        # Should have 1 embedding model
        self.assertEqual(len(active_embedding), 1, "Should have 1 embedding model")