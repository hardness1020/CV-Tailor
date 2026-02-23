import uuid
from django.db import models
from django.contrib.auth import get_user_model
from generation.models import GeneratedDocument

User = get_user_model()


class ExportTemplate(models.Model):
    """Export template definitions for different document formats."""

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
    css_styles = models.TextField(blank=True)
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Most recently created first

    def __str__(self):
        return f"{self.name} ({self.category})"


class ExportJob(models.Model):
    """Track document export jobs and their status."""

    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
    ]

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_jobs')
    generated_document = models.ForeignKey(GeneratedDocument, on_delete=models.CASCADE)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    template = models.ForeignKey(ExportTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    # Export options
    export_options = models.JSONField(default=dict, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # File information
    file_path = models.TextField(blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    download_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.format.upper()} export for {self.user.email} - {self.status}"

    @property
    def download_url(self):
        """Generate download URL for the exported file."""
        if self.file_path and self.status == 'completed':
            return f"/api/v1/export/{self.id}/download"
        return None


class ExportAnalytics(models.Model):
    """Track export analytics and user behavior."""

    EVENT_TYPES = [
        ('created', 'Export Created'),
        ('downloaded', 'File Downloaded'),
        ('shared', 'File Shared'),
        ('deleted', 'File Deleted'),
    ]

    id = models.AutoField(primary_key=True)
    export_job = models.ForeignKey(ExportJob, on_delete=models.CASCADE, related_name='analytics')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    metadata = models.JSONField(default=dict, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.export_job.id}"