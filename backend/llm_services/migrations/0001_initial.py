# Generated migration for LLM services models

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

# Try to import pgvector field
try:
    from pgvector.django import VectorField
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelPerformanceMetric',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('model_name', models.CharField(db_index=True, max_length=100)),
                ('task_type', models.CharField(choices=[('job_parsing', 'Job Description Parsing'), ('cv_generation', 'CV Content Generation'), ('embedding', 'Embedding Generation'), ('similarity_search', 'Similarity Search')], max_length=50)),
                ('processing_time_ms', models.IntegerField()),
                ('tokens_used', models.IntegerField(default=0)),
                ('cost_usd', models.DecimalField(decimal_places=6, max_digits=10)),
                ('quality_score', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])),
                ('success', models.BooleanField(default=True)),
                ('complexity_score', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])),
                ('selection_strategy', models.CharField(default='balanced', max_length=50)),
                ('fallback_used', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'model_performance_metrics',
            },
        ),
        migrations.CreateModel(
            name='EnhancedArtifact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('original_artifact_id', models.IntegerField(blank=True, null=True)),
                ('title', models.CharField(max_length=200)),
                ('content_type', models.CharField(choices=[('pdf', 'PDF Document'), ('github', 'GitHub Repository'), ('linkedin', 'LinkedIn Profile'), ('web_profile', 'Web Profile'), ('markdown', 'Markdown Document'), ('text', 'Plain Text')], max_length=50)),
                ('raw_content', models.TextField()),
                ('processed_content', models.JSONField(default=dict)),
                ('content_embedding', VectorField(dimensions=1536) if HAS_PGVECTOR else ArrayField(models.FloatField(), default=list, size=1536)),
                ('summary_embedding', VectorField(dimensions=1536) if HAS_PGVECTOR else ArrayField(models.FloatField(), default=list, size=1536)),
                ('embedding_model', models.CharField(default='text-embedding-3-small', max_length=50)),
                ('embedding_dimensions', models.IntegerField(default=1536)),
                ('embedding_cost_usd', models.DecimalField(decimal_places=6, default=0.0, max_digits=10)),
                ('langchain_version', models.CharField(default='0.2.0', max_length=20)),
                ('processing_strategy', models.CharField(default='adaptive', max_length=50)),
                ('total_chunks', models.IntegerField(default=0)),
                ('processing_time_ms', models.IntegerField(default=0)),
                ('llm_model_used', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_embedding_update', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enhanced_artifacts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'enhanced_artifacts',
            },
        ),
        migrations.CreateModel(
            name='CircuitBreakerState',
            fields=[
                ('model_name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('failure_count', models.IntegerField(default=0)),
                ('last_failure', models.DateTimeField(blank=True, null=True)),
                ('state', models.CharField(choices=[('closed', 'Closed'), ('open', 'Open'), ('half_open', 'Half Open')], default='closed', max_length=20)),
                ('failure_threshold', models.IntegerField(default=5)),
                ('timeout_duration', models.IntegerField(default=30)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'circuit_breaker_states',
            },
        ),
        migrations.CreateModel(
            name='ModelCostTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('model_name', models.CharField(max_length=100)),
                ('total_cost_usd', models.DecimalField(decimal_places=6, max_digits=10)),
                ('generation_count', models.IntegerField()),
                ('avg_cost_per_generation', models.DecimalField(decimal_places=6, max_digits=10)),
                ('total_tokens_used', models.BigIntegerField(default=0)),
                ('avg_tokens_per_generation', models.IntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'model_cost_tracking',
            },
        ),
        migrations.CreateModel(
            name='JobDescriptionEmbedding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('job_description_hash', models.CharField(max_length=64, unique=True)),
                ('company_name', models.CharField(blank=True, max_length=200)),
                ('role_title', models.CharField(blank=True, max_length=200)),
                ('embedding_vector', VectorField(dimensions=1536) if HAS_PGVECTOR else ArrayField(models.FloatField(), default=list, size=1536)),
                ('model_used', models.CharField(default='text-embedding-3-small', max_length=50)),
                ('dimensions', models.IntegerField(default=1536)),
                ('tokens_used', models.IntegerField(default=0)),
                ('cost_usd', models.DecimalField(decimal_places=6, default=0.0, max_digits=8)),
                ('access_count', models.IntegerField(default=1)),
                ('last_accessed', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'job_embeddings',
            },
        ),
        migrations.CreateModel(
            name='ArtifactChunk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('chunk_index', models.IntegerField()),
                ('content', models.TextField()),
                ('metadata', models.JSONField(default=dict)),
                ('embedding_vector', VectorField(dimensions=1536) if HAS_PGVECTOR else ArrayField(models.FloatField(), default=list, size=1536)),
                ('content_hash', models.CharField(max_length=64)),
                ('model_used', models.CharField(default='text-embedding-3-small', max_length=50)),
                ('tokens_used', models.IntegerField(default=0)),
                ('processing_cost_usd', models.DecimalField(decimal_places=6, default=0.0, max_digits=8)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('artifact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='llm_services.enhancedartifact')),
            ],
            options={
                'db_table': 'artifact_chunks',
            },
        ),
        migrations.AddIndex(
            model_name='modelperformancemetric',
            index=models.Index(fields=['model_name', 'task_type'], name='model_perf_model_task_idx'),
        ),
        migrations.AddIndex(
            model_name='modelperformancemetric',
            index=models.Index(fields=['created_at'], name='model_perf_created_idx'),
        ),
        migrations.AddIndex(
            model_name='modelperformancemetric',
            index=models.Index(fields=['success'], name='model_perf_success_idx'),
        ),
        migrations.AddIndex(
            model_name='enhancedartifact',
            index=models.Index(fields=['user', 'content_type'], name='enhanced_artifact_user_type_idx'),
        ),
        migrations.AddIndex(
            model_name='enhancedartifact',
            index=models.Index(fields=['created_at'], name='enhanced_artifact_created_idx'),
        ),
        migrations.AddIndex(
            model_name='enhancedartifact',
            index=models.Index(fields=['embedding_model'], name='enhanced_artifact_model_idx'),
        ),
        migrations.AddIndex(
            model_name='modelcosttracking',
            index=models.Index(fields=['date', 'model_name'], name='cost_tracking_date_model_idx'),
        ),
        migrations.AddIndex(
            model_name='modelcosttracking',
            index=models.Index(fields=['user', 'date'], name='cost_tracking_user_date_idx'),
        ),
        migrations.AddIndex(
            model_name='jobdescriptionembedding',
            index=models.Index(fields=['job_description_hash'], name='job_embedding_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='jobdescriptionembedding',
            index=models.Index(fields=['user', 'last_accessed'], name='job_embedding_user_accessed_idx'),
        ),
        migrations.AddIndex(
            model_name='jobdescriptionembedding',
            index=models.Index(fields=['created_at'], name='job_embedding_created_idx'),
        ),
        migrations.AddIndex(
            model_name='artifactchunk',
            index=models.Index(fields=['artifact', 'chunk_index'], name='artifact_chunk_artifact_idx'),
        ),
        migrations.AddIndex(
            model_name='artifactchunk',
            index=models.Index(fields=['content_hash'], name='artifact_chunk_hash_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='modelcosttracking',
            unique_together={('user', 'date', 'model_name')},
        ),
        migrations.AlterUniqueTogether(
            name='artifactchunk',
            unique_together={('artifact', 'chunk_index')},
        ),
    ]