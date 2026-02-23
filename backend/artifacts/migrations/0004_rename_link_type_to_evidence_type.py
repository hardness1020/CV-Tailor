# Manual migration to rename column link_type to evidence_type

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0003_rename_table_to_evidence"),
    ]

    operations = [
        migrations.RenameField(
            model_name="evidence",
            old_name="link_type",
            new_name="evidence_type",
        ),
    ]