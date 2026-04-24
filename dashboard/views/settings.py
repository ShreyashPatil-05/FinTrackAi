"""
Settings Dispatcher View

Redirects to default settings page.
"""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse


@login_required(login_url='login')
def settings(request: HttpRequest) -> HttpResponse:
    """
    Redirect to default settings page (income).
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Redirect to income settings
    """
    return redirect('settings_income')
