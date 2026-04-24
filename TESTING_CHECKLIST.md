# Testing Checklist - Email Verification Improvements

**Date:** April 24, 2026  
**Features to Test:** Rate limiting, Resend verification, Token cleanup

---

## 🧪 Manual Testing Guide

### Test 1: Resend Verification Feature

**Steps:**
1. Register a new test user (don't verify email yet)
2. Go to login page: `https://web-production-95045.up.railway.app/accounts/login/`
3. Click "Resend verification" link
4. Enter the email you just registered with
5. Click "Send Verification Email"

**Expected Results:**
- ✅ Success message: "If that email is registered and unverified, a verification link has been sent"
- ✅ New email received in inbox
- ✅ Old verification link should no longer work
- ✅ New verification link should work

**Test Rate Limiting:**
6. Try to resend 3 more times quickly (total 4 attempts)
7. On the 4th attempt, should see same success message (but no email sent)

---

### Test 2: Verification Rate Limiting

**Steps:**
1. Get an invalid verification token (make one up)
2. Try to verify 11 times: `https://web-production-95045.up.railway.app/accounts/verify/00000000-0000-0000-0000-000000000000/`
3. Use same IP address for all attempts

**Expected Results:**
- ✅ First 10 attempts: "Invalid or expired verification link"
- ✅ 11th attempt: "Too many verification attempts. Please try again in an hour"
- ✅ Check logs for warning: "Rate limit exceeded for verification from IP: ..."

---

### Test 3: Token Cleanup Command

**Steps:**
1. SSH into Railway or run locally:
```bash
# Dry run first
python manage.py cleanup_expired_tokens --dry-run

# If tokens exist, actually delete them
python manage.py cleanup_expired_tokens
```

**Expected Results:**
- ✅ Dry run shows count of expired tokens
- ✅ Actual run deletes expired tokens
- ✅ Success message: "Successfully deleted X expired tokens"

**Create Test Data:**
If no expired tokens exist, create one manually:
```python
# In Django shell
from accounts.models import EmailVerificationToken
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Create test user
user = User.objects.create_user('testexpired', 'test@example.com', 'password123')
user.is_active = False
user.save()

# Create expired token
token = EmailVerificationToken.objects.create(user=user)
token.created_at = timezone.now() - timedelta(hours=25)  # 25 hours ago
token.save()

# Now run cleanup command
```

---

### Test 4: Complete Registration Flow

**Steps:**
1. Register new user: `https://web-production-95045.up.railway.app/accounts/register/`
2. Check email for verification link
3. Click verification link
4. Try to login

**Expected Results:**
- ✅ Registration success message
- ✅ Email received within 1 minute
- ✅ Verification link works
- ✅ Can login after verification
- ✅ Token deleted after verification

---

### Test 5: Expired Token Handling

**Steps:**
1. Register new user
2. Wait 25 hours (or manually expire token in database)
3. Try to verify with expired token

**Expected Results:**
- ✅ Error message: "Verification link has expired. Please use the resend verification option."
- ✅ Redirected to resend verification page
- ✅ Expired token deleted from database

---

### Test 6: Security - Email Enumeration

**Steps:**
1. Go to resend verification page
2. Enter email that doesn't exist: `nonexistent@example.com`
3. Submit form

**Expected Results:**
- ✅ Same message as for existing email: "If that email is registered and unverified..."
- ✅ No indication whether email exists or not
- ✅ No error in logs

---

## 🔍 What to Check in Logs

### Successful Operations:
```
INFO: User registered: testuser (test@example.com)
INFO: Attempting to send email to test@example.com
INFO: Email sent successfully to test@example.com via SendGrid API
INFO: Email verified for user: testuser
INFO: Verification email resent to: testuser
```

### Rate Limiting:
```
WARNING: Rate limit exceeded for verification from IP: 123.456.789.0
WARNING: Resend rate limit exceeded for user: testuser
```

### Errors to Watch For:
```
ERROR: Background email send failed for testuser: [error details]
ERROR: SendGrid API error: [error details]
ERROR: Error during email verification: [error details]
```

---

## 📊 Success Criteria

### All Tests Pass If:
- [x] Resend verification works and sends new email
- [x] Rate limiting blocks after threshold
- [x] Token cleanup command works
- [x] Expired tokens redirect to resend page
- [x] No email enumeration vulnerability
- [x] All error messages are user-friendly
- [x] Logs show appropriate info/warning/error messages

---

## 🚨 If Something Fails

### Email Not Received:
1. Check SendGrid dashboard for delivery status
2. Check spam folder
3. Verify `DEFAULT_FROM_EMAIL` is verified in SendGrid
4. Check Railway logs for email errors

### Rate Limiting Not Working:
1. Check if Redis/cache is working: `cache.get('test_key')`
2. Verify IP extraction: Check `_get_client_ip()` returns correct IP
3. Check if behind proxy: Verify `HTTP_X_FORWARDED_FOR` header

### Token Cleanup Fails:
1. Check database connection
2. Verify migration 0001_email_verification_token is applied
3. Check if tokens exist: `EmailVerificationToken.objects.count()`

### Template Not Found:
1. Verify file exists: `accounts/templates/accounts/resend_verification.html`
2. Check `TEMPLATES` setting in `settings.py`
3. Run `python manage.py collectstatic` if needed

---

## 🎯 Quick Test Commands

```bash
# Test token cleanup (dry run)
python manage.py cleanup_expired_tokens --dry-run

# Check for expired tokens
python manage.py shell
>>> from accounts.models import EmailVerificationToken
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> cutoff = timezone.now() - timedelta(hours=24)
>>> EmailVerificationToken.objects.filter(created_at__lt=cutoff).count()

# Check rate limiting cache
>>> from django.core.cache import cache
>>> cache.get('verify_attempts_127.0.0.1')  # Replace with actual IP

# List all verification tokens
>>> EmailVerificationToken.objects.all()
```

---

## ✅ Post-Testing

After all tests pass:

1. **Schedule Token Cleanup**
   - Add to Railway cron or scheduler
   - Run daily at 2 AM: `0 2 * * * python manage.py cleanup_expired_tokens`

2. **Monitor for 1 Week**
   - Check SendGrid dashboard daily
   - Monitor Railway logs for errors
   - Track user registration success rate

3. **Document Any Issues**
   - Note any edge cases found
   - Update documentation if needed
   - Create tickets for future improvements

---

**Status:** Ready for testing  
**Estimated Testing Time:** 30-45 minutes  
**Priority:** High (test before announcing to users)
