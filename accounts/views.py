from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.db import IntegrityError
import logging
import threading
import os

# Optional: SendGrid for production email
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm
from .services.auth_service import (
    check_register_rate_limit,
    increment_register_rate_limit,
    create_user_with_token,
    verify_email_token,
    resend_verification_token,
)

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """
    Extract the client's IP address from the request.

    Uses the rightmost IP in X-Forwarded-For, which is set by the trusted
    proxy (Railway) and cannot be spoofed by the client. Falls back to
    REMOTE_ADDR if the header is absent.

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        # Rightmost IP is appended by our trusted proxy — not client-controlled
        ips = [ip.strip() for ip in x_forwarded.split(',')]
        return ips[-1]
    return request.META.get('REMOTE_ADDR', '')


def _verify_recaptcha(response_token):
    """
    Verify reCAPTCHA token with Google's API.

    Args:
        response_token: reCAPTCHA response token from client

    Returns:
        bool: True if verification successful, False otherwise

    Note:
        Returns True if RECAPTCHA_SECRET_KEY is not configured (dev fallback)
    """
    import urllib.request
    import urllib.parse
    import json

    if not settings.RECAPTCHA_SECRET_KEY:
        return True  # skip verification if key not configured (dev fallback)
    try:
        data = urllib.parse.urlencode({
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': response_token,
        }).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get('success', False)
    except Exception:
        return False


# ----------------------------
# VERIFY PENDING VIEW
# ----------------------------
def verify_pending(request):
    """
    Shown after registration — tells user to check their email.
    Email is pulled from session so it can be displayed.
    """
    email = request.session.get('pending_verification_email', '')
    return render(request, 'accounts/verify_pending.html', {'email': email})


# ----------------------------
# REGISTER VIEW
# ----------------------------
def register_view(request):
    """
    Handle user registration with email verification and reCAPTCHA.

    Features:
        - Rate limiting (3 attempts per IP per hour)
        - reCAPTCHA verification
        - Email verification token generation
        - Background email sending
        - Transaction safety to prevent race conditions

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Registration form or redirect to login on success
    """
    form = MyUserCreationForm(request.POST or None)

    if request.method == "POST":
        try:
            ip = _get_client_ip(request)
            allowed, attempts = check_register_rate_limit(ip)

            if not allowed:
                messages.error(request, 'Too many registration attempts. Please try again in an hour.')
                return render(request, "accounts/auth.html", {
                    "form": form, "page_title": "Create Account",
                    "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                    "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                })

            if form.is_valid():
                # Verify reCAPTCHA
                recaptcha_response = request.POST.get('g-recaptcha-response', '')
                if not _verify_recaptcha(recaptcha_response):
                    messages.error(request, 'Please complete the reCAPTCHA verification.')
                    return render(request, "accounts/auth.html", {
                        "form": form, "page_title": "Create Account",
                        "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                    })

                try:
                    user, token_obj = create_user_with_token(form)
                    _send_verification_email(request, user, token_obj.token)
                    increment_register_rate_limit(ip, attempts)
                    logger.info(f"User registered: {user.username} ({user.email})")

                except IntegrityError as e:
                    logger.error(f"Registration integrity error: {e}")
                    messages.error(request, 'Registration failed. This email or username may already be in use.')
                    return render(request, "accounts/auth.html", {
                        "form": form, "page_title": "Create Account",
                        "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                    })

                request.session['pending_verification_email'] = user.email
                return redirect("verify_pending")
            else:
                messages.error(request, "Registration failed. Please fix the errors.")

        except Exception as e:
            logger.error(f"Unexpected error in register_view: {e}", exc_info=True)
            messages.error(request, "Something went wrong. Please try again.")
            return render(request, "accounts/auth.html", {
                "form": form, "page_title": "Create Account",
                "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            })

    return render(request, "accounts/auth.html", {
        "form": form,
        "page_title": "Create Account",
        "button_text": "Register",
        "page_type": "register",
        "hide_auth_nav": True,
        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
    })


def _send_verification_email(request, user, token):
    """
    Send email verification link to user in a background thread.

    Uses SendGrid HTTP API (not SMTP) to avoid Railway port blocking.
    Falls back to SMTP for local development.

    Args:
        request: Django HttpRequest (for building absolute URL)
        user: Django User object
        token: UUID verification token

    Returns:
        None (email sent asynchronously)
    """
    verify_url = request.build_absolute_uri(
        reverse('verify_email', args=[str(token)])
    )
    subject = 'Verify your FinTrack account'
    message = (
        f"Hi {user.username},\n\n"
        f"Click the link below to verify your email address:\n\n"
        f"{verify_url}\n\n"
        f"This link is valid for 24 hours.\n\n"
        f"— FinTrack"
    )

    def _send():
        try:
            masked = user.email[:2] + '***@' + user.email.split('@')[1]
            logger.info(f"Sending verification email to {masked} (user_id={user.pk})")

            sendgrid_api_key = os.environ.get('EMAIL_HOST_PASSWORD', '')

            if sendgrid_api_key and sendgrid_api_key.startswith('SG.') and SENDGRID_AVAILABLE:
                logger.info("Using SendGrid HTTP API")
                try:
                    from_email = Email(os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@fintrack.app'))
                    to_email = To(user.email)
                    content = Content("text/plain", message)
                    mail = Mail(from_email, to_email, subject, content)

                    sg = SendGridAPIClient(sendgrid_api_key)
                    response = sg.client.mail.send.post(request_body=mail.get())

                    logger.info(f"SendGrid API response: {response.status_code}")
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"Email sent via SendGrid (user_id={user.pk})")
                    else:
                        logger.error(f"SendGrid error: {response.status_code}")
                except Exception as e:
                    logger.error(f"SendGrid API error: {e}", exc_info=True)
                    raise
            else:
                logger.info("Using SMTP (local development)")
                send_mail(subject, message, None, [user.email], fail_silently=False)
                logger.info(f"Email sent via SMTP (user_id={user.pk})")

        except Exception as e:
            logger.error(f"Background email send failed for {user.username}: {e}", exc_info=True)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def verify_email(request, token):
    """
    Verify user's email address using the token from the verification link.

    Rate limited to 10 attempts per IP per hour to prevent brute force attacks.

    Args:
        request: Django HttpRequest object
        token: UUID token from URL parameter

    Returns:
        HttpResponse: Redirect to login with success/error message
    """
    ip = _get_client_ip(request)
    success, error_msg = verify_email_token(token, ip)

    if error_msg == 'rate_limited':
        messages.error(request, 'Too many verification attempts. Please try again in an hour.')
        logger.warning(f"Rate limit exceeded for verification from IP: {ip}")
        return redirect('login')

    if success:
        messages.success(request, "Email verified! You can now log in.")
        return redirect("login")

    if error_msg == 'expired':
        messages.error(request, 'Verification link has expired. Please use the resend verification option.')
        return redirect('resend_verification')
    elif error_msg == 'invalid':
        messages.error(request, "Invalid or expired verification link.")
        logger.warning(f"Invalid verification token attempted: {token}")
    else:
        messages.error(request, "An error occurred during verification. Please try again.")
        logger.error(f"Error during email verification for token: {token}")

    return redirect("login")


# ----------------------------
# LOGIN VIEW
# ----------------------------
@never_cache
def login_view(request):
    """
    Handle user authentication and login.

    Features:
        - Username/password authentication
        - Session creation on success
        - Redirect to dashboard after login

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Login form or redirect to dashboard on success
    """
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_active:
                    # Account exists and password is correct but email not verified
                    messages.error(
                        request,
                        'Your email address is not verified. Please check your inbox or '
                        '<a href="/accounts/resend-verification/">resend the verification email</a>.'
                    )
                    return render(request, "accounts/auth.html", {
                        "form": form,
                        "page_title": "Welcome Back",
                        "button_text": "Login",
                        "page_type": "login",
                        "hide_auth_nav": True,
                        "show_resend": True,
                    })
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password")

    context = {
        "form": form,
        "page_title": "Welcome Back",
        "button_text": "Login",
        "page_type": "login",
        "hide_auth_nav": True,
    }

    return render(request, "accounts/auth.html", context)


# ----------------------------
# LOGOUT VIEW
# ----------------------------
def logout_view(request):
    """
    Log out the current user and destroy their session.

    Only accepts POST requests for security (prevents CSRF logout attacks).

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Redirect to login page
    """
    logout(request)
    return redirect("login")


logout_view = require_POST(logout_view)


# ----------------------------
# CHANGE PASSWORD VIEW
# ----------------------------
@never_cache
@login_required(login_url='login')
def change_password_view(request):
    """
    Allow authenticated users to change their own password.
    Handles POST only — form lives in a modal on the profile page.
    On success or failure, redirects back to profile.
    """
    from django.contrib.auth import update_session_auth_hash

    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password1    = request.POST.get("new_password1", "")
        new_password2    = request.POST.get("new_password2", "")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("/profile/?pw_error=1")
        elif new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("/profile/?pw_error=1")
        elif len(new_password1) < 8:
            messages.error(request, "New password must be at least 8 characters.")
            return redirect("/profile/?pw_error=1")
        else:
            request.user.set_password(new_password1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")

    return redirect("profile")


# ----------------------------
# RESEND VERIFICATION VIEW
# ----------------------------
@require_http_methods(["GET", "POST"])
def resend_verification(request):
    """
    Resend email verification link to users who didn't receive it.

    Features:
        - Rate limiting (3 resends per email per hour)
        - Doesn't reveal if email exists (security)
        - Creates new token and deletes old one

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Resend form or redirect to login on success
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/resend_verification.html')

        try:
            # Rate limit by IP — max 5 resends per IP per hour
            ip = _get_client_ip(request)
            ip_key = f'resend_ip_{ip}'
            ip_attempts = cache.get(ip_key, 0)
            if ip_attempts >= 5:
                messages.info(request, 'If that email is registered and unverified, a verification link has been sent.')
                return redirect('login')

            # Increment BEFORE sending to prevent race conditions
            cache.set(ip_key, ip_attempts + 1, timeout=3600)

            try:
                user, token_obj = resend_verification_token(email)
                _send_verification_email(request, user, token_obj.token)
                logger.info(f"Verification email resent (user_id={user.pk})")
            except User.DoesNotExist:
                raise

            messages.success(request, 'If that email is registered and unverified, a verification link has been sent. Check your inbox.')

        except User.DoesNotExist:
            messages.success(request, 'If that email is registered and unverified, a verification link has been sent. Check your inbox.')
            logger.info(f"Resend verification attempted for non-existent email: {email}")
        except Exception as e:
            logger.error(f"Error in resend_verification: {e}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')

        request.session['pending_verification_email'] = email
        return redirect('verify_pending')

    # GET request - show form
    return render(request, 'accounts/resend_verification.html', {
        'page_title': 'Resend Verification',
        'hide_auth_nav': True,
    })
