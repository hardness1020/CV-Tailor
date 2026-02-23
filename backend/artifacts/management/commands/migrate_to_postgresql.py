"""
Django management command to migrate data from SQLite to PostgreSQL.
This command handles the complete data migration process for CV Tailor.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections, transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Migrate data from SQLite to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sqlite-path',
            type=str,
            default='db.sqlite3',
            help='Path to the SQLite database file (default: db.sqlite3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without actually migrating data'
        )
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Only verify data integrity, do not migrate'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)'
        )

    def handle(self, *args, **options):
        self.sqlite_path = options['sqlite_path']
        self.dry_run = options['dry_run']
        self.verify_only = options['verify_only']
        self.batch_size = options['batch_size']

        # Resolve full path to SQLite file
        if not os.path.isabs(self.sqlite_path):
            self.sqlite_path = os.path.join(settings.BASE_DIR, self.sqlite_path)

        if not os.path.exists(self.sqlite_path):
            raise CommandError(f'SQLite database not found at: {self.sqlite_path}')

        # Check if we're configured for PostgreSQL
        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            raise CommandError(
                'Django is not configured to use PostgreSQL. '
                'Please set DB_ENGINE=postgresql environment variable.'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'DRY RUN: ' if self.dry_run else ''}"
                f"Starting migration from SQLite to PostgreSQL"
            )
        )
        self.stdout.write(f"SQLite database: {self.sqlite_path}")
        self.stdout.write(f"PostgreSQL database: {settings.DATABASES['default']['NAME']}")

        try:
            if self.verify_only:
                self.verify_migration()
            else:
                self.migrate_data()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Migration failed: {str(e)}")
            )
            sys.exit(1)

    def migrate_data(self):
        """Perform the complete data migration."""

        # Connect to SQLite
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        # Get PostgreSQL connection
        pg_conn = connections['default']

        try:
            # Get list of tables to migrate in dependency order
            tables_to_migrate = self.get_migration_order()

            self.stdout.write(f"Found {len(tables_to_migrate)} tables to migrate:")
            for table_info in tables_to_migrate:
                self.stdout.write(f"  - {table_info['name']} ({table_info['model'].__name__})")

            # Disable foreign key checks during migration
            with pg_conn.cursor() as pg_cursor:
                pg_cursor.execute("SET session_replication_role = replica;")

            total_migrated = 0

            # Migrate each table
            for table_info in tables_to_migrate:
                migrated_count = self.migrate_table(
                    sqlite_conn,
                    pg_conn,
                    table_info
                )
                total_migrated += migrated_count

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Migrated {migrated_count} records from {table_info['name']}"
                    )
                )

            # Re-enable foreign key checks
            with pg_conn.cursor() as pg_cursor:
                pg_cursor.execute("SET session_replication_role = DEFAULT;")

            # Update sequences
            self.update_sequences(pg_conn)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Migration completed successfully! "
                    f"Total records migrated: {total_migrated}"
                )
            )

            # Verify migration
            self.verify_migration()

        finally:
            sqlite_conn.close()

    def get_migration_order(self):
        """Get tables in dependency order to avoid foreign key conflicts."""

        # Define tables in dependency order (dependencies first)
        ordered_models = [
            # User model first (no dependencies)
            User,
            # Apps models in dependency order
            apps.get_model('generation', 'CVTemplate'),
            apps.get_model('generation', 'SkillsTaxonomy'),
            apps.get_model('generation', 'JobDescription'),
            apps.get_model('artifacts', 'Artifact'),
            apps.get_model('artifacts', 'Evidence'),
            apps.get_model('artifacts', 'UploadedFile'),
            apps.get_model('artifacts', 'ArtifactProcessingJob'),
            apps.get_model('generation', 'GeneratedDocument'),
            apps.get_model('generation', 'GenerationFeedback'),
            apps.get_model('export', 'ExportedDocument'),
            apps.get_model('export', 'ExportJob'),
        ]

        tables_info = []
        for model in ordered_models:
            try:
                table_name = model._meta.db_table
                tables_info.append({
                    'name': table_name,
                    'model': model
                })
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Skipping model {model.__name__}: {e}")
                )

        return tables_info

    def migrate_table(self, sqlite_conn, pg_conn, table_info):
        """Migrate a single table from SQLite to PostgreSQL."""

        table_name = table_info['name']
        model = table_info['model']

        if self.dry_run:
            # Count records for dry run
            cursor = sqlite_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            self.stdout.write(f"Would migrate {count} records from {table_name}")
            return count

        # Get all records from SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")

        migrated_count = 0
        batch = []

        for row in cursor.fetchall():
            # Convert row to dictionary
            row_dict = dict(row)
            batch.append(row_dict)

            if len(batch) >= self.batch_size:
                migrated_count += self.insert_batch(model, batch)
                batch = []

        # Insert remaining records
        if batch:
            migrated_count += self.insert_batch(model, batch)

        return migrated_count

    def insert_batch(self, model, batch):
        """Insert a batch of records into PostgreSQL."""

        if not batch:
            return 0

        try:
            with transaction.atomic():
                objects_to_create = []

                for row_dict in batch:
                    # Handle JSON fields
                    row_dict = self.convert_json_fields(model, row_dict)

                    # Create model instance
                    obj = model(**row_dict)
                    objects_to_create.append(obj)

                # Bulk create
                model.objects.bulk_create(objects_to_create, ignore_conflicts=False)

            return len(batch)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error inserting batch into {model._meta.db_table}: {e}"
                )
            )

            # Try inserting one by one to identify problematic records
            success_count = 0
            for row_dict in batch:
                try:
                    with transaction.atomic():
                        row_dict = self.convert_json_fields(model, row_dict)
                        model.objects.create(**row_dict)
                        success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping record in {model._meta.db_table}: {e}"
                        )
                    )

            return success_count

    def convert_json_fields(self, model, row_dict):
        """Convert JSON string fields to Python objects for models with JSONField."""

        # Get JSON fields from model
        json_fields = []
        for field in model._meta.fields:
            if field.get_internal_type() == 'JSONField':
                json_fields.append(field.name)

        # Convert JSON string fields
        for field_name in json_fields:
            if field_name in row_dict and row_dict[field_name]:
                if isinstance(row_dict[field_name], str):
                    try:
                        row_dict[field_name] = json.loads(row_dict[field_name])
                    except json.JSONDecodeError:
                        # Keep as string if not valid JSON
                        pass

        return row_dict

    def update_sequences(self, pg_conn):
        """Update PostgreSQL sequences to avoid primary key conflicts."""

        self.stdout.write("Updating PostgreSQL sequences...")

        with pg_conn.cursor() as cursor:
            # Get all sequences
            cursor.execute("""
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_schema = 'public'
            """)

            sequences = cursor.fetchall()

            for (sequence_name,) in sequences:
                # Extract table name from sequence name
                if sequence_name.endswith('_id_seq'):
                    table_name = sequence_name[:-7]  # Remove '_id_seq'

                    # Update sequence value
                    cursor.execute(f"""
                        SELECT setval('{sequence_name}',
                               COALESCE((SELECT MAX(id) FROM {table_name}), 1))
                    """)

                    self.stdout.write(f"  Updated sequence: {sequence_name}")

    def verify_migration(self):
        """Verify data integrity after migration."""

        self.stdout.write("Verifying migration...")

        # Connect to SQLite
        sqlite_conn = sqlite3.connect(self.sqlite_path)

        # Get PostgreSQL connection
        pg_conn = connections['default']

        try:
            verification_passed = True

            # Check each table
            tables_to_check = self.get_migration_order()

            for table_info in tables_to_check:
                table_name = table_info['name']
                model = table_info['model']

                # Count records in SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]

                # Count records in PostgreSQL
                pg_count = model.objects.count()

                if sqlite_count == pg_count:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {table_name}: {pg_count} records (matches SQLite)"
                        )
                    )
                else:
                    verification_passed = False
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ {table_name}: PostgreSQL has {pg_count} records, "
                            f"SQLite has {sqlite_count} records"
                        )
                    )

            if verification_passed:
                self.stdout.write(
                    self.style.SUCCESS("Migration verification passed!")
                )
            else:
                raise CommandError("Migration verification failed!")

        finally:
            sqlite_conn.close()