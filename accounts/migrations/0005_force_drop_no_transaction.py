from django.db import migrations


class Migration(migrations.Migration):

    # Run outside a transaction so Postgres FK errors don't cause a silent rollback
    atomic = False

    dependencies = [
        ('accounts', '0004_force_drop_token_table'),
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
