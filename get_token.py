import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fintrack.settings_dev')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import WebhookToken

# List all users
users = User.objects.all()
if not users.exists():
    print("No users found. Create one first with: python manage.py createsuperuser --settings=fintrack.settings_dev")
else:
    print("Users in local DB:")
    for u in users:
        print(f"  [{u.pk}] {u.username} (active={u.is_active})")

    # Use first active user
    user = users.filter(is_active=True).first()
    if not user:
        print("No active users found.")
    else:
        print(f"\nGenerating token for: {user.username}")
        try:
            token_obj = user.webhook_token
            raw = token_obj.regenerate()
        except WebhookToken.DoesNotExist:
            token_obj = WebhookToken(user=user)
            token_obj.save()
            raw = token_obj._raw_token

        print(f"\nYour webhook token:\n  {raw}")
        print(f"\nRun:\n  python test_webhook.py {raw}")
