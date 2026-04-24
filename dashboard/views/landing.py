"""
Landing Page View
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse


def landing(request: HttpRequest) -> HttpResponse:
    """
    Display landing page for non-authenticated users.
    
    Redirects authenticated users to dashboard.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Landing page or redirect to dashboard
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")
