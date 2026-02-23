# Manual migration to rename database table
# RenameModel didn't work because model has explicit db_table setting

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0002_rename_evidence_link_and_add_unified_fields"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="Evidence",
            table="evidence",
        ),
    ]