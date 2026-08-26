"""
Plan decorators for view-level feature gating.

Usage:
    @login_required
    @plan_required('export')
    def export_data(request): ...

    @login_required
    @plan_required('ai_insights')
    def insights_view(request): ...

For resource-creating views where the limit only applies on POST,
call check_limit() manually inside the POST block instead of using
this decorator — so GET requests (rendering the form) are never blocked.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from .services.plan_service import check_limit


def plan_required(resource: str):
    """
    Decorator that blocks a view entirely if the user has hit a
    free-tier limit or is trying to access a Pro-only feature.

    Adds a user-facing error message and redirects to the pricing page.
    Safe to stack with @login_required — always check auth first.

    Args:
        resource: One of the resource keys understood by check_limit()
                  e.g. 'export', 'ai_insights', 'csv_import', 'webhook'
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            allowed, msg = check_limit(request.user, resource)
            if not allowed:
                messages.error(request, msg)
                return redirect('pricing')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
