"""
FinTrack - Production Settings
Set this on your server: DJANGO_SETTINGS_MODULE=fintrack.settings_prod
"""
from .settings_base import *
import os

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# SITE_ID — set via environment variable so it works across platforms
# Railway used ID=2, Render/other platforms may use ID=1
SITE_ID = int(os.environ.get('SITE_ID', '1'))

# Trust the forwarded protocol header (works on Railway, Render, Heroku, etc.)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF trusted origins — must include your Railway domain
CSRF_TRUSTED_ORIGINS = [
    f'https://{host.strip()}'
    for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if host.strip()
]

# ── Security headers ──────────────────────────────────────
SECURE_SSL_REDIRECT        = True
SESSION_COOKIE_SECURE      = True
CSRF_COOKIE_SECURE         = True
SESSION_COOKIE_HTTPONLY    = True
SECURE_HSTS_SECONDS        = 31536000   # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD        = True
SECURE_BROWSER_XSS_FILTER  = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Session hardening ─────────────────────────────────────
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE    = 'Strict'
SESSION_COOKIE_AGE      = 3600          # 1 hour idle timeout
SESSION_SAVE_EVERY_REQUEST = True       # slide expiry on activity

# ── PostgreSQL ────────────────────────────────────────────
# Supports DATABASE_URL (Railway/Render/Heroku) or individual vars
import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Supabase session pooler — use sslmode=require and keep connections alive
    conn_max_age = 60
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=conn_max_age, ssl_require=True)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':     os.environ.get('DB_NAME'),
            'USER':     os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST':     os.environ.get('DB_HOST', 'localhost'),
            'PORT':     os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }

# ── WhiteNoise for static files ───────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Redis for sessions and cache (optional) ──────────────
# Set REDIS_URL in your environment to enable Redis-backed sessions and cache.
# Without it, Django falls back to database-backed sessions — fine for single-server deploys.
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Fallback: DB-backed sessions, local memory cache
    # NOTE: LocMemCache is per-process — rate limiting in accounts/views.py
    # will not be shared across multiple Gunicorn workers. Set REDIS_URL
    # in Railway environment variables for reliable rate limiting in production.
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ── Logging ───────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'accounts': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# ── S3 Media Storage (avatars and uploads) ────────────────
# Set USE_S3=true in your environment to enable S3 for media files.
# Without this, media files are stored on local disk and will be lost on redeploy.
if os.environ.get('USE_S3', 'false').lower() == 'true':
    AWS_ACCESS_KEY_ID     = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME    = os.environ.get('AWS_S3_REGION_NAME', 'ap-south-1')
    AWS_S3_CUSTOM_DOMAIN  = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL       = 'private'
    AWS_S3_FILE_OVERWRITE = False

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'bucket_name': AWS_STORAGE_BUCKET_NAME,
                'region_name': AWS_S3_REGION_NAME,
                'default_acl': 'private',
                'file_overwrite': False,
            },
        },
        # Keep WhiteNoise for static files
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
