from django.db import migrations


class Migration(migrations.Migration):
    """
    Placeholder — this migration was previously recorded in django_migrations
    but may not have actually dropped the table due to a Postgres FK constraint.
    Migration 0003 handles the actual drop with CASCADE.
    """

    dependencies = [
        ('accounts', '0001_email_verification_token'),
    ]

    operations = [
        # intentionally empty — real drop is in 0003
    ]
