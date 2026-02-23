"""
Models for enhanced LLM services.
Implements ft-005-multi-source-artifact-preprocessing.md and ft-007-manual-artifact-selection.md
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class ModelPerformanceMetric(models.Model):
    """Track performance metrics for different AI models"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=100, db_index=True)
    task_type = models.CharField(max_length=50, choices=[
        ('job_parsing', 'Job Description Parsing'),
        ('cv_generation', 'CV Content Generation'),
    ])

    # Performance metrics
    processing_time_ms = models.IntegerField()
    tokens_used = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    quality_score = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('1.0'))]
    )
    success = models.BooleanField(default=True)

    # Context
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    complexity_score = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('1.0'))]
    )
    selection_strategy = models.CharField(max_length=50, default='balanced')
    fallback_used = models.BooleanField(default=False)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'model_performance_metrics'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'task_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['success']),
        ]

    def __str__(self):
        return f"{self.model_name} - {self.task_type} - {self.created_at}"


class EnhancedEvidence(models.Model):
    """
    Enhanced content from a SINGLE evidence source.

    Stores processed content from ONE evidence link (GitHub, PDF, video, etc.).
    For unified artifact-level enrichment, see Artifact.unified_description.

    NOTE (ft-007): Embeddings removed - using keyword-only ranking.
    This model now stores only processed content without vector embeddings.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enhanced_evidence')

    # Reference to evidence source
    evidence = models.OneToOneField(
        'artifacts.Evidence',
        on_delete=models.CASCADE,
        related_name='enhanced_version',
        null=True,
        blank=True,
        help_text='The evidence source this enhancement is based on'
    )

    # Basic info
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=50, choices=[
        ('pdf', 'PDF Document'),
        ('github', 'GitHub Repository'),
        ('linkedin', 'LinkedIn Profile'),
        ('web_profile', 'Web Profile'),
        ('markdown', 'Markdown Document'),
        ('text', 'Plain Text'),
    ])

    # Content
    raw_content = models.TextField()
    processed_content = models.JSONField(default=dict)  # Structured achievements, skills

    # Processing metadata
    langchain_version = models.CharField(max_length=20, default='0.2.0')
    processing_strategy = models.CharField(max_length=50, default='adaptive')
    total_chunks = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(default=0)
    llm_model_used = models.CharField(max_length=100, blank=True)
    processing_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('1.0'))],
        help_text='Overall confidence in preprocessing quality (0.0-1.0)'
    )

    # Adaptive PDF Processing (ft-016)
    document_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('resume', 'Resume/CV'),
            ('certificate', 'Certificate'),
            ('research_paper', 'Research Paper'),
            ('project_report', 'Project Report'),
            ('academic_thesis', 'Academic Thesis'),
        ],
        help_text='Classified document type for adaptive processing (ft-016)'
    )
    classification_confidence = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('1.0'))],
        help_text='Confidence score for document classification (0.0-1.0)'
    )

    # Evidence review workflow (ft-045)
    accepted = models.BooleanField(
        default=False,
        help_text='Whether the user has accepted/approved this enhanced evidence'
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when evidence was accepted'
    )
    review_notes = models.TextField(
        blank=True,
        default='',
        help_text='Optional notes from user during evidence review'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enhanced_evidence'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'content_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.content_type}) - Evidence #{self.evidence_id}"


class ModelCostTracking(models.Model):
    """Track daily cost usage by user and model"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    model_name = models.CharField(max_length=100)

    # Aggregated costs
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    generation_count = models.IntegerField()
    avg_cost_per_generation = models.DecimalField(max_digits=10, decimal_places=6)

    # Token usage
    total_tokens_used = models.BigIntegerField(default=0)
    avg_tokens_per_generation = models.IntegerField(default=0)

    class Meta:
        db_table = 'model_cost_tracking'
        ordering = ['-date', 'model_name']
        unique_together = ['user', 'date', 'model_name']
        indexes = [
            models.Index(fields=['date', 'model_name']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.model_name} - {self.date}"


class CircuitBreakerState(models.Model):
    """Track circuit breaker state for each model"""

    model_name = models.CharField(max_length=100, primary_key=True)
    failure_count = models.IntegerField(default=0)
    last_failure = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=[
        ('closed', 'Closed'),      # Normal operation
        ('open', 'Open'),          # Circuit broken, using fallback
        ('half_open', 'Half Open'), # Testing if service recovered
    ], default='closed')

    # Configuration
    failure_threshold = models.IntegerField(default=5)
    timeout_duration = models.IntegerField(default=30)  # seconds

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'circuit_breaker_states'
        ordering = ['model_name']

    def record_failure(self):
        """Record a failure and update state if needed"""
        self.failure_count += 1
        self.last_failure = timezone.now()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'

        self.save()

    def record_success(self):
        """Record a success and reset failure count"""
        self.failure_count = 0
        self.state = 'closed'
        self.last_failure = None
        self.save()

    def should_attempt_request(self):
        """Check if we should attempt a request to this model"""
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            # Check if timeout has passed
            if self.last_failure and \
               (timezone.now() - self.last_failure).seconds >= self.timeout_duration:
                self.state = 'half_open'
                self.save()
                return True
            return False
        elif self.state == 'half_open':
            return True

        return False

    def __str__(self):
        return f"{self.model_name} - {self.state} ({self.failure_count} failures)"


class GitHubRepositoryAnalysis(models.Model):
    """
    Agent-based GitHub repository analysis tracking.
    Implements ft-013-github-agent-traversal.md (v1.3.0)

    Tracks all 4 phases of agent-based GitHub analysis:
    - Phase 1: Reconnaissance (metadata, project type detection)
    - Phase 2: File Selection (LLM-powered prioritization)
    - Phase 3: Hybrid Analysis (config/source/infra/docs parsing)
    - Phase 4: Refinement (optional iteration if confidence <0.75)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link to evidence source
    evidence = models.OneToOneField(
        'artifacts.Evidence',
        on_delete=models.CASCADE,
        related_name='github_analysis',
        help_text='The GitHub evidence this analysis is for'
    )

    # Phase 3.2: Removed extracted_content FK (ExtractedContent model deprecated)
    # Analysis data now tracked via evidence -> enhanced_version (EnhancedEvidence)

    # Phase 1: Reconnaissance
    repo_structure = models.JSONField(
        default=dict,
        help_text='Repository file structure from GitHub API'
    )
    detected_project_type = models.CharField(
        max_length=50,
        choices=[
            ('framework', 'Framework'),
            ('library', 'Library'),
            ('application', 'Application'),
            ('tool', 'Tool/CLI'),
            ('platform', 'Platform'),
            ('other', 'Other'),
        ],
        null=True,
        blank=True,
        help_text='Detected project type from Phase 1'
    )
    primary_language = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Primary programming language'
    )
    languages_breakdown = models.JSONField(
        default=dict,
        help_text='Language percentages from GitHub API'
    )

    # Phase 2: File selection
    files_loaded = models.JSONField(
        default=list,
        help_text='List of files selected by LLM in Phase 2'
    )
    total_tokens_used = models.IntegerField(
        default=0,
        help_text='Total tokens consumed across all phases'
    )
    selection_reasoning = models.TextField(
        blank=True,
        help_text='LLM reasoning for file selection in Phase 2'
    )

    # Phase 3: Hybrid analysis
    config_analysis = models.JSONField(
        default=dict,
        help_text='Config file analysis results (package.json, requirements.txt, etc.)'
    )
    source_analysis = models.JSONField(
        default=dict,
        help_text='Source code analysis results (patterns, architecture)'
    )
    infrastructure_analysis = models.JSONField(
        default=dict,
        help_text='Infrastructure analysis (Docker, CI/CD, K8s)'
    )
    documentation_analysis = models.JSONField(
        default=dict,
        help_text='Documentation analysis (README, ARCHITECTURE, etc.)'
    )

    # Phase 4: Refinement
    refinement_iterations = models.IntegerField(
        default=1,
        help_text='Number of refinement iterations (1 = no refinement, 2+ = refinement occurred)'
    )

    # Quality metrics
    analysis_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Overall confidence in analysis quality (0.0-1.0)'
    )
    consistency_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Consistency score from cross-referencing file types (0.0-1.0)'
    )

    # Performance tracking
    processing_time_ms = models.IntegerField(
        default=0,
        help_text='Total processing time in milliseconds'
    )
    llm_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0.0,
        help_text='Total LLM cost for this analysis'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'github_repository_analysis'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evidence']),
            models.Index(fields=['detected_project_type']),
            models.Index(fields=['primary_language']),
            models.Index(fields=['analysis_confidence']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"GitHub Analysis: {self.evidence.url} - {self.detected_project_type} ({self.analysis_confidence:.2f} confidence)"