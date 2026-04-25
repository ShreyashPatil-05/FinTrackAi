from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Previously cleaned up DB-stored email verification tokens. '
        'Tokens are now stored in cache and expire automatically — '
        'this command is a no-op and can be safely removed.'
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                'Pending registrations are now stored in cache and expire automatically after 24 hours. '
                'No manual cleanup is needed.'
            )
        )
