"""
Unit tests for BaseLLMService abstract class.
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, tag
from llm_services.services.base.base_service import BaseLLMService


class ConcreteService(BaseLLMService):
    """Concrete implementation of BaseLLMService for testing."""

    def _get_service_config(self):
        return {
            'api_key': 'test-key',
            'timeout': 30,
            'max_retries': 3
        }


@tag('medium', 'integration', 'llm_services')
class BaseLLMServiceTestCase(TestCase):
    """Test suite for BaseLLMService"""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ConcreteService()

    def test_initialization(self):
        """Test service initialization."""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.settings_manager)
        self.assertIsNotNone(self.service.client_manager)
        self.assertIsNotNone(self.service.task_executor)
        self.assertIsNotNone(self.service.circuit_breaker)
        self.assertIsNotNone(self.service.registry)
        self.assertIsNotNone(self.service.model_selector)
        self.assertIsNotNone(self.service.performance_tracker)

    def test_get_service_config(self):
        """Test getting service configuration."""
        config = self.service._get_service_config()
        self.assertIsInstance(config, dict)
        self.assertIn('api_key', config)
        self.assertEqual(config['api_key'], 'test-key')

    def test_client_manager_integration(self):
        """Test integration with ClientManager."""
        service = ConcreteService()

        # Verify client_manager is properly initialized
        self.assertIsNotNone(service.client_manager)

        # Verify client_manager is an instance of APIClientManager
        from llm_services.services.base.client_manager import APIClientManager
        self.assertIsInstance(service.client_manager, APIClientManager)

    def test_service_lifecycle(self):
        """Test service creation and destruction."""
        service = ConcreteService()
        self.assertIsNotNone(service)

        # Service should be reusable
        config1 = service._get_service_config()
        config2 = service._get_service_config()
        self.assertEqual(config1, config2)

    # REMOVED: test_abstract_method_enforcement
    # BaseLLMService is no longer an abstract base class - it's a concrete base class
    # that can be instantiated directly. The architecture changed to use composition
    # instead of inheritance for service configuration.
