"""
FinTrack - Settings Entry Point

Selects the correct settings file based on DJANGO_SETTINGS_MODULE env var.
Defaults to development settings if not set.

Local dev:   uses settings_dev.py automatically
Production:  set DJANGO_SETTINGS_MODULE=fintrack.settings_prod
"""
import os

env = os.environ.get('DJANGO_SETTINGS_MODULE', '')

if 'prod' in env:
    from .settings_prod import *
else:
    from .settings_dev import *
