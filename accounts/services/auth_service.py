"""
Auth Service

Business logic for user registration, email verification, and rate limiting.
"""
import logging
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth.models import User

from ..models import EmailVerificationToken

logger = logging.getLogger(__name__)


def check_register_rate_limit(ip):
    """
    Check whether a registration attempt from an IP is allowed.

    Args:
        ip: Client IP address string

    Returns:
        tuple: (allowed: bool, attempts: int)
    """
    cache_key = f'register_attempts_{ip}'
    attempts = cache.get(cache_key, 0)
    return attempts < 3, attempts


def increment_register_rate_limit(ip, attempts):
    """
    Increment the registration attempt counter for an IP.

    Args:
        ip: Client IP address string
        attempts: Current attempt count (will be incremented by 1)
    """
    cache_key = f'register_attempts_{ip}'
    cache.set(cache_key, attempts + 1, timeout=3600)


def create_user_with_token(form):
    """
    Atomically save a new inactive user and create an email verification token.

    Args:
        form: Validated MyUserCreationForm instance

    Returns:
        tuple: (user, token_obj) where token_obj is an EmailVerificationToken

    Raises:
        IntegrityError: If username or email already exists
    """
    with transaction.atomic():
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # Delete any existing tokens for this user (safety measure)
        EmailVerificationToken.objects.filter(user=user).delete()

        token_obj = EmailVerificationToken.objects.create(user=user)

    return user, token_obj


def verify_email_token(token, ip):
    """
    Validate an email verification token and activate the user.

    Args:
        token: UUID token string from the verification URL
        ip: Client IP address for rate limiting

    Returns:
        tuple: (success: bool, error_msg: str)
                success=True means user was activated; error_msg is empty on success.
    """
    cache_key = f'verify_attempts_{ip}'
    attempts = cache.get(cache_key, 0)

    if attempts >= 10:
        return False, 'rate_limited'

    try:
        token_obj = EmailVerificationToken.objects.get(token=token)

        if token_obj.is_expired():
            token_obj.delete()
            return False, 'expired'

        user = token_obj.user
        user.is_active = True
        user.save(update_fields=['is_active'])
        token_obj.delete()

        logger.info(f"Email verified for user: {user.username}")
        return True, ''

    except EmailVerificationToken.DoesNotExist:
        cache.set(cache_key, attempts + 1, timeout=3600)
        return False, 'invalid'
    except Exception as e:
        logger.error(f"Error during email verification: {e}", exc_info=True)
        return False, 'error'


def check_verify_rate_limit(ip):
    """
    Check whether a verification attempt from an IP is allowed.

    Args:
        ip: Client IP address string

    Returns:
        bool: True if allowed, False if rate limited
    """
    cache_key = f'verify_attempts_{ip}'
    attempts = cache.get(cache_key, 0)
    return attempts < 10


def resend_verification_token(email):
    """
    Atomically delete the old token and create a new one for an unverified user.

    Args:
        email: Email address of the unverified user

    Returns:
        tuple: (user, token_obj)

    Raises:
        User.DoesNotExist: If no inactive user with that email exists
        Exception: On any other error
    """
    user = User.objects.get(email=email, is_active=False)

    with transaction.atomic():
        EmailVerificationToken.objects.filter(user=user).delete()
        token_obj = EmailVerificationToken.objects.create(user=user)

    logger.info(f"Verification token regenerated for: {user.username}")
    return user, token_obj


def is_unverified_user(username, password):
    """
    Check if a user exists, is inactive (unverified), and the password matches.

    Args:
        username: Username string
        password: Plain-text password string

    Returns:
        bool: True if user exists, is inactive, and password is correct
    """
    try:
        user = User.objects.get(username=username)
        return not user.is_active and user.check_password(password)
    except User.DoesNotExist:
        return False
