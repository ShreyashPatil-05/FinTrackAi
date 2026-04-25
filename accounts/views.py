from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.db import IntegrityError
import logging
import threading
import uuid
import os

# Optional: SendGrid for production email
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm

logger = logging.getLogger(__name__)

# Cache TTL for pending registrations — 24 hours
PENDING_REG_TTL = 86400


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _verify_recaptcha(response_token):
    import urllib.request
    import urllib.parse
    import json

    if not settings.RECAPTCHA_SECRET_KEY:
        return True
    try:
        data = urllib.parse.urlencode({
            'secret':   settings.RECAPTCHA_SECRET_KEY,
            'response': response_token,
        }).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get('success', False)
    except Exception:
        return False


# ----------------------------
# REGISTER VIEW
# ----------------------------
def register_view(request):
    """
    Validate registration form, store pending data in cache, send verification email.
    No user is written to the database until the email link is clicked.
    """
    form = MyUserCreationForm(request.POST or None)

    _ctx = {
        "form": form,
        "page_title": "Create Account",
        "button_text": "Register",
        "page_type": "register",
        "hide_auth_nav": True,
        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
    }

    if request.method == "POST":
        # Rate limit: 3 attempts per IP per hour
        ip = _get_client_ip(request)
        rate_key = f'register_attempts_{ip}'
        attempts = cache.get(rate_key, 0)
        if attempts >= 3:
            messages.error(request, 'Too many registration attempts. Please try again in an hour.')
            return render(request, "accounts/auth.html", _ctx)

        if form.is_valid():
            # reCAPTCHA check
            if not _verify_recaptcha(request.POST.get('g-recaptcha-response', '')):
                messages.error(request, 'Please complete the reCAPTCHA verification.')
                return render(request, "accounts/auth.html", _ctx)

            username = form.cleaned_data['username']
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password1']

            # Double-check uniqueness (form already validates, but be safe)
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'This username is already taken.')
                return render(request, "accounts/auth.html", _ctx)
            if User.objects.filter(email=email).exists():
                form.add_error('email', 'This email address is already registered.')
                return render(request, "accounts/auth.html", _ctx)

            # Generate a unique token
            token = str(uuid.uuid4())

            # Store pending registration in cache (no DB write yet)
            pending_data = {
                'username': username,
                'email':    email,
                'password': password,   # plain text — only lives in cache for 24h
            }
            cache.set(f'pending_reg_{token}', pending_data, timeout=PENDING_REG_TTL)

            # Also store token → email mapping so resend can look it up by email
            cache.set(f'pending_email_{email}', token, timeout=PENDING_REG_TTL)

            # Increment rate limit
            cache.set(rate_key, attempts + 1, timeout=3600)

            # Send verification email (background thread)
            _send_verification_email_raw(request, username, email, token)

            logger.info(f"Pending registration stored for {username} ({email})")
            messages.success(request, "Almost there! Check your email and click the verification link to complete registration.")
            return redirect("login")

        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, "accounts/auth.html", _ctx)


def _send_verification_email_raw(request, username, email, token):
    """
    Send verification email using raw username/email/token (no User object needed).
    Runs in a background thread.
    """
    verify_url = request.build_absolute_uri(
        reverse('verify_email', args=[token])
    )
    subject = 'Verify your FinTrack account'
    body = (
        f"Hi {username},\n\n"
        f"Click the link below to verify your email and complete your registration:\n\n"
        f"{verify_url}\n\n"
        f"This link is valid for 24 hours. If you didn't sign up, ignore this email.\n\n"
        f"— FinTrack"
    )

    def _send():
        try:
            sendgrid_api_key = os.environ.get('EMAIL_HOST_PASSWORD', '')
            if sendgrid_api_key and sendgrid_api_key.startswith('SG.') and SENDGRID_AVAILABLE:
                from_email = Email(os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@fintrack.app'))
                mail = Mail(from_email, To(email), subject, Content("text/plain", body))
                sg = SendGridAPIClient(sendgrid_api_key)
                response = sg.client.mail.send.post(request_body=mail.get())
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Verification email sent to {email} via SendGrid")
                else:
                    logger.error(f"SendGrid error {response.status_code}: {response.body}")
            else:
                send_mail(subject, body, None, [email], fail_silently=False)
                logger.info(f"Verification email sent to {email} via SMTP")
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}", exc_info=True)

    threading.Thread(target=_send, daemon=True).start()


# ----------------------------
# VERIFY EMAIL VIEW
# ----------------------------
def verify_email(request, token):
    """
    Read pending registration from cache, create the user in DB, log them in.
    Token is a plain UUID string (not a DB model anymore).
    """
    # Rate limit: 10 attempts per IP per hour
    ip = _get_client_ip(request)
    rate_key = f'verify_attempts_{ip}'
    attempts = cache.get(rate_key, 0)
    if attempts >= 10:
        messages.error(request, 'Too many verification attempts. Please try again in an hour.')
        return redirect('login')

    pending = cache.get(f'pending_reg_{token}')

    if not pending:
        cache.set(rate_key, attempts + 1, timeout=3600)
        messages.error(request, 'This verification link is invalid or has expired. Please register again.')
        logger.warning(f"Invalid/expired verification token used: {token}")
        return redirect('register')

    username = pending['username']
    email    = pending['email']
    password = pending['password']

    # Final uniqueness check before creating (edge case: someone registered same
    # username/email in the 24h window via Google OAuth etc.)
    if User.objects.filter(username=username).exists():
        cache.delete(f'pending_reg_{token}')
        cache.delete(f'pending_email_{email}')
        messages.error(request, f'The username "{username}" was taken while you were verifying. Please register again.')
        return redirect('register')

    if User.objects.filter(email=email).exists():
        cache.delete(f'pending_reg_{token}')
        cache.delete(f'pending_email_{email}')
        messages.error(request, f'The email "{email}" is already registered. Try logging in.')
        return redirect('login')

    # Create the user — active immediately since email is now verified
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True,
        )
    except IntegrityError:
        messages.error(request, 'Registration failed due to a conflict. Please try again.')
        return redirect('register')

    # Clean up cache
    cache.delete(f'pending_reg_{token}')
    cache.delete(f'pending_email_{email}')

    # Log the user in immediately
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    logger.info(f"User created and verified: {username} ({email})")
    messages.success(request, f"Welcome to FinTrack, {username}! Your account is ready.")
    return redirect('dashboard')


# ----------------------------
# LOGIN VIEW
# ----------------------------
@never_cache
def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)
                return redirect("dashboard")
            else:
                # Check if there's a pending (unverified) registration for this username
                pending_email_key = None
                try:
                    existing = User.objects.get(username=username)
                    # User exists in DB but is_active=False (edge case / old data)
                    if not existing.is_active:
                        messages.error(
                            request,
                            'Your account is inactive. Please contact support.'
                        )
                    else:
                        messages.error(request, "Invalid username or password.")
                except User.DoesNotExist:
                    # Check if there's a pending registration in cache
                    # We can't look up by username easily, so just show generic message
                    # with a hint to check email
                    messages.error(
                        request,
                        'Invalid username or password. '
                        'If you just registered, check your email to verify your account first.'
                    )

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
    if request.method == 'POST':
        logout(request)
    return redirect("login")


# ----------------------------
# CHANGE PASSWORD VIEW
# ----------------------------
@never_cache
def change_password_view(request):
    form = ChangePasswordForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username         = form.cleaned_data.get("username")
            current_password = form.cleaned_data.get("current_password")
            new_password     = form.cleaned_data.get("new_password1")
            try:
                user = User.objects.get(username=username)
                if not user.check_password(current_password):
                    messages.error(request, "Current password is incorrect.")
                else:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, "Password changed successfully. Please log in.")
                    return redirect("login")
            except User.DoesNotExist:
                messages.error(request, "Current password is incorrect.")

    context = {
        "form": form,
        "page_title": "Change Password",
        "button_text": "Update Password",
        "page_type": "change_password",
        "hide_auth_nav": True,
    }
    return render(request, "accounts/auth.html", context)


# ----------------------------
# RESEND VERIFICATION VIEW
# ----------------------------
@require_http_methods(["GET", "POST"])
def resend_verification(request):
    """
    Resend verification email for a pending (cache-only) registration.
    Looks up the pending token by email from cache.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/resend_verification.html')

        # Rate limit: 3 resends per email per hour
        rate_key = f'resend_rate_{email}'
        attempts = cache.get(rate_key, 0)
        if attempts >= 3:
            messages.info(request, 'If that email has a pending registration, a new link has been sent.')
            return redirect('login')

        # Look up existing pending token by email
        existing_token = cache.get(f'pending_email_{email}')
        pending = cache.get(f'pending_reg_{existing_token}') if existing_token else None

        if pending:
            # Generate a fresh token, delete old one
            new_token = str(uuid.uuid4())
            cache.delete(f'pending_reg_{existing_token}')
            cache.set(f'pending_reg_{new_token}', pending, timeout=PENDING_REG_TTL)
            cache.set(f'pending_email_{email}', new_token, timeout=PENDING_REG_TTL)

            _send_verification_email_raw(request, pending['username'], email, new_token)
            cache.set(rate_key, attempts + 1, timeout=3600)
            logger.info(f"Verification email resent for pending registration: {email}")

        # Always same message — don't reveal if email is pending
        messages.success(request, 'If that email has a pending registration, a new verification link has been sent. Check your inbox.')
        return redirect('login')

    return render(request, 'accounts/resend_verification.html', {
        'page_title': 'Resend Verification',
        'hide_auth_nav': True,
    })
