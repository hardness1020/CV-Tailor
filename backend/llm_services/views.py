"""
DRF API views for LLM services management.
"""

from django.db.models import Avg, Sum, Count, Q, Max
from django.utils import timezone
from datetime import timedelta, date
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from .models import (
    ModelPerformanceMetric,
    EnhancedEvidence,
    ModelCostTracking,
    CircuitBreakerState
)
from .serializers import (
    ModelPerformanceMetricSerializer,
    CircuitBreakerStateSerializer,
    ModelCostTrackingSerializer,
    EnhancedEvidenceSerializer,
    EnhancedEvidenceUpdateSerializer,
    ModelStatsSerializer,
    ModelSelectionRequestSerializer,
    ModelSelectionResponseSerializer,
    SystemHealthSerializer
)

# Service layer imports (updated for SPEC-20250930)
from .services.core.tailored_content_service import TailoredContentService
from .services.core.artifact_ranking_service import ArtifactRankingService
from .services.infrastructure.model_registry import ModelRegistry
# from .services.infrastructure.model_selector import ModelSelector


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ModelPerformanceMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing model performance metrics.
    """
    serializer_class = ModelPerformanceMetricSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['model_name', 'task_type', 'success', 'selection_strategy']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = ModelPerformanceMetric.objects.select_related('user')

        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get performance summary statistics"""
        queryset = self.get_queryset()

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        today_metrics = queryset.filter(created_at__date=today)
        yesterday_metrics = queryset.filter(created_at__date=yesterday)

        summary_data = {
            'today': {
                'total_requests': today_metrics.count(),
                'success_rate': self._calculate_success_rate(today_metrics),
                'avg_cost': today_metrics.aggregate(avg=Avg('cost_usd'))['avg'] or 0,
                'total_cost': today_metrics.aggregate(sum=Sum('cost_usd'))['sum'] or 0,
            },
            'yesterday': {
                'total_requests': yesterday_metrics.count(),
                'success_rate': self._calculate_success_rate(yesterday_metrics),
                'avg_cost': yesterday_metrics.aggregate(avg=Avg('cost_usd'))['avg'] or 0,
                'total_cost': yesterday_metrics.aggregate(sum=Sum('cost_usd'))['sum'] or 0,
            }
        }

        return Response(summary_data)

    def _calculate_success_rate(self, queryset):
        total = queryset.count()
        if total == 0:
            return 0.0
        successful = queryset.filter(success=True).count()
        return (successful / total) * 100


class CircuitBreakerStateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing circuit breaker states.
    """
    queryset = CircuitBreakerState.objects.all()
    serializer_class = CircuitBreakerStateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'model_name'

    @action(detail=True, methods=['post'])
    def reset(self, request, model_name=None):
        """Reset a circuit breaker"""
        try:
            breaker = self.get_object()
            breaker.record_success()
            return Response({
                'message': f'Circuit breaker for {model_name} has been reset',
                'new_state': breaker.state
            })
        except CircuitBreakerState.DoesNotExist:
            return Response(
                {'error': 'Circuit breaker not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def health_status(self, request):
        """Get overall health status of all models"""
        breakers = self.get_queryset()

        health_data = {
            'total_models': breakers.count(),
            'healthy_models': breakers.filter(state='closed').count(),
            'unhealthy_models': breakers.exclude(state='closed').count(),
            'models_by_state': {
                state_choice[0]: breakers.filter(state=state_choice[0]).count()
                for state_choice in CircuitBreakerState._meta.get_field('state').choices
            },
            'recent_failures': list(breakers.filter(
                last_failure__gte=timezone.now() - timedelta(hours=24)
            ).values('model_name', 'failure_count', 'last_failure', 'state'))
        }

        return Response(health_data)


class ModelCostTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing cost tracking data.
    """
    serializer_class = ModelCostTrackingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['model_name', 'date']
    ordering = ['-date']

    def get_queryset(self):
        queryset = ModelCostTracking.objects.select_related('user')

        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        return queryset

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """Get monthly cost summary"""
        queryset = self.get_queryset()
        current_month = date.today().replace(day=1)

        monthly_data = queryset.filter(
            date__gte=current_month
        ).values('model_name').annotate(
            total_cost=Sum('total_cost_usd'),
            total_generations=Sum('generation_count'),
            avg_cost_per_generation=Avg('avg_cost_per_generation')
        ).order_by('-total_cost')

        return Response({
            'month': current_month.strftime('%Y-%m'),
            'models': list(monthly_data)
        })


class EnhancedEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing enhanced artifacts.
    Supports PATCH for updating processed_content fields (user edits to AI-generated content).
    """
    serializer_class = EnhancedEvidenceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['content_type', 'processing_strategy']
    ordering = ['-updated_at']
    # Allow only list, retrieve, partial_update (PATCH)
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        """Use update serializer for PATCH requests"""
        if self.action in ['partial_update', 'update']:
            return EnhancedEvidenceUpdateSerializer
        return EnhancedEvidenceSerializer

    def get_queryset(self):
        queryset = EnhancedEvidence.objects.select_related('user', 'evidence')

        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        return queryset

    def perform_update(self, serializer):
        """Ensure user owns the enhanced evidence before updating"""
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to edit this enhanced evidence")
        serializer.save()

    @action(detail=False, methods=['get'], url_path='by-evidence/(?P<evidence_id>[^/.]+)')
    def by_evidence(self, request, evidence_id=None):
        """Get enhanced evidence for a specific evidence ID"""
        try:
            enhanced_evidence = EnhancedEvidence.objects.select_related('user', 'evidence').get(
                evidence_id=evidence_id,
                user=request.user
            )
            serializer = self.get_serializer(enhanced_evidence)
            return Response(serializer.data)
        except EnhancedEvidence.DoesNotExist:
            return Response(
                {'detail': 'Enhanced evidence not found for this evidence.'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_stats(request):
    """
    Get aggregated statistics for all models.
    """
    cache_key = f'model_stats_{request.user.id if not request.user.is_staff else "all"}'
    cached_data = cache.get(cache_key)

    if cached_data:
        return Response(cached_data)

    # Build queryset
    queryset = ModelPerformanceMetric.objects.all()
    if not request.user.is_staff:
        queryset = queryset.filter(user=request.user)

    # Aggregate by model
    model_stats = list(
        queryset.values('model_name').annotate(
            total_requests=Count('id'),
            success_count=Count('id', filter=Q(success=True)),
            avg_processing_time=Avg('processing_time_ms'),
            total_cost=Sum('cost_usd'),
            avg_quality_score=Avg('quality_score'),
            last_used=Max('created_at')
        ).order_by('-total_requests')
    )

    # Calculate success rates and rename fields
    for stat in model_stats:
        stat['success_rate'] = (stat['success_count'] / stat['total_requests']) * 100 if stat['total_requests'] > 0 else 0
        del stat['success_count']  # Remove intermediate field
        # Rename fields to match serializer expectation
        stat['avg_processing_time_ms'] = stat.pop('avg_processing_time', 0)
        stat['total_cost_usd'] = stat.pop('total_cost', 0)

    serializer = ModelStatsSerializer(model_stats, many=True)

    # Cache for 5 minutes
    cache.set(cache_key, serializer.data, 300)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_model(request):
    """
    Select the best model for a given task.
    """
    serializer = ModelSelectionRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        content_service = TailoredContentService()
        model_registry = ModelRegistry()

        # Get selection parameters
        task_type = serializer.validated_data['task_type']
        complexity_score = serializer.validated_data.get('complexity_score', 0.5)
        user_budget = serializer.validated_data.get('user_budget')
        strategy = serializer.validated_data.get('strategy', 'balanced')

        # Select model
        selected_model, reasoning = content_service._select_model_for_task(
            task_type=task_type,
            complexity_score=complexity_score,
            user_id=request.user.id,
            strategy=strategy
        )

        # Get model info for cost estimation
        model_info = model_registry.get_model_config(selected_model)
        estimated_cost = model_info.get('input_cost_per_token', 0) * 1000  # Estimate for 1k tokens

        # Get fallback models
        all_models = model_registry.get_models_by_criteria(
            task_type=task_type,
            max_cost_per_token=user_budget if user_budget else float('inf')
        )
        fallback_models = [m for m in all_models if m != selected_model][:3]

        response_data = {
            'selected_model': selected_model,
            'reasoning': reasoning,
            'estimated_cost_usd': estimated_cost,
            'fallback_models': fallback_models
        }

        response_serializer = ModelSelectionResponseSerializer(response_data)
        return Response(response_serializer.data)

    except Exception as e:
        return Response(
            {'error': f'Model selection failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """
    Get overall system health status.
    """
    cache_key = 'system_health'
    cached_data = cache.get(cache_key)

    if cached_data:
        return Response(cached_data)

    try:
        # Circuit breaker health
        breakers = CircuitBreakerState.objects.all()
        healthy_models = breakers.filter(state='closed').count()
        unhealthy_models = breakers.exclude(state='closed').count()
        circuit_breakers_open = breakers.filter(state='open').count()

        # Today's costs and performance
        today = timezone.now().date()
        today_metrics = ModelPerformanceMetric.objects.filter(created_at__date=today)

        total_cost_today = today_metrics.aggregate(sum=Sum('cost_usd'))['sum'] or 0
        avg_response_time = today_metrics.aggregate(avg=Avg('processing_time_ms'))['avg'] or 0

        # Success rate calculation
        total_requests = today_metrics.count()
        successful_requests = today_metrics.filter(success=True).count()
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100

        health_data = {
            'healthy_models': healthy_models,
            'unhealthy_models': unhealthy_models,
            'circuit_breakers_open': circuit_breakers_open,
            'total_cost_today': total_cost_today,
            'avg_response_time_ms': avg_response_time,
            'success_rate': success_rate
        }

        serializer = SystemHealthSerializer(health_data)

        # Cache for 1 minute
        cache.set(cache_key, serializer.data, 60)

        return Response(serializer.data)

    except Exception as e:
        return Response(
            {'error': f'Failed to get system health: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_models(request):
    """
    Get list of available models and their configurations.
    """
    try:
        model_registry = ModelRegistry()
        models = model_registry.list_available_models()

        # Add current status from circuit breakers
        breakers_list = list(CircuitBreakerState.objects.all())
        breakers = {cb.model_name: cb for cb in breakers_list}

        for model_name, config in models.items():
            breaker = breakers.get(model_name)
            config['circuit_breaker_status'] = breaker.state if breaker else 'unknown'
            config['is_available'] = breaker.state == 'closed' if breaker else True

        return Response(models)

    except Exception as e:
        return Response(
            {'error': f'Failed to get available models: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )