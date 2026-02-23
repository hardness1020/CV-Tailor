"""
Django signal handlers for the artifacts app.

This module contains signal handlers that auto-trigger enrichment when
evidence is added to artifacts. This ensures consistent behavior across
all evidence source types (files, GitHub, future sources).

Related: ft-025, ADR-030
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Evidence
from .tasks import enrich_artifact


@receiver(post_save, sender=Evidence)
def auto_trigger_enrichment_on_evidence_creation(sender, instance, created, **kwargs):
    """
    Auto-trigger LLM enrichment when new evidence is added to an artifact.

    This signal handler ensures ALL evidence types (files, GitHub repos,
    future sources like URLs, LinkedIn profiles) trigger enrichment
    consistently without duplicating trigger logic across the codebase.

    Uses transaction.on_commit() to ensure enrichment starts AFTER the
    database transaction commits, preventing race conditions where the
    enrichment task runs before the Evidence object is visible to the
    database.

    Args:
        sender: The Evidence model class
        instance: The Evidence instance that was saved
        created: Boolean indicating if this is a new object (True) or update (False)
        **kwargs: Additional signal arguments

    Related:
        - ft-025: Fix GitHub Enrichment Trigger (this feature)
        - ft-010: Auto-Enrichment for File Uploads (original pattern)
        - ft-023: Fix Duplicate Enrichment Tasks (duplicate prevention)
        - ADR-030: Signal-Based Enrichment Trigger (architecture decision)

    Note:
        The enrich_artifact Celery task has built-in duplicate prevention
        (get_or_create on ArtifactProcessingJob), so multiple evidence
        creations for the same artifact won't create duplicate jobs.

    Example:
        # GitHub evidence creation
        Evidence.objects.create(
            artifact=my_artifact,
            url='https://github.com/user/repo',
            evidence_type='github'
        )
        # → Signal triggers enrichment automatically

        # File upload evidence creation
        Evidence.objects.create(
            artifact=my_artifact,
            url='/media/uploads/resume.pdf',
            evidence_type='document'
        )
        # → Signal triggers enrichment automatically

        # Evidence update (URL change)
        evidence.url = 'https://github.com/user/new-repo'
        evidence.save()
        # → Signal does NOT trigger (created=False)
    """
    if created:  # Only trigger for NEW evidence (not updates)
        # Use transaction.on_commit to ensure Evidence is committed to DB
        # before enrichment task starts (prevents race conditions)
        transaction.on_commit(
            lambda: enrich_artifact.delay(
                artifact_id=instance.artifact.id,
                user_id=instance.artifact.user.id
            )
        )
