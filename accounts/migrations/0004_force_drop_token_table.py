from django.db import migrations


class Migration(migrations.Migration):
    """
    Drops the FK constraint by its exact Postgres name, then drops the table.
    Migration 0003 may have been recorded but failed silently — this is a new
    migration so Django will always run it fresh.
    All statements are safe no-ops if the constraint/table no longer exists.
    """

    dependencies = [
        ('accounts', '0003_drop_token_table_cascade'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE IF EXISTS accounts_emailverificationtoken
                    DROP CONSTRAINT IF EXISTS accounts_emailverifi_user_id_4ff4e6c5_fk_auth_user;
                DROP TABLE IF EXISTS accounts_emailverificationtoken;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
