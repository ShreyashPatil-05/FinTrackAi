from django.db import migrations


def table_exists(cursor, db_vendor):
    if db_vendor == 'postgresql':
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'accounts_emailverificationtoken'
            );
        """)
        return cursor.fetchone()[0]
    else:
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='accounts_emailverificationtoken';"
        )
        return cursor.fetchone() is not None


def cleanup_token_table(apps, schema_editor):
    """
    Safely clean up the EmailVerificationToken table if it still exists.
    Idempotent — does nothing if the table is already gone.
    """
    db = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()

    if not table_exists(cursor, db):
        return  # Already gone — nothing to do

    # Clear token rows first (satisfies FK constraint on auth_user)
    cursor.execute("DELETE FROM accounts_emailverificationtoken;")

    # Remove leftover inactive non-superuser users from the old registration flow
    cursor.execute(
        "DELETE FROM auth_user "
        "WHERE is_active = false AND is_superuser = false;"
    )

    # Drop the table
    if db == 'postgresql':
        cursor.execute(
            "DROP TABLE IF EXISTS accounts_emailverificationtoken CASCADE;"
        )
    else:
        cursor.execute(
            "DROP TABLE IF EXISTS accounts_emailverificationtoken;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_drop_email_verification_token'),
    ]

    operations = [
        migrations.RunPython(
            cleanup_token_table,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
