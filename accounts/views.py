from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import MyUserCreationForm, LoginForm, ChangePasswordForm


# ----------------------------
# REGISTER VIEW
# ----------------------------
def register_view(request):

    form = MyUserCreationForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Registration failed. Please fix the errors.")

    context = {
        "form": form,
        "page_title": "Create Account",
        "button_text": "Register",
        "page_type": "register",
        "hide_auth_nav": True

    }

    return render(request, "accounts/auth.html", context)


# ----------------------------
# LOGIN VIEW
# ----------------------------
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
def change_password_view(request):
    form = ChangePasswordForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            new_password = form.cleaned_data.get("new_password1")
            try:
                user = User.objects.get(username=username)
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
