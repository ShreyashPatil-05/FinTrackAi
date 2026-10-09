"""
dashboard/services/email_service.py

Transactional emails for payment and plan lifecycle events.

All emails are sent in a background thread (fire-and-forget) using the same
SendGrid/SMTP pattern used in accounts/views.py. If sending fails, the error
is logged and the user-facing operation continues — email delivery failure
should never block a payment confirmation or plan expiry.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)


def _dispatch_email(recipient_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email in a background daemon thread.

    Uses SendGrid HTTP API when EMAIL_HOST_PASSWORD is a SendGrid key (starts with 'SG.').
    Falls back to Django's SMTP backend for local development.

    Args:
        recipient_address: Destination email address
        subject:           Email subject line
        body:              Plain-text email body
    """
    def _send_in_background():
        try:
            sendgrid_api_key = os.environ.get("EMAIL_HOST_PASSWORD", "")
            sender_address = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@fintrack.app")

            # Determine whether SendGrid is available and configured
            try:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail, Email, To, Content
                sendgrid_available = True
            except ImportError:
                sendgrid_available = False

            if sendgrid_api_key.startswith("SG.") and sendgrid_available:
                mail = Mail(
                    from_email=Email(sender_address),
                    to_emails=To(recipient_address),
                    subject=subject,
                    plain_text_content=Content("text/plain", body),
                )
                client = SendGridAPIClient(sendgrid_api_key)
                response = client.client.mail.send.post(request_body=mail.get())
                logger.info(
                    "Email sent via SendGrid to %s — status %s",
                    recipient_address,
                    response.status_code,
                )
            else:
                from django.core.mail import send_mail
                send_mail(subject, body, None, [recipient_address], fail_silently=False)
                logger.info("Email sent via SMTP to %s", recipient_address)

        except Exception:
            logger.error(
                "Failed to send email to %s — subject: %s",
                recipient_address,
                subject,
                exc_info=True,
            )

    background_thread = threading.Thread(target=_send_in_background, daemon=True)
    background_thread.start()


def send_payment_success_email(user, payment) -> None:
    """
    Send a payment confirmation email after a successful Pro plan upgrade.

    Args:
        user:    Django User instance
        payment: dashboard.models.Payment instance (status='captured')
    """
    try:
        plan_expiry = user.profile.plan_expires_at
        expiry_display = plan_expiry.strftime("%d %B %Y") if plan_expiry else "unlimited"
    except Exception:
        expiry_display = "N/A"

    subject = "FinTrack Pro — Payment Confirmed ✓"
    body = (
        f"Hi {user.username},\n\n"
        f"Your payment of ₹{payment.amount} for the {payment.get_plan_display()} plan "
        f"was successful.\n\n"
        f"Plan active until: {expiry_display}\n"
        f"Payment ID: {payment.razorpay_payment_id}\n\n"
        f"You now have unlimited access to all Pro features:\n"
        f"  • Unlimited expenses, income, goals & subscriptions\n"
        f"  • AI-powered financial insights (Gemini)\n"
        f"  • CSV import & data export\n"
        f"  • Bank webhook simulator\n\n"
        f"Thank you for upgrading!\n"
        f"— The FinTrack Team"
    )
    _dispatch_email(user.email, subject, body)


def send_expiry_reminder_email(user) -> None:
    """
    Send a 7-day expiry reminder before the Pro plan expires.

    Does nothing if plan_expires_at is not set on the user's profile.

    Args:
        user: Django User instance with an active Pro plan
    """
    try:
        from django.utils import timezone
        plan_expiry = user.profile.plan_expires_at
        if not plan_expiry:
            return
        days_remaining = max((plan_expiry - timezone.now()).days, 0)
        expiry_display = plan_expiry.strftime("%d %B %Y")
    except Exception:
        return

    day_word = "day" if days_remaining == 1 else "days"
    subject = f"FinTrack Pro — Your plan expires in {days_remaining} {day_word}"
    body = (
        f"Hi {user.username},\n\n"
        f"Your FinTrack Pro plan expires on {expiry_display} "
        f"({days_remaining} {day_word} remaining).\n\n"
        f"Renew your plan to keep unlimited access:\n"
        f"https://fintrack.app/pricing/\n\n"
        f"— The FinTrack Team"
    )
    _dispatch_email(user.email, subject, body)


def send_plan_expired_email(user) -> None:
    """
    Send a notification email when a Pro plan has expired and been downgraded to Free.

    Args:
        user: Django User instance whose plan was just expired by expire_plans command
    """
    subject = "FinTrack — Your Pro plan has ended"
    body = (
        f"Hi {user.username},\n\n"
        f"Your FinTrack Pro plan has expired and your account has been moved to the Free plan.\n\n"
        f"All your existing data is safe and still accessible. "
        f"To continue with unlimited access, renew your Pro plan at:\n"
        f"https://fintrack.app/pricing/\n\n"
        f"— The FinTrack Team"
    )
    _dispatch_email(user.email, subject, body)
