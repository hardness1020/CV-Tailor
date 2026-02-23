# Generated migration for ft-007: Remove embedding infrastructure
# This migration removes all embedding-related tables and the pgvector extension
# as we're transitioning to keyword-only artifact ranking.
#
# WARNING: This migration is NOT reversible. Once run, all embedding data will be lost.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('llm_services', '0011_add_adaptive_pdf_classification_fields'),
        ('artifacts', '0001_initial'),  # Need artifacts dependency for unified_embedding column
    ]

    operations = [
        # Drop embedding columns from enhanced_evidence (keep the table for processed_content)
        migrations.RunSQL(
            sql="""
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS content_embedding CASCADE;
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS summary_embedding CASCADE;
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS embedding_model CASCADE;
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS embedding_dimensions CASCADE;
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS embedding_cost_usd CASCADE;
                ALTER TABLE enhanced_evidence DROP COLUMN IF EXISTS last_embedding_update CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Drop the artifact_chunks table entirely (only used for embeddings)
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS artifact_chunks CASCADE;
                DROP TABLE IF EXISTS llm_services_artifactchunk CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Drop the job_embeddings table entirely (only used for embedding cache)
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS job_embeddings CASCADE;
                DROP TABLE IF EXISTS llm_services_jobdescriptionembedding CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Drop the unified_embedding column from artifacts_artifact
        migrations.RunSQL(
            sql="ALTER TABLE artifacts_artifact DROP COLUMN IF EXISTS unified_embedding CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Drop the vector extension (pgvector)
        # Note: This will cascade to any remaining vector columns
        migrations.RunSQL(
            sql="DROP EXTENSION IF EXISTS vector CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
