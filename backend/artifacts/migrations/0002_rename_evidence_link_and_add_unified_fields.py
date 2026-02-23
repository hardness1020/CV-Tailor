# Generated manually for ft-005 refactoring
# Renames EvidenceLink → Evidence and adds unified enrichment fields to Artifact

from django.db import migrations, models
import django.core.validators
from django.contrib.postgres.operations import CreateExtension

try:
    from pgvector.django import VectorField
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0001_initial"),
    ]

    operations = [
        # Rename EvidenceLink → Evidence
        migrations.RenameModel(
            old_name="EvidenceLink",
            new_name="Evidence",
        ),
        # Add unified enrichment fields to Artifact
        migrations.AddField(
            model_name="artifact",
            name="unified_description",
            field=models.TextField(
                blank=True,
                help_text="LLM-generated unified description from all evidence sources (ft-005)",
            ),
        ),
        migrations.AddField(
            model_name="artifact",
            name="enriched_technologies",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Normalized technologies extracted from all evidence (ft-005)",
            ),
        ),
        migrations.AddField(
            model_name="artifact",
            name="enriched_achievements",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Achievements extracted from all evidence with metrics (ft-005)",
            ),
        ),
        migrations.AddField(
            model_name="artifact",
            name="processing_confidence",
            field=models.FloatField(
                default=0.0,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
                help_text="Overall confidence in enrichment quality (0.0-1.0) (ft-005)",
            ),
        ),
        migrations.AddField(
            model_name="artifact",
            name="unified_embedding",
            field=(
                VectorField(dimensions=1536, null=True, blank=True)
                if HAS_PGVECTOR
                else ArrayField(
                    models.FloatField(),
                    size=1536,
                    default=list,
                    null=True,
                    blank=True,
                    help_text="Unified embedding for artifact-level similarity search (ft-005)",
                )
            ),
        ),
    ]