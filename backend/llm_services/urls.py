"""
URL patterns for LLM services API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'performance-metrics', views.ModelPerformanceMetricViewSet, basename='performance-metrics')
router.register(r'circuit-breakers', views.CircuitBreakerStateViewSet, basename='circuit-breakers')
router.register(r'cost-tracking', views.ModelCostTrackingViewSet, basename='cost-tracking')
router.register(r'enhanced-artifacts', views.EnhancedEvidenceViewSet, basename='enhanced-artifacts')

app_name = 'llm_services'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Custom API endpoints
    path('model-stats/', views.model_stats, name='model-stats'),
    path('select-model/', views.select_model, name='select-model'),
    path('system-health/', views.system_health, name='system-health'),
    path('available-models/', views.available_models, name='available-models'),
]