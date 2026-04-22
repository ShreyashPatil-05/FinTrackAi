from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.conf import settings
from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm
from .models import EmailVerificationToken


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _verify_recaptcha(response_token):
    """Verify reCAPTCHA token with Google. Returns True if valid."""
    from django.conf import settings
    import urllib.request
    import urllib.parse
    if not settings.RECAPTCHA_SECRET_KEY:
        return True  # skip verification if key not configured (dev fallback)
    try:
        data = urllib.parse.urlencode({
            'secret':   settings.RECAPTCHA_SECRET_KEY,
            'response': response_token,
        }).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json
            result = json.loads(resp.read())
            return result.get('success', False)
    except Exception:
        return False


# ----------------------------
# REGISTER VIEW
# ----------------------------
def register_view(request):
    form = MyUserCreationForm(request.POST or None)

    if request.method == "POST":
        # Rate limit: max 3 registrations per IP per hour
        ip = _get_client_ip(request)
        cache_key = f'register_attempts_{ip}'
        attempts = cache.get(cache_key, 0)

        if attempts >= 3:
            messages.error(request, 'Too many registration attempts. Please try again in an hour.')
            return render(request, "accounts/auth.html", {
                "form": form, "page_title": "Create Account",
                "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
            })

        if form.is_valid():
            # Verify reCAPTCHA
            recaptcha_response = request.POST.get('g-recaptcha-response', '')
            if not _verify_recaptcha(recaptcha_response):
                messages.error(request, 'Please complete the reCAPTCHA verification.')
                return render(request, "accounts/auth.html", {
                    "form": form, "page_title": "Create Account",
                    "button_text": "Register", "page_type": "register", "hide_auth_nav": True,
                })

            user = form.save(commit=False)
            user.is_active = False  # inactive until email verified
            user.save()

            # Increment attempt counter (expires in 1 hour)
            cache.set(cache_key, attempts + 1, timeout=3600)

            # Create verification token and send email
            token_obj = EmailVerificationToken.objects.create(user=user)
            _send_verification_email(request, user, token_obj.token)

            messages.success(request, "Account created! Check your email to verify your account.")
            return redirect("login")
        else:
            messages.error(request, "Registration failed. Please fix the errors.")

    return render(request, "accounts/auth.html", {
        "form": form,
        "page_title": "Create Account",
        "button_text": "Register",
        "page_type": "register",
        "hide_auth_nav": True,
        "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
    })


def _send_verification_email(request, user, token):
    from django.core.mail import send_mail
    from django.urls import reverse
    verify_url = request.build_absolute_uri(
        reverse('verify_email', args=[str(token)])
    )
    send_mail(
        subject='Verify your FinTrack account',
        message=(
            f"Hi {user.username},\n\n"
            f"Click the link below to verify your email address:\n\n"
            f"{verify_url}\n\n"
            f"This link is valid for 24 hours.\n\n"
            f"— FinTrack"
        ),
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )


def verify_email(request, token):
    try:
        token_obj = EmailVerificationToken.objects.get(token=token)

        # Check token is not older than 24 hours
        from django.utils import timezone
        from datetime import timedelta
        if timezone.now() - token_obj.created_at > timedelta(hours=24):
            token_obj.delete()
            messages.error(request, 'Verification link has expired. Please register again.')
            return redirect('register')

        user = token_obj.user
        user.is_active = True
        user.save(update_fields=['is_active'])
        token_obj.delete()
        messages.success(request, "Email verified! You can now log in.")
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
    return redirect("login")


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
