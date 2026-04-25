from django.db import migrations


def cleanup_token_table(apps, schema_editor):
    """
    Production fix: the accounts_emailverificationtoken table may still exist
    on PostgreSQL even though migration 0002 recorded itself as applied.
    This migration cleans up the data and drops the table safely.

    Steps:
      1. Check if the table exists — if not, nothing to do.
      2. Delete all token rows (removes FK references to auth_user).
      3. Delete leftover inactive non-superuser users (old unverified registrations).
      4. Drop the table using vendor-appropriate SQL.
    """
    db = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()

    # Check if table still exists
    if db == 'postgresql':
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'accounts_emailverificationtoken'
            );
        """)
        table_exists = cursor.fetchone()[0]
    else:
        # SQLite
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='accounts_emailverificationtoken';
        """)
        table_exists = cursor.fetchone() is not None

    if not table_exists:
        return  # Already gone — nothing to do

    # Clear token rows first (FK constraint)
    cursor.execute("DELETE FROM accounts_emailverificationtoken;")

    # Remove leftover inactive non-superuser users from old registration flow
    cursor.execute(
        "DELETE FROM auth_user WHERE is_active = false AND is_superuser = false;"
    )

    # Drop the table
    if db == 'postgresql':
        cursor.execute("DROP TABLE IF EXISTS accounts_emailverificationtoken CASCADE;")
    else:
        cursor.execute("DROP TABLE IF EXISTS accounts_emailverificationtoken;")


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
