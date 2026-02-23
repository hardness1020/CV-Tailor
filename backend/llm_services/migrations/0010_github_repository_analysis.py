# Generated manually for ft-013-github-agent-traversal (v1.3.0)

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('llm_services', '0009_drop_orphaned_tables'),
        ('artifacts', '0001_initial'),  # Depends on Evidence model
    ]

    operations = [
        migrations.CreateModel(
            name='GitHubRepositoryAnalysis',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('repo_structure', models.JSONField(default=dict, help_text='Repository file structure from GitHub API')),
                ('detected_project_type', models.CharField(
                    blank=True,
                    choices=[
                        ('framework', 'Framework'),
                        ('library', 'Library'),
                        ('application', 'Application'),
                        ('tool', 'Tool/CLI'),
                        ('platform', 'Platform'),
                        ('other', 'Other'),
                    ],
                    help_text='Detected project type from Phase 1',
                    max_length=50,
                    null=True
                )),
                ('primary_language', models.CharField(blank=True, help_text='Primary programming language', max_length=50, null=True)),
                ('languages_breakdown', models.JSONField(default=dict, help_text='Language percentages from GitHub API')),
                ('files_loaded', models.JSONField(default=list, help_text='List of files selected by LLM in Phase 2')),
                ('total_tokens_used', models.IntegerField(default=0, help_text='Total tokens consumed across all phases')),
                ('selection_reasoning', models.TextField(blank=True, help_text='LLM reasoning for file selection in Phase 2')),
                ('config_analysis', models.JSONField(default=dict, help_text='Config file analysis results (package.json, requirements.txt, etc.)')),
                ('source_analysis', models.JSONField(default=dict, help_text='Source code analysis results (patterns, architecture)')),
                ('infrastructure_analysis', models.JSONField(default=dict, help_text='Infrastructure analysis (Docker, CI/CD, K8s)')),
                ('documentation_analysis', models.JSONField(default=dict, help_text='Documentation analysis (README, ARCHITECTURE, etc.)')),
                ('refinement_iterations', models.IntegerField(default=1, help_text='Number of refinement iterations (1 = no refinement, 2+ = refinement occurred)')),
                ('analysis_confidence', models.FloatField(
                    default=0.0,
                    help_text='Overall confidence in analysis quality (0.0-1.0)',
                    validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
                )),
                ('consistency_score', models.FloatField(
                    default=0.0,
                    help_text='Consistency score from cross-referencing file types (0.0-1.0)',
                    validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
                )),
                ('processing_time_ms', models.IntegerField(default=0, help_text='Total processing time in milliseconds')),
                ('llm_cost_usd', models.DecimalField(decimal_places=6, default=0.0, help_text='Total LLM cost for this analysis', max_digits=10)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('evidence', models.OneToOneField(
                    help_text='The GitHub evidence this analysis is for',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='github_analysis',
                    to='artifacts.evidence'
                )),
                ('extracted_content', models.OneToOneField(
                    blank=True,
                    help_text='The extracted content record for this analysis',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='agent_analysis',
                    to='llm_services.extractedcontent'
                )),
            ],
            options={
                'db_table': 'github_repository_analysis',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['evidence'], name='github_repo_evidenc_7f0cc3_idx'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['detected_project_type'], name='github_repo_detecte_74e9e8_idx'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['primary_language'], name='github_repo_primary_c5e9f2_idx'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['analysis_confidence'], name='github_repo_analysi_8a7d4f_idx'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['created_at'], name='github_repo_created_b5e3d2_idx'),
        ),
    ]
