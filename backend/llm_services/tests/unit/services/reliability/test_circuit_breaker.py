"""
Unit tests for Circuit Breaker Manager (reliability layer).
"""

from django.test import TestCase, tag
from django.utils import timezone
from asgiref.sync import sync_to_async

from llm_services.services.reliability.circuit_breaker import CircuitBreakerManager
from llm_services.models import CircuitBreakerState


@tag('medium', 'integration', 'llm_services')
class CircuitBreakerManagerTestCase(TestCase):
    def setUp(self):
        self.service = CircuitBreakerManager()

    async def test_record_success(self):
        """Test recording successful request"""
        model_name = f'test-record-success-{self._testMethodName}'
        await self.service.record_success(model_name)

        breaker = await sync_to_async(CircuitBreakerState.objects.get)(model_name=model_name)
        self.assertEqual(breaker.state, 'closed')
        self.assertEqual(breaker.failure_count, 0)

    async def test_record_failure(self):
        """Test recording failed request"""
        # Create initial breaker
        await sync_to_async(CircuitBreakerState.objects.create)(
            model_name='test-model',
            failure_count=0,
            state='closed'
        )

        # Record failures
        for i in range(5):  # Default threshold
            await self.service.record_failure('test-model')

        breaker = await sync_to_async(CircuitBreakerState.objects.get)(model_name='test-model')
        self.assertEqual(breaker.state, 'open')
        self.assertEqual(breaker.failure_count, 5)

    async def test_can_attempt_request(self):
        """Test request permission checking"""
        # Closed circuit should allow requests
        result = await self.service.can_attempt_request('new-model')
        self.assertTrue(result)

        # Create open circuit
        await sync_to_async(CircuitBreakerState.objects.create)(
            model_name='broken-model',
            state='open',
            last_failure=timezone.now()
        )

        result = await self.service.can_attempt_request('broken-model')
        self.assertFalse(result)

    def test_get_breaker_status(self):
        """Test getting breaker status"""
        CircuitBreakerState.objects.create(
            model_name='test-model',
            state='closed',
            failure_count=2
        )

        status = self.service.get_breaker_status('test-model')

        self.assertEqual(status['state'], 'closed')
        self.assertEqual(status['failure_count'], 2)
        self.assertEqual(status['is_healthy'], True)