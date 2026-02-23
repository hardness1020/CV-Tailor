# Manual migration to rename database table
# RenameModel didn't work because model has explicit db_table setting

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("llm_services", "0006_rename_enhanced_artifact_to_enhanced_evidence"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="EnhancedEvidence",
            table="enhanced_evidence",
        ),
        migrations.AlterModelTable(
            name="ArtifactChunk",
            table="artifact_chunks",
        ),
    ]