"""
FinTrack - Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render


# Error handlers — active when DEBUG=False
handler404 = lambda request, exception: render(request, '404.html', status=404)


def custom_404(request, *args, **kwargs):
    return render(request, '404.html', status=404)


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication  (register, login, logout, change-password)
    path('accounts/', include('accounts.urls')),

    # Google OAuth via django-allauth
    path('social/', include('allauth.urls')),

    # Expenses  (list, add, edit, delete, bulk-delete)
    path('expenses/', include('expenses.urls')),

    # Core app  (dashboard, settings, savings, subscriptions, profile, export)
    path('', include('dashboard.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [

    # Catch-all — must stay last, renders 404 for any unmatched route
    re_path(r'^.*$', custom_404),
]
