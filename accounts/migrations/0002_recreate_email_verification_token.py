import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_stale_migration_record(apps, schema_editor):
    """
    Remove the stale record of the old 0002_drop migration so this
    migration can run cleanly even if the old one was previously applied.
    """
    schema_editor.connection.cursor().execute(
        "DELETE FROM django_migrations "
        "WHERE app = 'accounts' AND name = '0002_drop_email_verification_token';"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_email_verification_token'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the stale record of the old drop migration
        migrations.RunPython(delete_stale_migration_record, migrations.RunPython.noop),

        # Recreate the table (DROP first in case a partial state exists)
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS accounts_emailverificationtoken;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_token',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Email Verification Token',
                'verbose_name_plural': 'Email Verification Tokens',
                'ordering': ['-created_at'],
            },
        ),
    ]
