"""
URL configuration for cv_tailor project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    """Simple health check endpoint for ALB/ECS."""
    return JsonResponse({'status': 'healthy', 'service': 'cv-tailor-backend'})

urlpatterns = [
    path('health/', health_check, name='health-check'),  # For ALB/ECS health checks
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/artifacts/', include('artifacts.urls')),
    path('api/v1/generations/', include('generation.urls')),  # Renamed from /generate/ and /cv/
    path('api/v1/export/', include('export.urls')),
    path('api/v1/llm/', include('llm_services.urls')),
]

# Debug toolbar URLs (development only)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include('debug_toolbar.urls')),
        ] + urlpatterns
    except ImportError:
        pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)