from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone
import uuid


class EmailVerificationToken(models.Model):
    """
    Email verification token for user registration.
    
    Tokens expire after 24 hours and are deleted after verification.
    """
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_token')
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email Verification Token"
        verbose_name_plural = "Email Verification Tokens"
        ordering = ['-created_at']

    def __str__(self):
        return f"Token for {self.user.username}"
    
    def __repr__(self):
        return f"<EmailVerificationToken: {self.user.username} ({self.token})>"
    
    def is_expired(self):
        """Check if token is older than 24 hours"""
        return timezone.now() - self.created_at > timedelta(hours=24)
    
    def clean(self):
        """Validate token data — only check expiry on existing (saved) tokens"""
        if self.pk and self.is_expired():
            raise ValidationError("This verification token has expired.")
