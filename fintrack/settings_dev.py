"""
FinTrack - Development Settings
Use this locally: python manage.py runserver --settings=fintrack.settings_dev
Or set: DJANGO_SETTINGS_MODULE=fintrack.settings_dev
"""
from .settings_base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# SQLite for local development — no setup required
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Print emails to console instead of sending — useful when testing locally
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable all HTTPS enforcement locally
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
