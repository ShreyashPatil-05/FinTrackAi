"""
Management command: expire_plans

Expires Pro plans that have passed their expiry date and sends
7-day advance reminder emails to users whose plan expires soon.

Schedule with cron (runs daily at midnight):
    0 0 * * * /path/to/venv/bin/python manage.py expire_plans --settings=fintrack.settings_prod

Or Windows Task Scheduler:
    python manage.py expire_plans --settings=fintrack.settings_prod
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import UserProfile


class Command(BaseCommand):
    help = 'Expire overdue Pro plans and send 7-day renewal reminders.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now     = timezone.now()

        # ── 1. Expire overdue plans ───────────────────────────────────────────
        expired_qs = UserProfile.objects.filter(
            plan__in=[UserProfile.PLAN_MONTHLY, UserProfile.PLAN_YEARLY],
            plan_expires_at__lt=now,
        ).select_related('user')

        expired_count = expired_qs.count()

        if expired_count:
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would expire {expired_count} plan(s):')
                for p in expired_qs:
                    self.stdout.write(f'  - {p.user.username} ({p.plan}, expired {p.plan_expires_at})')
            else:
                from dashboard.services.email_service import send_plan_expired_email
                for profile in expired_qs:
                    try:
                        send_plan_expired_email(profile.user)
                    except Exception as e:
                        self.stderr.write(f'  Failed to send expiry email to {profile.user.username}: {e}')
                expired_qs.update(plan=UserProfile.PLAN_FREE, plan_expires_at=None)
                self.stdout.write(self.style.SUCCESS(f'Expired {expired_count} plan(s).'))
        else:
            self.stdout.write('No plans to expire.')

        # ── 2. Send 7-day reminders ───────────────────────────────────────────
        reminder_qs = UserProfile.objects.filter(
            plan__in=[UserProfile.PLAN_MONTHLY, UserProfile.PLAN_YEARLY],
            plan_expires_at__lte=now + timedelta(days=7),
            plan_expires_at__gt=now,
        ).select_related('user')

        reminder_count = reminder_qs.count()

        if reminder_count:
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would send {reminder_count} reminder(s):')
                for p in reminder_qs:
                    days_left = (p.plan_expires_at - now).days
                    self.stdout.write(f'  - {p.user.username} ({days_left} days left)')
            else:
                from dashboard.services.email_service import send_expiry_reminder_email
                sent = 0
                for profile in reminder_qs:
                    try:
                        send_expiry_reminder_email(profile.user)
                        sent += 1
                    except Exception as e:
                        self.stderr.write(f'  Failed to send reminder to {profile.user.username}: {e}')
                self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder email(s).'))
        else:
            self.stdout.write('No reminders to send.')
