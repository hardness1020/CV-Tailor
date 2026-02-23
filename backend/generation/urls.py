from django.urls import path
from . import views

urlpatterns = [
    # Document generation endpoints
    path('create/', views.create_generation, name='create_generation'),  # Replaces generate_cv
    path('cover-letter/', views.generate_cover_letter, name='generate_cover_letter'),
    path('', views.GenerationListView.as_view(), name='generation_list'),  # Renamed from user_generations_list
    path('<uuid:generation_id>/', views.GenerationDetailView.as_view(), name='generation_detail'),  # ADR-038: Consistent parameter naming
    path('<uuid:generation_id>/status/', views.generation_status, name='generation_status'),  # Nested under generation detail
    path('<uuid:generation_id>/generation-status/', views.unified_generation_status, name='unified_generation_status'),  # ft-026: Unified status endpoint (ADR-040)
    path('<uuid:generation_id>/rate/', views.rate_generation, name='rate_generation'),
    path('templates/', views.GenerationTemplateListView.as_view(), name='generation_templates_list'),  # Renamed from cv_templates_list
    path('analytics/', views.generation_analytics, name='generation_analytics'),

    # ft-009: Two-phase generation workflow endpoints
    # ft-006 + ADR-038: Consolidated generation-scoped bullet endpoints
    path('<uuid:generation_id>/bullets/', views.generation_bullets, name='generation_bullets'),  # GET: fetch bullets, POST: generate bullets
    path('<uuid:generation_id>/bullets/<int:bullet_id>/', views.edit_generation_bullet, name='edit_generation_bullet'),  # Renamed from edit_cv_bullet
    path('<uuid:generation_id>/bullets/approve/', views.approve_generation_bullets, name='approve_generation_bullets'),  # Renamed from approve_cv_bullets
    path('<uuid:generation_id>/bullets/regenerate/', views.regenerate_generation_bullets, name='regenerate_generation_bullets'),  # Renamed from regenerate_cv_bullets (ft-024)
    path('<uuid:generation_id>/assemble/', views.assemble_generation, name='assemble_generation'),  # Renamed from assemble_cv

    # Bullet validation endpoint (not scoped to specific generation)
    path('bullets/validate/', views.validate_bullets, name='validate_bullets'),
]