from django.db import migrations


class Migration(migrations.Migration):
    """
    Drops the accounts_emailverificationtoken table using raw SQL with CASCADE.
    This is a new migration (0003) so Django will always run it fresh regardless
    of whether 0002 was previously recorded.
    IF EXISTS makes it a safe no-op if the table is already gone.
    """

    dependencies = [
        ('accounts', '0002_drop_email_verification_token'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS accounts_emailverificationtoken CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
