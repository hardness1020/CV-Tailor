from django.urls import path
from . import views

urlpatterns = [
    # List and non-parameterized endpoints first
    path('', views.UserExportsListView.as_view(), name='user_exports_list'),
    path('templates/', views.ExportTemplateListView.as_view(), name='export_templates_list'),
    path('analytics/', views.export_analytics, name='export_analytics'),

    # Export creation with explicit /create/ prefix to avoid conflict with detail view
    # Takes generation_id (not export_id) since export doesn't exist yet
    path('create/<uuid:generation_id>/', views.export_document, name='export_document'),

    # Export-specific operations (more specific patterns first)
    path('<uuid:export_id>/status/', views.export_status, name='export_status'),
    path('<uuid:export_id>/download/', views.download_export, name='download_export'),

    # Export detail view (generic pattern, must be last)
    path('<uuid:export_id>/', views.ExportJobDetailView.as_view(), name='export_job_detail'),
]
