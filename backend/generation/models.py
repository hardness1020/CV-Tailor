import uuid
import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
# from django.contrib.postgres.fields import ArrayField

User = get_user_model()


class JobDescription(models.Model):
    """Cache for parsed job descriptions."""

    id = models.AutoField(primary_key=True)
    content_hash = models.CharField(max_length=64, unique=True)
    raw_content = models.TextField()
    parsed_data = models.JSONField(default=dict, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    role_title = models.CharField(max_length=255, blank=True)
    parsing_confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_or_create_from_content(cls, content, company_name="", role_title=""):
        """Get or create job description from content hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        job_desc, created = cls.objects.get_or_create(
            content_hash=content_hash,
            defaults={
                'raw_content': content,
                'company_name': company_name,
                'role_title': role_title
            }
        )
        return job_desc, created

    def __str__(self):
        return f"{self.role_title} at {self.company_name}" if self.role_title and self.company_name else f"Job {self.id}"


class GeneratedDocument(models.Model):
    """Generated CV/Cover Letter documents."""

    DOCUMENT_TYPES = [
        ('cv', 'CV/Resume'),
        ('cover_letter', 'Cover Letter'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('bullets_ready', 'Bullets Ready'),
        ('bullets_approved', 'Bullets Approved'),
        ('assembling', 'Assembling CV'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='cv')
    job_description_hash = models.CharField(max_length=64)
    job_description = models.ForeignKey(JobDescription, on_delete=models.SET_NULL, null=True, blank=True)
    job_description_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Job context data for bullet generation (key_requirements, etc.) - ft-024'
    )

    # Generation configuration
    label_ids = models.JSONField(default=list, blank=True)
    template_id = models.IntegerField(default=1)
    custom_sections = models.JSONField(default=dict, blank=True)
    generation_preferences = models.JSONField(default=dict, blank=True)

    # Generated content
    content = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # Processing info
    artifacts_used = models.JSONField(default=list, blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    generation_time_ms = models.IntegerField(null=True, blank=True)

    # Two-phase workflow tracking (ft-009)
    bullets_generated_at = models.DateTimeField(null=True, blank=True, help_text='Timestamp when bullets were generated')
    bullets_count = models.IntegerField(default=0, help_text='Total number of bullets generated')
    assembled_at = models.DateTimeField(null=True, blank=True, help_text='Timestamp when CV was assembled')

    # User feedback
    user_rating = models.IntegerField(null=True, blank=True)  # 1-10
    user_feedback = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.user.email} - {self.status}"


class GenerationFeedback(models.Model):
    """Track user feedback on generated documents."""

    FEEDBACK_TYPES = [
        ('rating', 'Rating'),
        ('edit', 'Content Edit'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
    ]

    id = models.AutoField(primary_key=True)
    generation = models.ForeignKey(GeneratedDocument, on_delete=models.CASCADE, related_name='feedback')
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES)
    feedback_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.feedback_type} for {self.generation.id}"


class CVTemplate(models.Model):
    """CV template definitions."""

    TEMPLATE_CATEGORIES = [
        ('modern', 'Modern'),
        ('classic', 'Classic'),
        ('technical', 'Technical'),
        ('creative', 'Creative'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=TEMPLATE_CATEGORIES)
    description = models.TextField()
    preview_image_url = models.URLField(blank=True)
    template_config = models.JSONField(default=dict)
    prompt_template = models.TextField()
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Most recently created first

    def __str__(self):
        return f"{self.name} ({self.category})"


class SkillsTaxonomy(models.Model):
    """Skills taxonomy for normalization and suggestions."""

    id = models.AutoField(primary_key=True)
    skill_name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50)  # programming, framework, tool, etc.
    aliases = models.JSONField(default=list, blank=True)
    related_skills = models.JSONField(default=list, blank=True)
    popularity_score = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.skill_name

    class Meta:
        verbose_name_plural = "Skills taxonomy"


# ===== ft-006 Bullet Point Models =====
# Added for three-bullets-per-artifact feature
# Reference: docs/specs/spec-20251001-ft006-implementation.md

class BulletPoint(models.Model):
    """
    Individual bullet point generated for an artifact.

    Each bullet belongs to a specific CV generation and represents one
    of exactly 3 bullets generated per artifact.

    Feature: ft-006 (three-bullets-per-artifact)
    """

    # Primary key
    id = models.AutoField(primary_key=True)

    # Relationships
    artifact = models.ForeignKey(
        'artifacts.Artifact',
        on_delete=models.CASCADE,
        related_name='bullet_points',
        help_text='Artifact this bullet describes'
    )
    cv_generation = models.ForeignKey(
        'GeneratedDocument',
        on_delete=models.CASCADE,
        related_name='bullet_points',
        null=True,
        blank=True,
        help_text='CV generation this bullet belongs to (optional until associated)'
    )

    # Position and hierarchy
    position = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text='Position in 3-bullet set (1, 2, or 3)'
    )
    bullet_type = models.CharField(
        max_length=20,
        choices=[
            ('achievement', 'Primary Achievement'),
            ('technical', 'Technical Detail'),
            ('impact', 'Impact/Results')
        ],
        help_text='Structured hierarchy type'
    )

    # Content
    text = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(60)],
        help_text='Bullet point text (60-150 chars)'
    )

    # Metadata
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='ATS-relevant keywords extracted from text'
    )
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text='Quantified metrics (e.g., {"performance_improvement": "40%"})'
    )
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='LLM confidence in bullet quality (0.0-1.0)'
    )

    # Quality metrics
    quality_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Validation quality score (0.0-1.0)'
    )
    has_action_verb = models.BooleanField(
        default=False,
        help_text='Starts with strong action verb'
    )
    keyword_relevance_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Job keyword relevance (0.0-1.0)'
    )

    # User interaction (ft-024 individual approval)
    user_approved = models.BooleanField(
        default=False,
        help_text='User explicitly approved this bullet'
    )
    user_rejected = models.BooleanField(
        default=False,
        help_text='User explicitly rejected this bullet'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when bullet was approved'
    )
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_bullets',
        help_text='User who approved this bullet'
    )
    user_edited = models.BooleanField(
        default=False,
        help_text='User manually edited this bullet'
    )
    original_text = models.CharField(
        max_length=150,
        blank=True,
        help_text='Original LLM-generated text before user edits'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generation_bullet_point'
        ordering = ['cv_generation', 'artifact', 'position']
        indexes = [
            models.Index(fields=['cv_generation', 'artifact']),
            models.Index(fields=['user_approved']),
            models.Index(fields=['quality_score']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cv_generation', 'artifact', 'position'],
                name='unique_bullet_position_per_artifact'
            ),
            models.CheckConstraint(
                check=models.Q(position__gte=1) & models.Q(position__lte=3),
                name='valid_bullet_position'
            ),
            models.CheckConstraint(
                check=~models.Q(user_approved=True, user_rejected=True),
                name='user_approved_rejected_mutually_exclusive'
            ),
        ]

    def __str__(self):
        return f"Bullet {self.position} for {self.artifact.title} ({self.bullet_type})"

    def clean(self):
        """Validate bullet point constraints"""
        super().clean()

        # Validate text length
        if not (60 <= len(self.text) <= 150):
            raise ValidationError(f"Bullet text must be 60-150 characters, got {len(self.text)}")

        # Validate hierarchy based on position
        expected_types = {
            1: 'achievement',
            2: 'technical',
            3: 'impact'
        }
        if self.position in expected_types:
            if self.bullet_type != expected_types[self.position]:
                raise ValidationError(
                    f"Position {self.position} must be '{expected_types[self.position]}' type, "
                    f"got '{self.bullet_type}'"
                )


class BulletGenerationJob(models.Model):
    """
    Track bullet generation requests for artifacts.

    Supports async processing, retry logic, and status tracking.

    Feature: ft-006 (three-bullets-per-artifact)
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    artifact = models.ForeignKey(
        'artifacts.Artifact',
        on_delete=models.CASCADE,
        related_name='bullet_generation_jobs',
        help_text='Artifact to generate bullets for'
    )
    cv_generation = models.ForeignKey(
        'GeneratedDocument',
        on_delete=models.CASCADE,
        related_name='bullet_generation_jobs',
        null=True,
        blank=True,
        help_text='Parent CV generation job'
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='bullet_generation_jobs',
        help_text='User who requested generation'
    )

    # Job context
    job_context = models.JSONField(
        default=dict,
        help_text='Job requirements, keywords, and context for bullet generation'
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('needs_review', 'Needs Review'),
        ],
        default='pending',
        help_text='Current job status'
    )
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Processing progress (0-100)'
    )

    # Generation attempts
    generation_attempts = models.IntegerField(
        default=0,
        help_text='Number of generation attempts made'
    )
    max_attempts = models.IntegerField(
        default=3,
        help_text='Maximum generation attempts before marking as failed'
    )

    # Results
    generated_bullets = models.JSONField(
        default=list,
        blank=True,
        help_text='Generated bullet points (serialized)'
    )
    validation_results = models.JSONField(
        default=dict,
        blank=True,
        help_text='Validation scores and issues'
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text='Error message if generation failed'
    )
    error_traceback = models.TextField(
        blank=True,
        help_text='Full traceback for debugging'
    )

    # Performance metrics
    processing_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Total processing time in milliseconds'
    )
    llm_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Total LLM API cost for this job'
    )
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Total tokens consumed'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'generation_bullet_generation_job'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['artifact', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"BulletGenJob {self.id} for {self.artifact.title} ({self.status})"

    def mark_started(self):
        """Mark job as started"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, bullets, validation):
        """Mark job as completed with results"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.generated_bullets = bullets
        self.validation_results = validation
        self.processing_duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        ) if self.started_at else None
        self.save()

    def mark_failed(self, error_msg: str, traceback: str = ""):
        """Mark job as failed with error details"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_msg
        self.error_traceback = traceback
        self.save()

    def increment_attempt(self):
        """Increment generation attempt counter and update status if max reached"""
        self.generation_attempts += 1

        # Change status to needs_review if max attempts reached
        if self.generation_attempts >= self.max_attempts:
            self.status = 'needs_review'
            self.save(update_fields=['generation_attempts', 'status'])
        else:
            self.save(update_fields=['generation_attempts'])

    def has_attempts_remaining(self) -> bool:
        """Check if more generation attempts are allowed"""
        return self.generation_attempts < self.max_attempts