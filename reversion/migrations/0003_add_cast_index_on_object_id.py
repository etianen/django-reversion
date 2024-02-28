# Generated manually lol

from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("reversion", "0002_add_index_on_version_for_content_type_and_db"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE INDEX CONCURRENTLY IF NOT EXISTS "reversion_version_object_id_cast_index" ON
"reversion_version" ((object_id::text));
            """,
            reverse_sql="""
DROP INDEX CONCURRENTLY IF EXISTS "reversion_version_object_id_cast_index";
""",
            elidable=False,
        ),
    ]
