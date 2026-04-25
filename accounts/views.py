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
from django.utils import timezone
from django.db import transaction, IntegrityError
import logging
import threading
import os
from datetime import timedelta

# Optional: SendGrid for production email
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm
from .models import EmailVerificationToken

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """
    Extract the client's IP address from the request.
    
    Handles X-Forwarded-For header for proxied requests (Railway, Heroku, etc.)
    Takes the first IP in the chain if multiple proxies are present.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Client IP address
    """
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
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
            # Rate limit: max 3 registrations per IP per hour
            ip = _get_client_ip(request)
            cache_key = f'register_attempts_{ip}'
            attempts = cache.get(cache_key, 0)

            if attempts >= 3:
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

                # Use transaction to prevent race conditions
                try:
                    with transaction.atomic():
                        user = form.save(commit=False)
                        user.is_active = False
                        user.save()

                        # Delete any existing tokens for this user (shouldn't exist, but safety)
                        EmailVerificationToken.objects.filter(user=user).delete()
                        
                        # Create new verification token
                        token_obj = EmailVerificationToken.objects.create(user=user)
                        
                        # Send verification email
                        _send_verification_email(request, user, token_obj.token)
                        
                        # Increment rate limit counter
                        cache.set(cache_key, attempts + 1, timeout=3600)
                        
                        logger.info(f"User registered: {user.username} ({user.email})")

                except IntegrityError as e:
                    logger.error(f"Registration integrity error: {e}")
                    messages.error(request, 'Registration failed. This email or username may already be in use.')
                    return render(request, "accounts/auth.html", {
                        "form": form, "page_title": "Create Account",
                        "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                    })

                # Redirect to "check your email" page
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
            logger.info(f"Attempting to send email to {user.email}")
            
            # Get SendGrid API key from environment
            sendgrid_api_key = os.environ.get('EMAIL_HOST_PASSWORD', '')
            
            # Use SendGrid HTTP API if API key is present
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
                        logger.info(f"Email sent successfully to {user.email} via SendGrid API")
                    else:
                        logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
                except Exception as e:
                    logger.error(f"SendGrid API error: {e}", exc_info=True)
                    raise
            else:
                # Fall back to SMTP for local development
                logger.info("Using SMTP (local development)")
                send_mail(subject, message, None, [user.email], fail_silently=False)
                logger.info(f"Email sent successfully to {user.email} via SMTP")
                
        except Exception as e:
            logger.error(f"Background email send failed for {user.username}: {e}", exc_info=True)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def verify_email(request, token):
    """
    Verify user's email address using the token from the verification link.
    
    Rate limited to 10 attempts per IP per hour to prevent brute force attacks.
    
    Validates:
        - Token exists in database
        - Token is less than 24 hours old
        
    On success:
        - Activates user account
        - Deletes verification token
        
    Args:
        request: Django HttpRequest object
        token: UUID token from URL parameter
        
    Returns:
        HttpResponse: Redirect to login with success/error message
    """
    # Rate limit: max 10 verification attempts per IP per hour
    ip = _get_client_ip(request)
    cache_key = f'verify_attempts_{ip}'
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 10:
        messages.error(request, 'Too many verification attempts. Please try again in an hour.')
        logger.warning(f"Rate limit exceeded for verification from IP: {ip}")
        return redirect('login')
    
    try:
        token_obj = EmailVerificationToken.objects.get(token=token)

        # Check if token is expired
        if token_obj.is_expired():
            token_obj.delete()
            messages.error(request, 'Verification link has expired. Please use the resend verification option.')
            return redirect('resend_verification')

        # Activate user
        user = token_obj.user
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        # Delete token after successful verification
        token_obj.delete()
        
        messages.success(request, "Email verified! You can now log in.")
        logger.info(f"Email verified for user: {user.username}")
        
    except EmailVerificationToken.DoesNotExist:
        # Increment rate limit counter
        cache.set(cache_key, attempts + 1, timeout=3600)
        messages.error(request, "Invalid or expired verification link.")
        logger.warning(f"Invalid verification token attempted: {token}")
    except Exception as e:
        logger.error(f"Error during email verification: {e}", exc_info=True)
        messages.error(request, "An error occurred during verification. Please try again.")
    
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

            # Check if user exists but is inactive (unverified email)
            try:
                unverified_user = User.objects.get(username=username)
                if not unverified_user.is_active and unverified_user.check_password(password):
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
            except User.DoesNotExist:
                pass

            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password")

    context = {
        "form": form,
        "page_title": "Welcome Back",
        "button_text": "Login",
        "page_type": "login",
        "hide_auth_nav": True

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
    if request.method == 'POST':
        logout(request)
    return redirect("login")


# ----------------------------
# CHANGE PASSWORD VIEW
# ----------------------------
@never_cache
def change_password_view(request):
    """
    Allow users to change their password with current password verification.
    
    Security features:
        - Requires current password verification
        - Same error message for wrong password and non-existent user
          (prevents username enumeration)
        - Forces re-login after password change
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Password change form or redirect to login on success
    """
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
                # Same message as wrong password — prevents username enumeration
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
            # Find inactive user with this email
            user = User.objects.get(email=email, is_active=False)
            
            # Rate limit: max 3 resends per email per hour
            cache_key = f'resend_verification_{user.id}'
            attempts = cache.get(cache_key, 0)
            
            if attempts >= 3:
                # Don't reveal if email exists - same message
                messages.info(request, 'If that email is registered and unverified, a verification link has been sent.')
                logger.warning(f"Resend rate limit exceeded for user: {user.username}")
                return redirect('login')
            
            # Delete old token and create new one
            with transaction.atomic():
                EmailVerificationToken.objects.filter(user=user).delete()
                token_obj = EmailVerificationToken.objects.create(user=user)
                
                # Send verification email
                _send_verification_email(request, user, token_obj.token)
                
                # Increment rate limit counter
                cache.set(cache_key, attempts + 1, timeout=3600)
                
                logger.info(f"Verification email resent to: {user.username}")
            
            # Don't reveal if email exists - same message for security
            messages.success(request, 'If that email is registered and unverified, a verification link has been sent. Check your inbox.')
            
        except User.DoesNotExist:
            # Don't reveal if email exists - same message for security
            messages.success(request, 'If that email is registered and unverified, a verification link has been sent. Check your inbox.')
            logger.info(f"Resend verification attempted for non-existent email: {email}")
        except Exception as e:
            logger.error(f"Error in resend_verification: {e}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')

        # Go back to verify_pending page
        request.session['pending_verification_email'] = email
        return redirect('verify_pending')
    
    # GET request - show form
    return render(request, 'accounts/resend_verification.html', {
        'page_title': 'Resend Verification',
        'hide_auth_nav': True,
    })
