"""
Model Performance Tracking Service.
Implements performance monitoring from ft-llm-003-flexible-model-selection.md
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q
from django.db import transaction
from asgiref.sync import sync_to_async

from ...models import ModelPerformanceMetric, ModelCostTracking

logger = logging.getLogger(__name__)


class ModelPerformanceTracker:
    """Track and analyze model performance metrics"""

    async def record_task(self,
                         model: str,
                         task_type: str,
                         processing_time_ms: int,
                         tokens_used: int,
                         cost_usd: float,
                         success: bool = True,
                         quality_score: Optional[float] = None,
                         user_id: Optional[int] = None,
                         complexity_score: Optional[float] = None,
                         selection_strategy: str = 'balanced',
                         fallback_used: bool = False,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a task execution for performance tracking"""

        try:
            # Create performance metric record (skip if user doesn't exist in test environment)
            try:
                # Use thread_sensitive=True to ensure database access in same thread as test transactions
                metric = await sync_to_async(ModelPerformanceMetric.objects.create, thread_sensitive=True)(
                    model_name=model,
                    task_type=task_type,
                    processing_time_ms=processing_time_ms,
                    tokens_used=tokens_used,
                    cost_usd=cost_usd,
                    quality_score=quality_score,
                    success=success,
                    user_id=user_id,
                    complexity_score=complexity_score,
                    selection_strategy=selection_strategy,
                    fallback_used=fallback_used,
                    metadata=metadata or {}
                )
            except Exception as db_error:
                if "foreign key constraint" in str(db_error).lower():
                    # Skip performance tracking if user doesn't exist (common in tests)
                    logger.debug(f"Skipping performance metric for non-existent user {user_id}")
                    return
                else:
                    raise db_error

            # Update daily cost tracking
            if user_id:
                await self._update_daily_cost_tracking(user_id, model, cost_usd, tokens_used)

            logger.debug(f"Recorded performance metric for {model}: {processing_time_ms}ms, ${cost_usd:.6f}")

        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")

    async def _update_daily_cost_tracking(self, user_id: int, model_name: str, cost_usd: float, tokens_used: int):
        """Update daily cost tracking for user and model"""
        from django.db import transaction

        today = timezone.now().date()

        @sync_to_async(thread_sensitive=True)
        def update_cost_tracking():
            with transaction.atomic():
                cost_tracking, created = ModelCostTracking.objects.get_or_create(
                    user_id=user_id,
                    date=today,
                    model_name=model_name,
                    defaults={
                        'total_cost_usd': cost_usd,
                        'generation_count': 1,
                        'avg_cost_per_generation': cost_usd,
                        'total_tokens_used': tokens_used,
                        'avg_tokens_per_generation': tokens_used
                    }
                )

                if not created:
                    # Update existing record
                    new_generation_count = cost_tracking.generation_count + 1
                    new_total_cost = float(cost_tracking.total_cost_usd) + cost_usd
                    new_total_tokens = int(cost_tracking.total_tokens_used) + tokens_used

                    cost_tracking.total_cost_usd = new_total_cost
                    cost_tracking.generation_count = new_generation_count
                    cost_tracking.avg_cost_per_generation = float(new_total_cost) / new_generation_count
                    cost_tracking.total_tokens_used = new_total_tokens
                    cost_tracking.avg_tokens_per_generation = int(float(new_total_tokens) / new_generation_count)
                    cost_tracking.save()

        await update_cost_tracking()


    def get_model_performance_summary(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for all models over specified days (sync version)"""
        return self._get_model_performance_summary_sync(days)

    async def get_model_performance_summary_async(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Async version of get_model_performance_summary for use in async contexts"""
        return await sync_to_async(self._get_model_performance_summary_sync)(days)

    def _get_model_performance_summary_sync(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Internal sync implementation of get_model_performance_summary"""
        since = timezone.now() - timedelta(days=days)

        metrics = ModelPerformanceMetric.objects.filter(created_at__gte=since)

        summary = {}
        for model_name in metrics.values_list('model_name', flat=True).distinct():
            model_metrics = metrics.filter(model_name=model_name)

            # Calculate aggregated metrics
            agg_data = model_metrics.aggregate(
                avg_processing_time_ms=Avg('processing_time_ms'),
                avg_cost_per_generation=Avg('cost_usd'),
                avg_quality_score=Avg('quality_score'),
                total_generations=Count('id'),
                success_count=Count('id', filter=Q(success=True)),
                total_tokens_used=Sum('tokens_used'),
                total_cost_usd=Sum('cost_usd')
            )

            # Calculate success rate
            success_rate = agg_data['success_count'] / agg_data['total_generations'] if agg_data['total_generations'] > 0 else 0

            # Get task type breakdown
            task_breakdown = {}
            for task_type in model_metrics.values_list('task_type', flat=True).distinct():
                task_metrics = model_metrics.filter(task_type=task_type).aggregate(
                    count=Count('id'),
                    avg_time=Avg('processing_time_ms'),
                    avg_cost=Avg('cost_usd')
                )
                task_breakdown[task_type] = task_metrics

            summary[model_name] = {
                'avg_processing_time_ms': round(agg_data['avg_processing_time_ms'] or 0, 2),
                'avg_cost_per_generation': round(agg_data['avg_cost_per_generation'] or 0, 6),
                'avg_quality_score': round(agg_data['avg_quality_score'] or 0, 3),
                'success_rate': round(success_rate, 3),
                'total_generations': agg_data['total_generations'],
                'total_tokens_used': agg_data['total_tokens_used'] or 0,
                'total_cost_usd': round(agg_data['total_cost_usd'] or 0, 6),
                'task_breakdown': task_breakdown
            }

        return summary

    def get_cost_analysis(self, user_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """Get cost analysis for user or system-wide (sync version)"""
        return self._get_cost_analysis_sync(user_id, days)

    async def get_cost_analysis_async(self, user_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """Async version of get_cost_analysis for use in async contexts"""
        return await sync_to_async(self._get_cost_analysis_sync)(user_id, days)

    def _get_cost_analysis_sync(self, user_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """Internal sync implementation of get_cost_analysis"""
        since = timezone.now().date() - timedelta(days=days)

        cost_data = ModelCostTracking.objects.filter(date__gte=since)
        if user_id:
            cost_data = cost_data.filter(user_id=user_id)

        # Aggregate by model
        model_costs = {}
        total_cost = 0
        total_generations = 0

        for record in cost_data:
            model_name = record.model_name
            if model_name not in model_costs:
                model_costs[model_name] = {
                    'total_cost_usd': 0,
                    'total_generations': 0,
                    'days_active': set()
                }

            model_costs[model_name]['total_cost_usd'] += float(record.total_cost_usd)
            model_costs[model_name]['total_generations'] += record.generation_count
            model_costs[model_name]['days_active'].add(record.date)

            total_cost += float(record.total_cost_usd)
            total_generations += record.generation_count

        # Calculate averages and convert sets to counts
        for model_data in model_costs.values():
            model_data['avg_cost_per_generation'] = (
                model_data['total_cost_usd'] / model_data['total_generations']
                if model_data['total_generations'] > 0 else 0
            )
            model_data['days_active'] = len(model_data['days_active'])

        return {
            'period_days': days,
            'user_id': user_id,
            'total_cost_usd': round(total_cost, 6),
            'total_generations': total_generations,
            'avg_cost_per_generation': round(total_cost / total_generations, 6) if total_generations > 0 else 0,
            'model_breakdown': {
                model: {
                    'total_cost_usd': round(data['total_cost_usd'], 6),
                    'total_generations': data['total_generations'],
                    'avg_cost_per_generation': round(data['avg_cost_per_generation'], 6),
                    'days_active': data['days_active'],
                    'cost_percentage': round((data['total_cost_usd'] / total_cost * 100), 2) if total_cost > 0 else 0
                }
                for model, data in model_costs.items()
            }
        }

    def get_user_budget_status(self, user_id: int) -> Dict[str, Any]:
        """Get budget usage status for a specific user"""
        from django.conf import settings

        budget_config = getattr(settings, 'MODEL_BUDGETS', {})
        daily_budget = budget_config.get('daily_budget_usd', 50.0)
        monthly_budget = budget_config.get('monthly_budget_usd', 1000.0)
        max_user_daily = budget_config.get('max_cost_per_user_daily', 5.0)

        # Get daily usage
        today = timezone.now().date()
        daily_cost = ModelCostTracking.objects.filter(
            user_id=user_id,
            date=today
        ).aggregate(total=Sum('total_cost_usd'))['total'] or 0

        # Get monthly usage
        month_start = today.replace(day=1)
        monthly_cost = ModelCostTracking.objects.filter(
            user_id=user_id,
            date__gte=month_start
        ).aggregate(total=Sum('total_cost_usd'))['total'] or 0

        return {
            'user_id': user_id,
            'daily_usage': {
                'spent_usd': round(daily_cost, 6),
                'budget_usd': max_user_daily,
                'usage_percentage': round((daily_cost / max_user_daily * 100), 2) if max_user_daily > 0 else 0,
                'remaining_usd': max(0, max_user_daily - daily_cost),
                'over_budget': daily_cost > max_user_daily
            },
            'monthly_usage': {
                'spent_usd': round(monthly_cost, 6),
                'budget_usd': monthly_budget,
                'usage_percentage': round((monthly_cost / monthly_budget * 100), 2) if monthly_budget > 0 else 0,
                'remaining_usd': max(0, monthly_budget - monthly_cost),
                'over_budget': monthly_cost > monthly_budget
            }
        }

    def get_performance_recommendations(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Generate performance-based recommendations"""
        performance_data = self._get_model_performance_summary_sync(days)
        recommendations = {
            'model_changes': [],
            'cost_optimizations': [],
            'quality_improvements': [],
            'reliability_issues': []
        }

        for model_name, metrics in performance_data.items():
            # Performance issues (> 5 seconds average)
            if metrics['avg_processing_time_ms'] > 5000:
                recommendations['model_changes'].append({
                    'model': model_name,
                    'issue': 'slow_performance',
                    'current_avg_ms': metrics['avg_processing_time_ms'],
                    'suggestion': f'Consider switching to faster model. Current: {metrics["avg_processing_time_ms"]}ms avg'
                })

            # Cost issues (> $0.20 per generation)
            if metrics['avg_cost_per_generation'] > 0.20:
                recommendations['cost_optimizations'].append({
                    'model': model_name,
                    'issue': 'high_cost',
                    'current_cost': metrics['avg_cost_per_generation'],
                    'suggestion': f'High cost per generation: ${metrics["avg_cost_per_generation"]:.6f}. Consider cost-effective alternative'
                })

            # Quality issues (< 0.75 quality score)
            if metrics['avg_quality_score'] and metrics['avg_quality_score'] < 0.75:
                recommendations['quality_improvements'].append({
                    'model': model_name,
                    'issue': 'low_quality',
                    'current_score': metrics['avg_quality_score'],
                    'suggestion': f'Low quality score: {metrics["avg_quality_score"]:.3f}. Consider higher-quality model'
                })

            # Reliability issues (< 95% success rate)
            if metrics['success_rate'] < 0.95:
                recommendations['reliability_issues'].append({
                    'model': model_name,
                    'issue': 'low_reliability',
                    'success_rate': metrics['success_rate'],
                    'suggestion': f'Low success rate: {metrics["success_rate"]:.1%}. Model may be unstable'
                })

        return recommendations

    def get_trend_analysis(self, model_name: str, days: int = 30) -> Dict[str, Any]:
        """Analyze performance trends for a specific model"""
        since = timezone.now() - timedelta(days=days)

        daily_metrics = []
        current_date = since.date()
        end_date = timezone.now().date()

        while current_date <= end_date:
            day_metrics = ModelPerformanceMetric.objects.filter(
                model_name=model_name,
                created_at__date=current_date
            ).aggregate(
                avg_time=Avg('processing_time_ms'),
                avg_cost=Avg('cost_usd'),
                avg_quality=Avg('quality_score'),
                total_calls=Count('id'),
                success_count=Count('id', filter=models.Q(success=True))
            )

            success_rate = (day_metrics['success_count'] / day_metrics['total_calls']
                          if day_metrics['total_calls'] > 0 else 0)

            daily_metrics.append({
                'date': current_date.isoformat(),
                'avg_processing_time_ms': day_metrics['avg_time'] or 0,
                'avg_cost_usd': day_metrics['avg_cost'] or 0,
                'avg_quality_score': day_metrics['avg_quality'],
                'total_calls': day_metrics['total_calls'],
                'success_rate': success_rate
            })

            current_date += timedelta(days=1)

        # Calculate trends
        recent_week = daily_metrics[-7:] if len(daily_metrics) >= 7 else daily_metrics
        previous_week = daily_metrics[-14:-7] if len(daily_metrics) >= 14 else []

        trends = {}
        if previous_week and recent_week:
            for metric in ['avg_processing_time_ms', 'avg_cost_usd', 'success_rate']:
                recent_avg = sum(d[metric] for d in recent_week if d[metric] is not None) / len(recent_week)
                previous_avg = sum(d[metric] for d in previous_week if d[metric] is not None) / len(previous_week)

                if previous_avg > 0:
                    change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
                    trends[metric] = {
                        'recent_avg': recent_avg,
                        'previous_avg': previous_avg,
                        'change_percentage': round(change_pct, 2),
                        'improving': change_pct < 0 if metric != 'success_rate' else change_pct > 0
                    }

        return {
            'model_name': model_name,
            'period_days': days,
            'daily_metrics': daily_metrics,
            'trends': trends
        }

    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Clean up old performance metrics to manage database size"""
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        deleted_count = ModelPerformanceMetric.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info(f"Cleaned up {deleted_count[0]} old performance metrics (older than {days_to_keep} days)")
        return deleted_count[0]

    def get_model_performance_stats(self, model_name: str, task_type: str):
        """Get performance statistics for a model and task type"""
        summary = self._get_model_performance_summary_sync()
        model_data = summary.get(model_name, {})
        task_breakdown = model_data.get('task_breakdown', {})
        return task_breakdown.get(task_type, {})

    def get_best_model_for_task(self, task_type: str, priority: str = 'balanced'):
        """Get the best model for a given task type"""
        summary = self._get_model_performance_summary_sync()

        best_model = None
        best_score = 0

        # Map priority aliases to canonical values
        priority_mapping = {
            'performance_first': 'quality',
            'cost_optimized': 'cost',
            'speed_first': 'speed'
        }
        canonical_priority = priority_mapping.get(priority, priority)

        for model_name, model_data in summary.items():
            task_data = model_data.get('task_breakdown', {}).get(task_type, {})
            if not task_data:
                continue

            # Calculate score based on priority
            if canonical_priority == 'speed':
                score = 1.0 / (float(task_data.get('avg_time', 1000)) / 1000.0)  # Lower time = higher score
            elif canonical_priority == 'quality':
                # Quality score is only available at model level, not task level
                score = float(model_data.get('avg_quality_score', 0))
            elif canonical_priority == 'cost':
                score = 1.0 / max(float(task_data.get('avg_cost', 0.001)), 0.001)  # Lower cost = higher score
            else:  # balanced
                time_score = 1.0 / (float(task_data.get('avg_time', 1000)) / 1000.0)
                quality_score = float(model_data.get('avg_quality_score', 0))  # Use model-level quality
                cost_score = 1.0 / max(float(task_data.get('avg_cost', 0.001)), 0.001)
                score = (time_score + quality_score + cost_score) / 3

            if score > best_score:
                best_score = score
                best_model = model_name

        return best_model