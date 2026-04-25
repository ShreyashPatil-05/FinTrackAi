from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Drop the accounts_emailverificationtoken table directly on production PostgreSQL'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'accounts_emailverificationtoken'
                );
            """)
            exists = cursor.fetchone()[0]

            if not exists:
                self.stdout.write(self.style.SUCCESS('Table does not exist — nothing to do.'))
                return

            self.stdout.write('Table found. Cleaning up...')

            # Delete all token rows (removes FK references)
            cursor.execute("DELETE FROM accounts_emailverificationtoken;")
            self.stdout.write('  Deleted all token rows.')

            # Delete leftover inactive non-superuser users
            cursor.execute(
                "DELETE FROM auth_user WHERE is_active = false AND is_superuser = false;"
            )
            self.stdout.write('  Deleted inactive unverified users.')

            # Drop the table with CASCADE
            cursor.execute("DROP TABLE accounts_emailverificationtoken CASCADE;")
            self.stdout.write(self.style.SUCCESS('  Table dropped successfully.'))

            # Mark all accounts migrations as applied so Django doesn't try again
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                VALUES ('accounts', '0002_drop_email_verification_token', NOW()),
                       ('accounts', '0003_cleanup_token_table_production', NOW())
                ON CONFLICT DO NOTHING;
            """)
            self.stdout.write(self.style.SUCCESS('Done. Token table removed from production.'))
