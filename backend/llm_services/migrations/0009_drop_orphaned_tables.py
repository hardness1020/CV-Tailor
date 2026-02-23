"""
Migration to drop orphaned database tables that no longer have corresponding Django models.

These tables were from previous implementations that have been refactored:
- preprocessed_artifacts: Replaced by unified fields in Artifact model (ft-005)
- enhanced_cv_generations: Replaced by GeneratedDocument model
- artifact_processing_jobs: Duplicate of artifacts_artifactprocessingjob

All three tables are confirmed empty and safe to drop.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('llm_services', '0008_alter_artifactchunk_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS preprocessed_artifacts CASCADE;
                DROP TABLE IF EXISTS enhanced_cv_generations CASCADE;
                DROP TABLE IF EXISTS artifact_processing_jobs CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
