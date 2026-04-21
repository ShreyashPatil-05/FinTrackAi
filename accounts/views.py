from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm
from .models import EmailVerificationToken


# ----------------------------
# REGISTER VIEW
# ----------------------------
def register_view(request):
    form = MyUserCreationForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # inactive until email verified
            user.save()

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
                messages.error(request, "No account found with that username.")

    context = {
        "form": form,
        "page_title": "Change Password",
        "button_text": "Update Password",
        "page_type": "change_password",
        "hide_auth_nav": True,
    }
    return render(request, "accounts/auth.html", context)
