"""
Unit tests for LLM services serializers.

NOTE (ft-007): JobDescriptionEmbedding, ArtifactChunk tests removed - models deleted in embeddings removal.
"""

from decimal import Decimal
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone

from llm_services.models import (
    ModelPerformanceMetric,
    CircuitBreakerState,
    ModelCostTracking
)
from llm_services.serializers import (
    ModelPerformanceMetricSerializer,
    CircuitBreakerStateSerializer,
    ModelCostTrackingSerializer,
    ModelStatsSerializer,
    ModelSelectionRequestSerializer,
    ModelSelectionResponseSerializer,
    SystemHealthSerializer
)

User = get_user_model()


@tag('medium', 'integration', 'llm_services')
class ModelPerformanceMetricSerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='metric_testuser',
            email='metric_test@example.com',
            password='testpass123'
        )

        self.metric = ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1500,
            tokens_used=800,
            cost_usd=Decimal('0.008'),
            quality_score=Decimal('0.85'),
            success=True,
            complexity_score=Decimal('0.6'),
            selection_strategy='balanced',
            fallback_used=False,
            metadata={'test': 'data'},
            user=self.user
        )

    def test_serialize_metric(self):
        """Test serializing a performance metric"""
        serializer = ModelPerformanceMetricSerializer(self.metric)
        data = serializer.data

        self.assertEqual(data['model_name'], 'gpt-5')
        self.assertEqual(data['task_type'], 'cv_generation')
        self.assertEqual(data['processing_time_ms'], 1500)
        self.assertEqual(data['tokens_used'], 800)
        self.assertEqual(data['cost_usd'], '0.008000')
        self.assertEqual(data['quality_score'], '0.85')
        self.assertTrue(data['success'])
        self.assertEqual(data['user_email'], 'metric_test@example.com')
        self.assertEqual(data['metadata'], {'test': 'data'})

    def test_deserialize_metric(self):
        """Test deserializing metric data"""
        data = {
            'model_name': 'claude-sonnet-4',
            'task_type': 'job_parsing',
            'processing_time_ms': 2000,
            'tokens_used': 1200,
            'cost_usd': '0.012000',
            'quality_score': '0.90',
            'success': True,
            'complexity_score': '0.7',
            'selection_strategy': 'performance_first',
            'fallback_used': True,
            'metadata': {'parser': 'v2'}
        }

        serializer = ModelPerformanceMetricSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['model_name'], 'claude-sonnet-4')
        self.assertEqual(validated_data['cost_usd'], Decimal('0.012000'))
        self.assertTrue(validated_data['fallback_used'])

    def test_validation_errors(self):
        """Test serializer validation"""
        serializer = ModelPerformanceMetricSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('model_name', serializer.errors)
        self.assertIn('task_type', serializer.errors)


@tag('medium', 'integration', 'llm_services')
class CircuitBreakerStateSerializerTestCase(TestCase):
    def setUp(self):
        self.breaker = CircuitBreakerState.objects.create(
            model_name=f'gpt-5-{self.__class__.__name__}',
            failure_count=2,
            state='closed',
            failure_threshold=5,
            timeout_duration=30
        )

    def test_serialize_circuit_breaker(self):
        """Test serializing circuit breaker state"""
        serializer = CircuitBreakerStateSerializer(self.breaker)
        data = serializer.data

        self.assertEqual(data['model_name'], f'gpt-5-{self.__class__.__name__}')
        self.assertEqual(data['failure_count'], 2)
        self.assertEqual(data['state'], 'closed')
        self.assertEqual(data['state_display'], 'Closed')
        self.assertEqual(data['failure_threshold'], 5)
        self.assertEqual(data['timeout_duration'], 30)
        self.assertTrue(data['is_healthy'])

    def test_unhealthy_circuit_breaker(self):
        """Test serializing unhealthy circuit breaker"""
        self.breaker.state = 'open'
        self.breaker.save()

        serializer = CircuitBreakerStateSerializer(self.breaker)
        data = serializer.data

        self.assertEqual(data['state'], 'open')
        self.assertEqual(data['state_display'], 'Open')
        self.assertFalse(data['is_healthy'])

    def test_deserialize_circuit_breaker(self):
        """Test deserializing circuit breaker data"""
        data = {
            'model_name': 'new-model',
            'failure_count': 0,
            'state': 'closed',
            'failure_threshold': 10,
            'timeout_duration': 60
        }

        serializer = CircuitBreakerStateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['model_name'], 'new-model')
        self.assertEqual(validated_data['failure_threshold'], 10)


@tag('medium', 'integration', 'llm_services')
class ModelCostTrackingSerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cost_testuser',
            email='cost_test@example.com',
            password='testpass123'
        )

        self.cost_entry = ModelCostTracking.objects.create(
            user=self.user,
            date=timezone.now().date(),
            model_name='gpt-5',
            total_cost_usd=Decimal('0.150'),
            generation_count=15,
            avg_cost_per_generation=Decimal('0.010'),
            total_tokens_used=15000,
            avg_tokens_per_generation=1000
        )

    def test_serialize_cost_tracking(self):
        """Test serializing cost tracking data"""
        serializer = ModelCostTrackingSerializer(self.cost_entry)
        data = serializer.data

        self.assertEqual(data['user_email'], 'cost_test@example.com')
        self.assertEqual(data['model_name'], 'gpt-5')
        self.assertEqual(data['total_cost_usd'], '0.150000')
        self.assertEqual(data['generation_count'], 15)
        self.assertEqual(data['avg_cost_per_generation'], '0.010000')
        self.assertEqual(data['total_tokens_used'], 15000)
        self.assertEqual(data['avg_tokens_per_generation'], 1000)

    def test_deserialize_cost_tracking(self):
        """Test deserializing cost tracking data"""
        data = {
            'date': '2025-01-15',
            'model_name': 'claude-sonnet-4',
            'total_cost_usd': '0.250000',
            'generation_count': 10,
            'avg_cost_per_generation': '0.025000',
            'total_tokens_used': 5000,
            'avg_tokens_per_generation': 500
        }

        serializer = ModelCostTrackingSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['model_name'], 'claude-sonnet-4')
        self.assertEqual(validated_data['total_cost_usd'], Decimal('0.250000'))


@tag('medium', 'integration', 'llm_services')
class ModelStatsSerializerTestCase(TestCase):
    def test_serialize_model_stats(self):
        """Test serializing model statistics"""
        stats_data = {
            'model_name': 'gpt-5',
            'total_requests': 150,
            'success_rate': 96.5,
            'avg_processing_time_ms': 1250.0,
            'total_cost_usd': Decimal('1.275'),
            'avg_quality_score': 0.85,
            'last_used': timezone.now()
        }

        serializer = ModelStatsSerializer(data=stats_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['model_name'], 'gpt-5')
        self.assertEqual(validated_data['total_requests'], 150)
        self.assertEqual(validated_data['success_rate'], 96.5)


@tag('medium', 'integration', 'llm_services')
class ModelSelectionRequestSerializerTestCase(TestCase):
    def test_valid_request_data(self):
        """Test valid model selection request"""
        data = {
            'task_type': 'cv_generation',
            'complexity_score': 0.7,
            'user_budget': '0.05',
            'strategy': 'balanced'
        }

        serializer = ModelSelectionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['task_type'], 'cv_generation')
        self.assertEqual(validated_data['complexity_score'], 0.7)
        self.assertEqual(validated_data['strategy'], 'balanced')

    def test_invalid_task_type(self):
        """Test invalid task type"""
        data = {
            'task_type': 'invalid_task',
            'complexity_score': 0.5
        }

        serializer = ModelSelectionRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('task_type', serializer.errors)

    def test_invalid_complexity_score(self):
        """Test invalid complexity score"""
        data = {
            'task_type': 'cv_generation',
            'complexity_score': 1.5
        }

        serializer = ModelSelectionRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('complexity_score', serializer.errors)

    def test_optional_fields(self):
        """Test that optional fields work correctly"""
        data = {
            'task_type': 'cv_generation'  # ft-007: Changed from 'embedding' (removed)
        }

        serializer = ModelSelectionRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())


@tag('medium', 'integration', 'llm_services')
class ModelSelectionResponseSerializerTestCase(TestCase):
    def test_serialize_selection_response(self):
        """Test serializing model selection response"""
        response_data = {
            'selected_model': 'gpt-5',
            'reasoning': 'Selected GPT-5 for balanced performance and cost',
            'estimated_cost_usd': Decimal('0.025'),
            'fallback_models': ['gpt-5-mini', 'claude-sonnet-4']
        }

        serializer = ModelSelectionResponseSerializer(data=response_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['selected_model'], 'gpt-5')
        self.assertEqual(len(validated_data['fallback_models']), 2)


@tag('medium', 'integration', 'llm_services')
class SystemHealthSerializerTestCase(TestCase):
    def test_serialize_system_health(self):
        """Test serializing system health data"""
        health_data = {
            'healthy_models': 5,
            'unhealthy_models': 1,
            'circuit_breakers_open': 1,
            'total_cost_today': Decimal('0.45'),
            'avg_response_time_ms': 1150.2,
            'success_rate': 95.5
        }

        serializer = SystemHealthSerializer(data=health_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['healthy_models'], 5)
        self.assertEqual(validated_data['unhealthy_models'], 1)
        self.assertEqual(validated_data['success_rate'], 95.5)
