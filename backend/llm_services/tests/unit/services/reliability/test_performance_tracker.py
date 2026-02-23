"""
Unit tests for Model Performance Tracker (reliability layer).
"""

from decimal import Decimal
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from llm_services.services.reliability.performance_tracker import ModelPerformanceTracker
from llm_services.models import ModelPerformanceMetric

User = get_user_model()


@tag('fast', 'unit', 'llm_services')
class ModelPerformanceTrackerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tracker = ModelPerformanceTracker()

    async def test_record_performance(self):
        """Test recording performance metric"""
        # Verify user exists first (using sync_to_async)
        self.assertTrue(self.user.id is not None)
        user_exists = await sync_to_async(User.objects.filter(id=self.user.id).exists)()
        self.assertTrue(user_exists)

        # Call the async method directly instead of the sync wrapper
        await self.tracker.record_task(
            model='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1500,
            tokens_used=800,
            cost_usd=Decimal('0.008'),
            success=True,
            quality_score=0.85,
            user_id=self.user.id
        )

        # Check that the metric was actually created (using sync_to_async)
        metrics_count = await sync_to_async(
            lambda: ModelPerformanceMetric.objects.filter(
                model_name='gpt-5',
                task_type='cv_generation'
            ).count()
        )()
        self.assertEqual(metrics_count, 1)

        metric = await sync_to_async(
            lambda: ModelPerformanceMetric.objects.filter(
                model_name='gpt-5',
                task_type='cv_generation'
            ).first()
        )()
        self.assertEqual(metric.processing_time_ms, 1500)
        self.assertEqual(metric.success, True)

    def test_get_model_performance_stats(self):
        """Test getting performance statistics"""
        # Create test metrics
        ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1000,
            cost_usd=Decimal('0.005'),
            success=True,
            user=self.user
        )
        ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1500,
            cost_usd=Decimal('0.008'),
            success=True,
            user=self.user
        )

        stats = self.tracker.get_model_performance_stats('gpt-5', 'cv_generation')

        self.assertEqual(stats['count'], 2)
        # Note: success_rate is not available in task breakdown, only at model level
        self.assertEqual(stats['avg_time'], 1250.0)

    def test_get_best_model_for_task(self):
        """Test best model selection"""
        # Create metrics for different models
        ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1000,
            cost_usd=Decimal('0.008'),
            success=True,
            quality_score=Decimal('0.9'),
            user=self.user
        )
        ModelPerformanceMetric.objects.create(
            model_name='gpt-5-mini',
            task_type='cv_generation',
            processing_time_ms=800,
            cost_usd=Decimal('0.002'),
            success=True,
            quality_score=Decimal('0.8'),
            user=self.user
        )

        # Test different strategies - method now returns just the model name
        best_performance = self.tracker.get_best_model_for_task(
            'cv_generation', priority='quality'
        )
        best_cost = self.tracker.get_best_model_for_task(
            'cv_generation', priority='cost'
        )

        self.assertEqual(best_performance, 'gpt-5')  # Higher quality score
        self.assertEqual(best_cost, 'gpt-5-mini')  # Lower cost