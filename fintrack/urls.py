"""
URL configuration for fintrack project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

# Custom error handlers (active when DEBUG=False)
handler404 = lambda request, exception: render(request, '404.html', status=404)

def custom_404(request, *args, **kwargs):
    return render(request, '404.html', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('dashboard.urls')),
    path('expenses/', include('expenses.urls')),
    # Catch-all — must be last, handles any unmatched URL
    re_path(r'^.*$', custom_404),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
