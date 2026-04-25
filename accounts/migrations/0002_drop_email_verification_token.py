from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration is intentionally a no-op.
    The actual cleanup is handled in 0003_cleanup_token_table_production
    which checks for table existence before doing anything.
    """

    dependencies = [
        ('accounts', '0001_email_verification_token'),
    ]

    operations = []
