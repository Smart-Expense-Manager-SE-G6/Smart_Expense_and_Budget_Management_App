"""Create the shared cache table used for rate limits and login lockouts (S3-15)."""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Uses settings.CACHES; does nothing if the table already exists.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = []

    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
