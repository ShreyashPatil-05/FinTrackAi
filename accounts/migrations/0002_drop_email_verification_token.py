from django.db import migrations


def clear_tokens_and_deactivated_users(apps, schema_editor):
    """
    1. Delete all EmailVerificationToken rows (removes FK references).
    2. Delete any User accounts that are still inactive (is_active=False)
       — these are leftover unverified registrations from the old flow.
       Active users and superusers are never touched.
    """
    db = schema_editor.connection.vendor

    # Delete all token rows first (satisfies FK constraint)
    schema_editor.connection.cursor().execute(
        "DELETE FROM accounts_emailverificationtoken;"
    )

    # Delete leftover inactive non-superuser users
    schema_editor.connection.cursor().execute(
        "DELETE FROM auth_user WHERE is_active = false AND is_superuser = false;"
    )


def drop_token_table(apps, schema_editor):
    """
    Drop the table using vendor-appropriate SQL.
    PostgreSQL supports CASCADE; SQLite does not need it (no FK enforcement).
    """
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.connection.cursor().execute(
            "DROP TABLE IF EXISTS accounts_emailverificationtoken CASCADE;"
        )
    else:
        schema_editor.connection.cursor().execute(
            "DROP TABLE IF EXISTS accounts_emailverificationtoken;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_email_verification_token'),
    ]

    operations = [
        # Step 1: clear rows so FK constraint is satisfied
        migrations.RunPython(
            clear_tokens_and_deactivated_users,
            reverse_code=migrations.RunPython.noop,
        ),

        # Step 2: drop the table (vendor-aware)
        migrations.RunPython(
            drop_token_table,
            reverse_code=migrations.RunPython.noop,
        ),

        # Step 3: tell Django's ORM the model is gone
        migrations.DeleteModel(
            name='EmailVerificationToken',
        ),
    ]
