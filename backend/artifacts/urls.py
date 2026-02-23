from django.urls import path
from . import views, editing_views, validators

urlpatterns = [
    path('', views.ArtifactListCreateView.as_view(), name='artifact_list_create'),
    path('<int:artifact_id>/', views.ArtifactDetailView.as_view(), name='artifact_detail'),
    path('<int:artifact_id>/upload/', views.upload_artifact_files, name='upload_artifact_files'),
    path('<int:artifact_id>/status/', views.artifact_processing_status, name='artifact_processing_status'),
    path('upload-file/', views.upload_file, name='upload_file'),
    path('suggestions/', views.artifact_suggestions, name='artifact_suggestions'),
    path('suggest-for-job/', views.suggest_artifacts_for_job, name='artifact-suggest-for-job'),

    # Enrichment endpoints
    path('<int:artifact_id>/enrich/', views.trigger_artifact_enrichment, name='trigger_artifact_enrichment'),
    path('<int:artifact_id>/enrichment-status/', views.artifact_enrichment_status, name='artifact_enrichment_status'),
    path('<int:artifact_id>/enriched-content/', views.update_enriched_content, name='update_enriched_content'),
    path('<int:artifact_id>/enrichment-debug/', views.artifact_enrichment_debug, name='artifact_enrichment_debug'),

    # Evidence validation endpoints (Layer 2 validation from ft-010)
    path('validate-evidence-links/', validators.validate_evidence_links, name='validate_evidence_links'),

    # Artifact editing endpoints
    path('<int:artifact_id>/evidence-links/', editing_views.add_evidence_link, name='add_evidence_link'),
    path('evidence-links/<int:link_id>/', editing_views.evidence_link_detail, name='evidence_link_detail'),
    path('files/<uuid:file_id>/', editing_views.delete_artifact_file, name='delete_artifact_file'),

    # Evidence Review & Acceptance endpoints (ft-045)
    path('<int:artifact_id>/evidence/<uuid:evidence_id>/accept/', views.accept_evidence, name='artifact_evidence_accept'),
    path('<int:artifact_id>/evidence/<uuid:evidence_id>/reject/', views.reject_evidence, name='artifact_evidence_reject'),
    path('<int:artifact_id>/evidence/<uuid:evidence_id>/content/', views.edit_evidence_content, name='artifact_evidence_edit_content'),
    path('<int:artifact_id>/evidence-acceptance-status/', views.get_evidence_acceptance_status, name='artifact_evidence_acceptance_status'),
    path('<int:artifact_id>/finalize-evidence-review/', views.finalize_evidence_review, name='artifact_finalize_evidence_review'),
    path('<int:artifact_id>/accept-artifact/', views.accept_artifact, name='artifact_accept'),
]