"""
Circuit Breaker Service for LLM providers.
Implements reliability patterns from ft-llm-003-flexible-model-selection.md
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async

from ...models import CircuitBreakerState

logger = logging.getLogger(__name__)


class CircuitBreakerManager:
    """Manage circuit breaker states for LLM models to handle failures gracefully"""

    def __init__(self):
        self.config = getattr(settings, 'CIRCUIT_BREAKER_SETTINGS', {})
        self.failure_threshold = self.config.get('failure_threshold', 5)
        self.timeout_duration = self.config.get('timeout_duration', 30)  # seconds
        self.retry_attempts = self.config.get('retry_attempts', 3)

    @sync_to_async
    def can_attempt_request(self, model_name: str) -> bool:
        """Check if we should attempt a request to the given model"""
        try:
            breaker, created = CircuitBreakerState.objects.get_or_create(
                model_name=model_name,
                defaults={
                    'failure_threshold': self.failure_threshold,
                    'timeout_duration': self.timeout_duration
                }
            )

            return breaker.should_attempt_request()

        except Exception as e:
            logger.error(f"Error checking circuit breaker for {model_name}: {e}")
            # Default to allowing requests if breaker check fails
            return True

    @sync_to_async
    def record_success(self, model_name: str) -> None:
        """Record a successful request for the model"""
        try:
            breaker, created = CircuitBreakerState.objects.get_or_create(
                model_name=model_name,
                defaults={
                    'failure_threshold': self.failure_threshold,
                    'timeout_duration': self.timeout_duration
                }
            )

            breaker.record_success()
            logger.debug(f"Circuit breaker for {model_name}: recorded success, reset to closed state")

        except Exception as e:
            logger.error(f"Error recording success for {model_name}: {e}")

    @sync_to_async
    def record_failure(self, model_name: str, error_type: Optional[str] = None) -> None:
        """Record a failure for the model"""
        try:
            breaker, created = CircuitBreakerState.objects.get_or_create(
                model_name=model_name,
                defaults={
                    'failure_threshold': self.failure_threshold,
                    'timeout_duration': self.timeout_duration
                }
            )

            breaker.record_failure()

            # Log the state change
            if breaker.state == 'open':
                logger.warning(f"Circuit breaker for {model_name} is now OPEN after {breaker.failure_count} failures")
            else:
                logger.debug(f"Circuit breaker for {model_name}: recorded failure ({breaker.failure_count}/{breaker.failure_threshold})")

        except Exception as e:
            logger.error(f"Error recording failure for {model_name}: {e}")

    def get_breaker_status(self, model_name: str) -> Dict[str, any]:
        """Get current status of circuit breaker for a model (sync version)"""
        return self._get_breaker_status_sync(model_name)

    async def get_breaker_status_async(self, model_name: str) -> Dict[str, any]:
        """Async version of get_breaker_status for use in async contexts"""
        return await sync_to_async(self._get_breaker_status_sync)(model_name)

    def get_all_breaker_statuses(self) -> Dict[str, Dict[str, any]]:
        """Get status of all circuit breakers (sync version)"""
        return self._get_all_breaker_statuses_sync()

    async def get_all_breaker_statuses_async(self) -> Dict[str, Dict[str, any]]:
        """Async version of get_all_breaker_statuses for use in async contexts"""
        return await sync_to_async(self._get_all_breaker_statuses_sync)()

    def _get_all_breaker_statuses_sync(self) -> Dict[str, Dict[str, any]]:
        """Internal sync implementation of get_all_breaker_statuses"""
        statuses = {}

        for breaker in CircuitBreakerState.objects.all():
            # Call the inner sync implementation to avoid double wrapping
            statuses[breaker.model_name] = self._get_breaker_status_sync(breaker.model_name)

        return statuses

    def _get_breaker_status_sync(self, model_name: str) -> Dict[str, any]:
        """Internal sync implementation of get_breaker_status"""
        try:
            breaker = CircuitBreakerState.objects.get(model_name=model_name)

            time_since_failure = None
            if breaker.last_failure:
                time_since_failure = (timezone.now() - breaker.last_failure).total_seconds()

            return {
                'model_name': model_name,
                'state': breaker.state,
                'failure_count': breaker.failure_count,
                'failure_threshold': breaker.failure_threshold,
                'last_failure': breaker.last_failure.isoformat() if breaker.last_failure else None,
                'time_since_failure_seconds': time_since_failure,
                'timeout_duration_seconds': breaker.timeout_duration,
                'can_attempt_request': breaker.should_attempt_request(),
                'time_until_retry': max(0, breaker.timeout_duration - time_since_failure) if time_since_failure else 0,
                'is_healthy': breaker.state == 'closed'
            }

        except CircuitBreakerState.DoesNotExist:
            return {
                'model_name': model_name,
                'state': 'closed',
                'failure_count': 0,
                'failure_threshold': self.failure_threshold,
                'last_failure': None,
                'time_since_failure_seconds': None,
                'timeout_duration_seconds': self.timeout_duration,
                'can_attempt_request': True,
                'time_until_retry': 0,
                'is_healthy': True
            }

    def reset_breaker(self, model_name: str) -> bool:
        """Manually reset a circuit breaker (admin function)"""
        try:
            breaker = CircuitBreakerState.objects.get(model_name=model_name)
            breaker.record_success()  # This resets the breaker
            logger.info(f"Circuit breaker for {model_name} manually reset")
            return True

        except CircuitBreakerState.DoesNotExist:
            logger.warning(f"No circuit breaker found for {model_name} to reset")
            return False

    def get_failure_statistics(self, days: int = 7) -> Dict[str, any]:
        """Get failure statistics across all models (sync version)"""
        return self._get_failure_statistics_sync(days)

    async def get_failure_statistics_async(self, days: int = 7) -> Dict[str, any]:
        """Async version of get_failure_statistics for use in async contexts"""
        return await sync_to_async(self._get_failure_statistics_sync)(days)

    def _get_failure_statistics_sync(self, days: int = 7) -> Dict[str, any]:
        """Internal sync implementation of get_failure_statistics"""
        since = timezone.now() - timedelta(days=days)

        breakers = CircuitBreakerState.objects.all()
        stats = {
            'total_models': breakers.count(),
            'models_with_failures': breakers.filter(failure_count__gt=0).count(),
            'models_circuit_open': breakers.filter(state='open').count(),
            'models_half_open': breakers.filter(state='half_open').count(),
            'recent_failures': breakers.filter(last_failure__gte=since).count(),
            'model_details': {}
        }

        for breaker in breakers:
            stats['model_details'][breaker.model_name] = {
                'state': breaker.state,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure.isoformat() if breaker.last_failure else None,
                'uptime_status': 'healthy' if breaker.state == 'closed' and breaker.failure_count == 0 else
                               'degraded' if breaker.state == 'half_open' else
                               'down' if breaker.state == 'open' else 'unknown'
            }

        return stats

    def should_use_fallback_strategy(self, primary_model: str, fallback_model: str) -> bool:
        """Determine if we should use fallback strategy based on circuit breaker states"""
        primary_status = self._get_breaker_status_sync(primary_model)
        fallback_status = self._get_breaker_status_sync(fallback_model)

        # Use fallback if primary is down and fallback is available
        primary_available = primary_status['can_attempt_request']
        fallback_available = fallback_status['can_attempt_request']

        if not primary_available and fallback_available:
            logger.info(f"Using fallback strategy: {primary_model} -> {fallback_model}")
            return True

        return False

    def get_recommended_models(self, task_type: str = None) -> List[str]:
        """Get list of currently recommended models (those with closed circuit breakers)"""
        from ..infrastructure.model_registry import ModelRegistry

        registry = ModelRegistry()
        all_models = registry.MODELS.get('chat_models', {})

        # Filter models with closed circuit breakers
        available_models = []

        for model_name in all_models.keys():
            if not all_models[model_name].get('deprecated', False):
                status = self._get_breaker_status_sync(model_name)
                if status['can_attempt_request']:
                    available_models.append(model_name)

        # Sort by reliability (models with fewer failures first)
        available_models.sort(key=lambda m: self._get_breaker_status_sync(m)['failure_count'])

        return available_models

    def cleanup_old_states(self, days_to_keep: int = 30):
        """Clean up old circuit breaker states that haven't been used recently"""
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Only clean up states that are closed with no recent failures
        deleted_count = CircuitBreakerState.objects.filter(
            state='closed',
            failure_count=0,
            updated_at__lt=cutoff_date
        ).delete()

        logger.info(f"Cleaned up {deleted_count[0]} old circuit breaker states")
        return deleted_count[0]

    def get_health_check_summary(self) -> Dict[str, any]:
        """Get overall health summary for monitoring/alerting (sync version)"""
        # Call the sync internal implementations
        stats = self._get_failure_statistics_sync()
        breaker_statuses = self._get_all_breaker_statuses_sync()

        # Determine overall system health
        total_models = len(breaker_statuses)
        healthy_models = sum(1 for status in breaker_statuses.values()
                           if status['state'] == 'closed' and status['failure_count'] == 0)

        degraded_models = sum(1 for status in breaker_statuses.values()
                            if status['state'] == 'half_open' or
                            (status['state'] == 'closed' and status['failure_count'] > 0))

        down_models = sum(1 for status in breaker_statuses.values()
                         if status['state'] == 'open')

        # Calculate overall health score (0-1)
        if total_models == 0:
            health_score = 1.0
        else:
            health_score = (healthy_models + (degraded_models * 0.5)) / total_models

        # Determine health status
        if health_score >= 0.9:
            health_status = 'healthy'
        elif health_score >= 0.7:
            health_status = 'degraded'
        elif health_score >= 0.5:
            health_status = 'unstable'
        else:
            health_status = 'critical'

        return {
            'health_status': health_status,
            'health_score': round(health_score, 3),
            'total_models': total_models,
            'healthy_models': healthy_models,
            'degraded_models': degraded_models,
            'down_models': down_models,
            'available_models': [model for model, status in breaker_statuses.items()
                               if status['can_attempt_request']],
            'recommendations': self._generate_health_recommendations(health_status, breaker_statuses)
        }

    def _generate_health_recommendations(self, health_status: str, breaker_statuses: Dict) -> List[str]:
        """Generate recommendations based on current health status"""
        recommendations = []

        if health_status == 'critical':
            recommendations.append("URGENT: Multiple models are down. Check API keys and service status.")

        elif health_status == 'unstable':
            recommendations.append("WARNING: System reliability is compromised. Consider fallback strategies.")

        # Check for models that have been down for a long time
        for model, status in breaker_statuses.items():
            if status['state'] == 'open' and status['time_since_failure_seconds']:
                if status['time_since_failure_seconds'] > 3600:  # 1 hour
                    recommendations.append(f"Model {model} has been down for over 1 hour. Investigate service issues.")

        # Check for models with high failure rates
        for model, status in breaker_statuses.items():
            if status['failure_count'] >= status['failure_threshold'] * 0.8:
                recommendations.append(f"Model {model} is approaching failure threshold. Monitor closely.")

        return recommendations