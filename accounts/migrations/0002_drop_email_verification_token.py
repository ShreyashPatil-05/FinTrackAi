from django.db import migrations


def remove_stale_migration_record(apps, schema_editor):
    """
    If this migration was previously recorded but the table still exists
    (because the ORM DeleteModel was blocked by a Postgres FK constraint),
    delete the stale record so the RunSQL below actually executes.
    This function itself is idempotent — safe to run multiple times.
    """
    schema_editor.connection.cursor().execute(
        "DELETE FROM django_migrations WHERE app = 'accounts' AND name = '0002_drop_email_verification_token';"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_email_verification_token'),
    ]

    operations = [
        # Step 1: clear any stale record of this migration so RunSQL below always fires
        migrations.RunPython(remove_stale_migration_record, migrations.RunPython.noop),

        # Step 2: drop the table — CASCADE removes the FK constraint automatically
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS accounts_emailverificationtoken CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
