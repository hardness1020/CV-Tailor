# Generated manually for ft-005 refactoring
# Renames EnhancedArtifact → EnhancedEvidence and updates FK relationships

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0001_initial"),
        ("llm_services", "0005_artifact_preprocessing"),
    ]

    operations = [
        # Rename the model (table rename)
        migrations.RenameModel(
            old_name="EnhancedArtifact",
            new_name="EnhancedEvidence",
        ),
        # Rename the FK field from original_artifact to evidence
        migrations.RenameField(
            model_name="EnhancedEvidence",
            old_name="original_artifact",
            new_name="evidence",
        ),
        # Update the FK in ArtifactChunk
        migrations.RenameField(
            model_name="ArtifactChunk",
            old_name="artifact",
            new_name="enhanced_evidence",
        ),
    ]