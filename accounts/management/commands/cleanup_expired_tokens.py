from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import EmailVerificationToken


class Command(BaseCommand):
    help = 'Delete expired email verification tokens (older than 24 hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        expired_tokens = EmailVerificationToken.objects.filter(created_at__lt=cutoff)
        
        count = expired_tokens.count()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} expired tokens')
            )
            for token in expired_tokens[:10]:  # Show first 10
                self.stdout.write(f'  - {token.user.username} ({token.user.email}) - created {token.created_at}')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            deleted_count, _ = expired_tokens.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} expired tokens')
            )
