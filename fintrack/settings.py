"""
FinTrack - Settings Entry Point

Automatically selects the correct settings file:
- If DATABASE_URL is set (Railway/Render/Supabase) → production settings
- If DJANGO_SETTINGS_MODULE contains 'prod' → production settings
- Otherwise → development settings (SQLite, DEBUG=True)
"""
import os

_env = os.environ.get('DJANGO_SETTINGS_MODULE', '')
_has_db_url = bool(os.environ.get('DATABASE_URL', ''))

if 'prod' in _env or _has_db_url:
    from .settings_prod import *
else:
    from .settings_dev import *
