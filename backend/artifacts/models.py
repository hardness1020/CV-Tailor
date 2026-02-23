import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField

User = get_user_model()


class Artifact(models.Model):
    """Main artifact model representing user's work artifacts."""

    ARTIFACT_TYPES = [
        ('project', 'Project'),
        ('publication', 'Publication'),
        ('presentation', 'Presentation'),
        ('certification', 'Certification'),
        ('experience', 'Work Experience'),
        ('education', 'Education'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='artifacts')
    title = models.CharField(max_length=255)
    description = models.TextField()
    artifact_type = models.CharField(max_length=20, choices=ARTIFACT_TYPES, default='project')

    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Skills and metadata
    technologies = models.JSONField(default=list, blank=True)
    collaborators = models.JSONField(default=list, blank=True)

    # Auto-extracted metadata
    extracted_metadata = models.JSONField(default=dict, blank=True)

    # NEW (ft-018): User-provided context for enrichment
    user_context = models.TextField(
        blank=True,
        help_text='User-provided context (immutable, preserved during enrichment)'
    )

    # NEW: Unified enrichment from all evidence sources (ft-005)
    unified_description = models.TextField(
        blank=True,
        help_text='LLM-generated unified description from all evidence sources (ft-005)'
    )
    enriched_technologies = models.JSONField(
        default=list,
        blank=True,
        help_text='Normalized technologies extracted from all evidence (ft-005)'
    )
    enriched_achievements = models.JSONField(
        default=list,
        blank=True,
        help_text='Achievements extracted from all evidence with metrics (ft-005)'
    )
    processing_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Overall confidence in enrichment quality (0.0-1.0) (ft-005)'
    )

    # Wizard workflow tracking (ft-045)
    STATUS_CHOICES = [
        ('draft', 'Draft'),                          # Created but wizard incomplete
        ('processing', 'Processing Evidence'),       # Enrichment running (Step 5)
        ('review_pending', 'Evidence Review Pending'),  # Waiting for user acceptance (Step 5)
        ('reunifying', 'Finalizing Evidence'),       # Phase 2 finalization in progress (Step 6)
        ('review_finalized', 'Review Finalized'),    # Finalization complete, awaiting acceptance (Step 6)
        ('complete', 'Complete'),                    # User accepted artifact (wizard complete)
        ('abandoned', 'Abandoned'),                  # User left wizard without completing
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text='Current completion state of artifact in wizard workflow'
    )
    wizard_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when user accepted artifact (completed wizard at Step 6)'
    )
    last_wizard_step = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text='Last wizard step user reached (1-6) for resume capability'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class Evidence(models.Model):
    """Evidence (sources/links) associated with artifacts."""

    EVIDENCE_TYPES = [
        ('github', 'GitHub Repository'),
        ('document', 'Document/PDF'),
    ]

    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name='evidence')
    url = models.URLField(validators=[URLValidator()])
    evidence_type = models.CharField(
        max_length=20,
        choices=EVIDENCE_TYPES,
        help_text='Evidence type: github (repository) or document (PDF upload)'
    )
    description = models.CharField(max_length=255, blank=True)

    # File-specific fields (for uploaded files)
    file_path = models.TextField(blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)

    # Validation metadata
    validation_metadata = models.JSONField(default=dict, blank=True)
    last_validated = models.DateTimeField(null=True, blank=True)
    is_accessible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate evidence type constraints"""
        super().clean()
        from django.core.exceptions import ValidationError

        if self.evidence_type == 'document':
            # Document evidence must have an uploaded file
            if not self.file_path:
                raise ValidationError({
                    'file_path': 'Document evidence must have an uploaded file (file_path required)'
                })

        elif self.evidence_type == 'github':
            # GitHub evidence must be a github.com URL and should NOT have file_path
            if self.file_path:
                raise ValidationError({
                    'file_path': 'GitHub evidence cannot have uploaded files (must be a URL only)'
                })
            if 'github.com' not in self.url.lower():
                raise ValidationError({
                    'url': 'GitHub evidence must be a github.com URL'
                })

    class Meta:
        db_table = 'evidence'
        verbose_name_plural = 'Evidence'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.description or self.url} ({self.artifact.title})"


class ArtifactProcessingJob(models.Model):
    """Track artifact processing status for async operations."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    JOB_TYPE_CHOICES = [
        ('phase1_extraction', 'Phase 1: Evidence Extraction'),
        ('phase2_reunification', 'Phase 2: Evidence Reunification'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name='processing_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    job_type = models.CharField(
        max_length=30,
        choices=JOB_TYPE_CHOICES,
        default='phase1_extraction',
        help_text='Type of processing job: Phase 1 (extraction) or Phase 2 (reunification)'
    )
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # Processing results
    metadata_extracted = models.JSONField(default=dict, blank=True)
    evidence_validation_results = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Processing {self.artifact.title} - {self.status}"


class UploadedFile(models.Model):
    """Temporary storage for uploaded files during processing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)

    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Auto-cleanup after 24 hours
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.user.email})"