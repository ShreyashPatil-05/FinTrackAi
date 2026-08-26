"""
Dashboard Email Service

Sends transactional emails for payment and plan lifecycle events.
Uses the same SendGrid/SMTP pattern as accounts/views.py.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)


def _send_email_background(to_email: str, subject: str, message: str) -> None:
    """Send an email in a background thread (fire-and-forget)."""

    def _send():
        try:
            sendgrid_key = os.environ.get('EMAIL_HOST_PASSWORD', '')
            try:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail, Email, To, Content
                SENDGRID_AVAILABLE = True
            except ImportError:
                SENDGRID_AVAILABLE = False

            if sendgrid_key and sendgrid_key.startswith('SG.') and SENDGRID_AVAILABLE:
                from_email = Email(os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@fintrack.app'))
                mail = Mail(from_email, To(to_email), subject, Content('text/plain', message))
                sg = SendGridAPIClient(sendgrid_key)
                response = sg.client.mail.send.post(request_body=mail.get())
                logger.info(f"Payment email sent via SendGrid: {response.status_code}")
            else:
                from django.core.mail import send_mail
                send_mail(subject, message, None, [to_email], fail_silently=False)
                logger.info(f"Payment email sent via SMTP to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send payment email to {to_email}: {e}", exc_info=True)

    threading.Thread(target=_send, daemon=True).start()


def send_payment_success_email(user, payment) -> None:
    """
    Send a payment confirmation email after a successful Pro plan upgrade.

    Args:
        user:    Django User instance
        payment: dashboard.models.Payment instance (status='captured')
    """
    try:
        expires = user.profile.plan_expires_at
        expires_str = expires.strftime('%d %B %Y') if expires else 'unlimited'
    except Exception:
        expires_str = 'N/A'

    subject = f'FinTrack Pro — Payment Confirmed ✓'
    message = (
        f"Hi {user.username},\n\n"
        f"Your payment of ₹{payment.amount} for the {payment.get_plan_display()} plan "
        f"was successful.\n\n"
        f"Plan active until: {expires_str}\n"
        f"Payment ID: {payment.razorpay_payment_id}\n\n"
        f"You now have unlimited access to all Pro features:\n"
        f"  • Unlimited expenses, income, goals & subscriptions\n"
        f"  • AI-powered financial insights (Gemini)\n"
        f"  • CSV import & data export\n"
        f"  • Bank webhook simulator\n\n"
        f"Thank you for upgrading!\n"
        f"— The FinTrack Team"
    )
    _send_email_background(user.email, subject, message)


def send_expiry_reminder_email(user) -> None:
    """
    Send a 7-day expiry reminder email before the Pro plan expires.

    Args:
        user: Django User instance with an active Pro plan
    """
    try:
        from django.utils import timezone
        expires = user.profile.plan_expires_at
        if not expires:
            return
        days_left = max((expires - timezone.now()).days, 0)
        expires_str = expires.strftime('%d %B %Y')
    except Exception:
        return

    subject = f'FinTrack Pro — Your plan expires in {days_left} day{"s" if days_left != 1 else ""}'
    message = (
        f"Hi {user.username},\n\n"
        f"Your FinTrack Pro plan expires on {expires_str} ({days_left} day{'s' if days_left != 1 else ''} left).\n\n"
        f"Renew your plan to keep unlimited access:\n"
        f"https://fintrack.app/pricing/\n\n"
        f"— The FinTrack Team"
    )
    _send_email_background(user.email, subject, message)


def send_plan_expired_email(user) -> None:
    """
    Send a notification email when a Pro plan has been expired (downgraded to free).

    Args:
        user: Django User instance whose plan was just expired
    """
    subject = 'FinTrack — Your Pro plan has ended'
    message = (
        f"Hi {user.username},\n\n"
        f"Your FinTrack Pro plan has expired and your account has been moved to the Free plan.\n\n"
        f"You can still access all your existing data. To continue with unlimited access, "
        f"renew your Pro plan at:\n"
        f"https://fintrack.app/pricing/\n\n"
        f"— The FinTrack Team"
    )
    _send_email_background(user.email, subject, message)
