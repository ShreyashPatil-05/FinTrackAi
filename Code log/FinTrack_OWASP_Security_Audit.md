# FinTrack — Full OWASP Top 10 Security Audit

Gathering all security-relevant files for a comprehensive OWASP audit
Read every security-relevant file in the FinTrack Django project at E:\Projects\fintrack for a full OWASP Top 10 security audit. Read ALL of these files completely:

1. fintrack/settings_base.py
2. fintrack/settings_prod.py
3. fintrack/settings_dev.py
4. fintrack/middleware.py
5. fintrack/urls.py
6. accounts/views.py
7. accounts/models.py
8. accounts/forms.py
9. accounts/services/auth_service.py
10. accounts/urls.py
11. dashboard/views/profile.py
12. dashboard/views/export.py
13. dashboard/views/upload.py
14. expenses/views.py
15. expenses/webhook.py
16. expenses/models.py
17. dashboard/models.py
18. .env (check for exposed secrets)
19. requirements.txt
20. dashboard/views/insights.py (for API key handling)

For each file, identify:
- Hardcoded secrets or API keys
- Missing authentication decorators
- Missing authorization checks (user ownership)
- SQL injection risks
- XSS vulnerabilities
- CSRF issues
- Insecure file upload handling
- Rate limiting gaps
- Session security issues
- Insecure direct object references (IDOR)
- Missing input validation
- Logging of sensitive data
- Any other OWASP Top 10 issues

Be exhaustive and specific — include file name, function name, and exact line/pattern for each finding.

Let me batch-read all the security-relevant files in parallel.

Read file(s)

settings_base.py

settings_prod.py

settings_dev.py

middleware.py

fintrack/urls.py

accounts/views.py

accounts/models.py

forms.py

auth_service.py

accounts/urls.py

profile.py

export.py

upload.py

insights.py

expenses/views.py

webhook.py

expenses/models.py

dashboard/models.py

.env

requirements.txt
Now I have everything needed. Here is the full, exhaustive OWASP Top 10 security audit.

FinTrack — Full OWASP Top 10 Security Audit
🔴 CRITICAL
[C1] .env — Real Secrets Committed to Repository
File: .env OWASP: A02 Cryptographic Failures / A07 Identification & Authentication Failures

The .env file contains live, real credentials that appear to be committed to the repository (it's present in the file tree, not gitignored from the project root):

SECRET_KEY=^lcngywzqblm#2^l8j$pi111)-2zd*)05f1*#&030d_wvxjei(
EMAIL_HOST_USER=shreyashpatil655@gmail.com
EMAIL_HOST_PASSWORD=jcvtpqwojimtfswr        ← Gmail App Password (live)
RECAPTCHA_SITE_KEY=6LfgE8QsAAAAAOpuZNBG3x08ICllYqKpJfqT_fhG
RECAPTCHA_SECRET_KEY=6LfgE8QsAAAAALXtgIYBQAh3G9ssPET-SstxBKzR
BANK_WEBHOOK_SECRET=fintrack-mock-bank-secret-2026
Risk: Anyone with repo access has your Gmail app password, Django secret key, and reCAPTCHA secret. The Gmail app password can be used to send email as you. The Django SECRET_KEY being exposed means session cookies, CSRF tokens, and signed data can all be forged.

Fix:

Immediately revoke the Gmail app password and generate a new one
Rotate the Django SECRET_KEY (all existing sessions will be invalidated — that's fine)
Add .env to .gitignore and verify it's not in git history (git log --all --full-history -- .env)
If it's in history, use git filter-repo to purge it
[C2] 
views.py
 — change_password_view Does Not Require Login
File: 
views.py
, function change_password_view OWASP: A07 Identification & Authentication Failures

@never_cache
def change_password_view(request):
    ...
    user = User.objects.get(username=username)
    if not user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
    else:
        user.set_password(new_password)
There is no @login_required decorator. The view accepts a username field from POST data and changes the password for any user by username. While it does verify the current password, this endpoint is fully accessible to unauthenticated users and accepts the target username from user-supplied input.

Risk: An attacker who knows (or guesses) a username and current password can change the password without being logged in. More critically, this design means the password change form is a standalone unauthenticated endpoint — it doesn't tie the operation to the currently authenticated session.

Fix:

@never_cache
@login_required(login_url='login')
def change_password_view(request):
    # Remove the username field entirely — use request.user
    user = request.user
    if not user.check_password(current_password):
        ...
Remove the username field from ChangePasswordForm and use request.user instead.

[C3] 
views.py
 — logout_view Accepts GET Requests (CSRF Logout)
File: 
views.py
, function logout_view OWASP: A01 Broken Access Control / CSRF

def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect("login")
If the request is GET, the user is not logged out but is silently redirected to login. This means:

A <img src="/accounts/logout/"> tag on any page will silently fail but not error — the user stays logged in thinking they logged out.
More importantly, there is no @login_required — any unauthenticated request hits this view.
The view has no CSRF protection decorator, and since it only acts on POST, it relies on Django's global CSRF middleware — which is correct, but the silent GET behavior is misleading.
Fix: Add @require_POST to enforce POST-only and make the behavior explicit:

from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")
🟠 HIGH
[H1] 
views.py
 — Login Has No Rate Limiting
File: 
views.py
, function login_view OWASP: A07 Identification & Authentication Failures

@never_cache
def login_view(request):
    ...
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
django-axes is installed and configured in settings_base.py (AXES_FAILURE_LIMIT = 5), but axes works via the AxesStandaloneBackend authentication backend. The login view uses authenticate() which does go through the backends — so axes should fire. However:

AXES_LOCKOUT_PARAMETERS = ['ip_address'] only — no username-based lockout. An attacker can brute-force a single account from many IPs (distributed attack).
There is no CAPTCHA on the login form (only on registration).
The axes lockout response is not customized — a locked-out user gets a generic error with no guidance.
Fix:

# settings_base.py
AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]  # lock on IP+username combo
Add reCAPTCHA to the login form after N failures.

[H2] 
upload.py
 — CSV Data Stored in Session (No Size Limit)
File: 
upload.py
, settings_upload OWASP: A04 Insecure Design / DoS

request.session['csv_data'] = decoded
The entire decoded CSV file content is stored in the session. There is a 2MB file size check on avatar uploads but no size limit on CSV uploads. A user can upload an arbitrarily large CSV file, which gets stored in the session (database or Redis depending on config).

Risk: Memory exhaustion / DoS. With database-backed sessions (the fallback when Redis is not set), this writes unbounded data to the django_session table.

Fix:

# Add before storing in session
MAX_CSV_SIZE = 1 * 1024 * 1024  # 1MB
if csv_file.size > MAX_CSV_SIZE:
    error = "CSV file too large. Maximum size is 1MB."
else:
    request.session['csv_data'] = decoded
[H3] 
webhook.py
 — No Rate Limiting on Webhook Endpoint
File: 
webhook.py
, bank_webhook OWASP: A04 Insecure Design / DoS

@csrf_exempt
@require_POST
def bank_webhook(request):
    token = request.headers.get('X-Bank-Token', '')
    token_obj = WebhookToken.verify(token)
The webhook endpoint has no rate limiting. An attacker with a valid token can flood the endpoint and create thousands of Expense records. Even without a valid token, the endpoint performs a SHA-256 hash and a database lookup on every unauthenticated request.

Fix: Add django-axes or a simple cache-based rate limiter:

from django.core.cache import cache

def bank_webhook(request):
    ip = request.META.get('REMOTE_ADDR', '')
    rate_key = f'webhook_rate_{ip}'
    hits = cache.get(rate_key, 0)
    if hits > 60:  # 60 requests/minute
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    cache.set(rate_key, hits + 1, timeout=60)
    ...
[H4] 
middleware.py
 — CSP Uses 'unsafe-inline' for Scripts
File: 
middleware.py
, ContentSecurityPolicyMiddleware OWASP: A03 Injection (XSS)

"script-src 'self' 'unsafe-inline' cdn.jsdelivr.net www.google.com ..."
'unsafe-inline' in script-src completely defeats the XSS protection that CSP is meant to provide. Any injected inline <script> tag will execute.

Fix: Use a nonce-based CSP:

import secrets

def __call__(self, request):
    nonce = secrets.token_urlsafe(16)
    request.csp_nonce = nonce
    response = self.get_response(request)
    csp = (
        f"script-src 'self' 'nonce-{nonce}' cdn.jsdelivr.net www.google.com ...;"
    )
Then use {{ request.csp_nonce }} in templates for inline scripts.

[H5] settings_base.py — SOCIALACCOUNT_LOGIN_ON_GET = True
File: 
settings_base.py
 OWASP: A01 Broken Access Control / CSRF

SOCIALACCOUNT_LOGIN_ON_GET = True
This allows OAuth login to be initiated via a GET request. This is a known CSRF vector — an attacker can embed <img src="/social/google/login/"> and silently initiate an OAuth flow for the victim, potentially linking the attacker's Google account to the victim's session (account takeover via OAuth account linking).

Fix:

SOCIALACCOUNT_LOGIN_ON_GET = False  # Require POST for OAuth initiation
[H6] 
views.py
 — _get_client_ip Trusts X-Forwarded-For Unconditionally
File: 
views.py
, _get_client_ip OWASP: A07 Identification & Authentication Failures

def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
This function is used for rate limiting (registration, email verification). X-Forwarded-For is a client-controlled header — any client can set it to any value. An attacker can bypass all IP-based rate limits by rotating the X-Forwarded-For header:

X-Forwarded-For: 1.2.3.4
X-Forwarded-For: 1.2.3.5
X-Forwarded-For: 1.2.3.6
Fix: Only trust X-Forwarded-For when behind a known proxy. In production (Railway), use Django's SECURE_PROXY_SSL_HEADER and configure NUM_PROXIES or use django-ipware with TRUSTED_PROXY_LIST:

# Use the rightmost IP in X-Forwarded-For (set by your trusted proxy)
# or use django-ipware:
from ipware import get_client_ip
ip, is_routable = get_client_ip(request)
[H7] 
profile.py
 — Avatar Upload: WebP Magic Bytes Not Validated
File: 
profile.py
, profile OWASP: A04 Insecure Design / File Upload

allowed_signatures = [
    b'\xff\xd8\xff',           # JPEG
    b'\x89PNG\r\n\x1a\n',     # PNG
    b'GIF87a', b'GIF89a',     # GIF
    b'RIFF',                   # WebP (WRONG)
]
The WebP check uses b'RIFF' which matches any RIFF container — WAV audio files, AVI video files, and other RIFF-based formats all start with b'RIFF'. A WAV file would pass this check. The correct WebP signature is RIFF....WEBP (bytes 0-3 are RIFF, bytes 8-11 are WEBP).

Fix:

# Check for WebP specifically
is_webp = header[:4] == b'RIFF' and len(header) >= 12 and header[8:12] == b'WEBP'
allowed = (
    header.startswith(b'\xff\xd8\xff') or   # JPEG
    header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
    header.startswith(b'GIF87a') or
    header.startswith(b'GIF89a') or
    is_webp
)
Also: the file extension is not validated or normalized. The uploaded file retains whatever name the user gave it. Django's ImageField with Pillow does re-validate on save, but the magic-byte check happens before that and could give false confidence.

[H8] 
views.py
 — login_view Error Message Enables Username Enumeration (Partial)
File: 
views.py
, login_view OWASP: A07 Identification & Authentication Failures

if is_unverified_user(username, password):
    messages.error(request,
        'Your email address is not verified...'
    )
    ...
user = authenticate(request, username=username, password=password)
if user:
    login(request, user)
else:
    messages.error(request, "Invalid username or password")
The is_unverified_user check reveals that a specific username exists AND has a matching password but is unverified. This is a distinct error message from "Invalid username or password", which allows an attacker to enumerate:

Valid username + correct password → "not verified" (confirms account exists with that exact password)
Valid username + wrong password → "Invalid username or password"
Invalid username → "Invalid username or password"
Case 1 is a significant information leak — it confirms both the username and password are correct.

Fix: After a successful authenticate() call, check user.is_active rather than using a separate pre-check:

user = authenticate(request, username=username, password=password)
if user is not None:
    if not user.is_active:
        messages.error(request, 'Your email address is not verified...')
    else:
        login(request, user)
        return redirect("dashboard")
else:
    messages.error(request, "Invalid username or password")
🟡 MEDIUM
[M1] 
settings_base.py
 — ACCOUNT_EMAIL_VERIFICATION = 'none' for allauth
File: 
settings_base.py
 OWASP: A07 Identification & Authentication Failures

ACCOUNT_EMAIL_VERIFICATION = 'none'
The allauth email verification is disabled. The project implements its own email verification, but allauth's own flows (password reset, email change via allauth) bypass this entirely. If any allauth-managed views are reachable, they won't enforce email verification.

Fix: Either use allauth's built-in verification (ACCOUNT_EMAIL_VERIFICATION = 'mandatory') or ensure all allauth views that require verified email are properly gated.

[M2] 
settings_prod.py
 — Redis Optional, Rate Limiting Broken Without It
File: 
settings_prod.py
 OWASP: A07 Identification & Authentication Failures

# NOTE: LocMemCache is per-process — rate limiting in accounts/views.py
# will not be shared across multiple Gunicorn workers.
The code itself documents this problem. With multiple Gunicorn workers (the default in production), each worker has its own LocMemCache. Rate limiting counters are not shared — an attacker gets N × limit attempts where N is the number of workers. With 4 workers and a limit of 3, that's 12 registration attempts per hour per IP.

Fix: Make Redis mandatory in production, or document clearly that single-worker deployment is required without Redis. Add a startup check:

# settings_prod.py
if not REDIS_URL:
    import warnings
    warnings.warn("REDIS_URL not set — rate limiting will not work correctly with multiple workers", RuntimeWarning)
[M3] 
export.py
 — No Rate Limiting on Data Export
File: 
export.py
, export_data OWASP: A04 Insecure Design

The export endpoint generates and streams CSV data for all of a user's financial records. There is no rate limiting. An authenticated user (or a compromised session) can hammer this endpoint to repeatedly download all financial data or cause excessive database load.

[M4] 
webhook.py
 — txn_date Not Validated
File: 
webhook.py
, bank_webhook OWASP: A03 Injection / A04 Insecure Design

txn_date = data.get('date', str(date.today()))

expense = Expense.objects.create(
    ...
    date=txn_date,
    ...
)
The date field from the webhook payload is passed directly to Expense.objects.create() without validation. Django's DateField will raise a ValueError on invalid input, but:

There's no try/except around the create() call for this specific error — it would return a 500.
An attacker with a valid token can create expenses with arbitrary past or future dates (e.g., "date": "1900-01-01" or "date": "2099-12-31"), polluting the user's financial history.
Fix:

from datetime import datetime, date as date_type

date_str = data.get('date', str(date_type.today()))
try:
    txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    if txn_date > date_type.today():
        return JsonResponse({'error': 'Date cannot be in the future'}, status=400)
except ValueError:
    return JsonResponse({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)
[M5] 
upload.py
 — CSV Import Has No Row Count Limit
File: 
upload.py
, settings_upload OWASP: A04 Insecure Design / DoS

rows = list(reader)
...
for row_num, row in enumerate(reader, start=2):
    Expense.objects.create(...)
list(reader) loads the entire CSV into memory. The import loop calls Expense.objects.create() once per row — no bulk insert, no row limit. A CSV with 100,000 rows would make 100,000 individual INSERT queries.

Fix:

MAX_ROWS = 1000
rows = list(reader)
if len(rows) > MAX_ROWS:
    error = f"CSV too large. Maximum {MAX_ROWS} rows allowed."
else:
    # Use bulk_create for performance
    expenses_to_create = []
    ...
    Expense.objects.bulk_create(expenses_to_create, batch_size=500)
[M6] 
views.py
 — _send_verification_email Leaks Email Address in Log
File: 
views.py
, _send_verification_email OWASP: A09 Security Logging and Monitoring Failures

logger.info(f"Attempting to send email to {user.email}")
logger.info(f"Email sent successfully to {user.email} via SendGrid API")
logger.info(f"Email sent successfully to {user.email} via SMTP")
User email addresses are logged at INFO level. In production, logs are often shipped to third-party services (Datadog, Papertrail, etc.) and retained for extended periods. Email addresses are PII and should not appear in logs.

Fix: Log a user ID or masked email instead:

masked = user.email[:2] + '***@' + user.email.split('@')[1]
logger.info(f"Email sent to {masked} (user_id={user.pk})")
[M7] 
views.py
 — resend_verification Rate Limit Bypass
File: 
views.py
, resend_verification OWASP: A07 Identification & Authentication Failures

try:
    user_check = User.objects.get(email=email, is_active=False)
    cache_key = f'resend_verification_{user_check.id}'
    attempts = cache.get(cache_key, 0)
    if attempts >= 3:
        ...
    user, token_obj = resend_verification_token(email)
    _send_verification_email(request, user, token_obj.token)
    cache.set(cache_key, attempts + 1, timeout=3600)
except User.DoesNotExist:
    raise
The rate limit key is resend_verification_{user_check.id} — keyed on user ID, not IP. An attacker can bypass this by using different source IPs (or even the same IP, since there's no IP-based check here). The rate limit only applies per-user, not per-requester.

Also: the rate limit counter is only incremented after the email is sent. If _send_verification_email raises an exception before cache.set, the counter is never incremented.

Fix: Key on IP address as well, and increment the counter before sending:

ip = _get_client_ip(request)
ip_key = f'resend_ip_{ip}'
ip_attempts = cache.get(ip_key, 0)
if ip_attempts >= 5:
    # rate limit
    ...
cache.set(ip_key, ip_attempts + 1, timeout=3600)  # increment first
_send_verification_email(...)
[M8] 
settings_base.py
 — Session Cookie Missing SameSite Attribute
File: 
settings_base.py
 / settings_prod.py OWASP: A01 Broken Access Control / CSRF

Neither settings file sets SESSION_COOKIE_SAMESITE. Django's default is 'Lax', which is acceptable but not ideal. More importantly, CSRF_COOKIE_SAMESITE is also not set. For a financial application, 'Strict' is recommended.

Fix:

# settings_prod.py
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour — consider shorter for financial app
[M9] 
insights.py
 — Gemini API Error Logged with Full Exception
File: 
insights.py
, _call_gemini and _parse_insights OWASP: A09 Security Logging and Monitoring Failures

logger.error(f"Gemini API error: {e}", exc_info=True)
logger.error(f"Failed to parse Gemini response: {e}\nRaw: {raw[:200]}")
The raw Gemini response (first 200 chars) is logged on parse failure. If Gemini ever echoes back user financial data in an error response, that data ends up in logs. The exc_info=True also dumps full stack traces which can reveal internal paths and logic.

[M10] 
profile.py
 — Email Change Without Verification
File: 
profile.py
, profile OWASP: A07 Identification & Authentication Failures

user.email = request.POST.get("email", "").strip()
user.save()
A user can change their email address to any value without verifying ownership of the new address. This means:

A user can claim someone else's email address
If email is used for account recovery, this is an account takeover vector
No uniqueness check on the new email
Fix:

new_email = request.POST.get("email", "").strip()
if new_email != user.email:
    if User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
        messages.error(request, 'That email is already in use.')
        return redirect('profile')
    # Send verification to new email before changing
    # Store pending_email in UserProfile and verify before applying
[M11] 
settings_prod.py
 — SESSION_COOKIE_AGE Not Set
File: 
settings_prod.py
 OWASP: A07 Identification & Authentication Failures

Django's default SESSION_COOKIE_AGE is 2 weeks (1,209,600 seconds). For a financial application, this is too long. A stolen session cookie remains valid for 2 weeks.

Fix:

SESSION_COOKIE_AGE = 3600  # 1 hour, or 28800 for 8 hours
SESSION_SAVE_EVERY_REQUEST = True  # Slide the expiry on activity
[M12] 
webhook.py
 — merchant Field Not Length-Limited
File: 
webhook.py
, bank_webhook OWASP: A03 Injection

title=str(data['merchant']).strip(),
Expense.title has max_length=200 in the model, but there's no explicit truncation or validation in the webhook handler. Django will raise a DataError on databases that enforce length (PostgreSQL), or silently truncate on SQLite. This should be explicitly validated:

merchant = str(data['merchant']).strip()[:200]
if not merchant:
    return JsonResponse({'error': 'merchant cannot be empty'}, status=400)
🟢 LOW / INFORMATIONAL
[L1] 
urls.py
 — MEDIA_URL Served in All Environments
File: 
urls.py
 OWASP: A05 Security Misconfiguration

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
django.conf.urls.static.static() only adds the route when DEBUG=True, so this is safe in production. However, in production with S3 disabled, media files (including user avatars) are served from local disk with no access control — any URL like 
filename.jpg
 is publicly accessible without authentication.

Fix: If not using S3, serve media through a view that checks authentication, or use nginx X-Accel-Redirect with auth checks.

[L2] 
models.py
 — WebhookToken.verify Does Redundant hmac.compare_digest
File: 
models.py
, WebhookToken.verify OWASP: A02 Cryptographic Failures (informational)

obj = cls.objects.select_related('user').get(token_hash=token_hash)
if hmac.compare_digest(obj.token_hash, token_hash):
    return obj
The hmac.compare_digest after a .get(token_hash=token_hash) is redundant — if the .get() succeeded, the hashes are already equal. The timing-attack protection should be at the hash comparison level, not after a database lookup that already reveals existence. The database lookup itself is the timing oracle. The correct approach is to hash the input and do a constant-time DB lookup, which this code does correctly via the hash — the hmac.compare_digest is just dead code.

[L3] 
views.py
 — change_password_view Doesn't Invalidate Other Sessions
File: 
views.py
, change_password_view OWASP: A07 Identification & Authentication Failures

user.set_password(new_password)
user.save()
messages.success(request, "Password changed successfully. Please log in.")
return redirect("login")
After a password change, only the current session is implicitly invalidated (by redirecting to login). Other active sessions (e.g., on other devices) remain valid. Django provides update_session_auth_hash() to handle this, but since this view doesn't require login, the user isn't logged in to begin with — however, if they were logged in on another device, that session stays alive.

Fix: After password change, call django.contrib.auth.update_session_auth_hash(request, user) if the user is authenticated, and consider adding a mechanism to invalidate all other sessions.

[L4] 
middleware.py
 — CSP Missing upgrade-insecure-requests in Production
File: 
middleware.py
 OWASP: A05 Security Misconfiguration

The CSP middleware applies the same policy in dev and prod. In production, upgrade-insecure-requests should be added to the CSP to force all mixed content to HTTPS.

[L5] 
upload.py
 — CSV Preview Stored in Session Indefinitely
File: 
upload.py
 OWASP: A04 Insecure Design

request.session['csv_data'] = decoded
The CSV data is stored in the session with request.session.pop('csv_data', None) on import. But if the user previews a CSV and then navigates away without importing, the CSV data remains in the session until it expires (up to 2 weeks by default). This wastes session storage and keeps potentially sensitive financial data in the session store longer than necessary.

Fix: Set a short TTL or use session.set_expiry() for this specific key, or store a temporary file reference instead.

[L6] requirements.txt — Unpinned psycopg2-binary and requests
File: requirements.txt OWASP: A06 Vulnerable and Outdated Components

psycopg2-binary>=2.9.10
requests>=2.32.0
These use >= (minimum version) rather than exact pins. A future release with a breaking change or vulnerability could be automatically installed. All dependencies should be pinned to exact versions in production.

[L7] 
views.py
 — verify_pending Leaks Email from Session
File: 
views.py
, verify_pending OWASP: A01 Broken Access Control

def verify_pending(request):
    email = request.session.get('pending_verification_email', '')
    return render(request, 'accounts/verify_pending.html', {'email': email})
This view is accessible without authentication. If someone knows the URL and the session cookie (e.g., shared computer), they can see the pending email address. This is low risk but worth noting.

[L8] 
settings_base.py
 — AXES_COOLOFF_TIME = 0.25 (15 minutes)
File: 
settings_base.py
 OWASP: A07 Identification & Authentication Failures

AXES_COOLOFF_TIME = 0.25  # hours = 15 minutes
15 minutes is a short lockout window. For a financial application, consider 1 hour or progressive lockout (15 min → 1 hour → 24 hours).

Summary Table
ID	Severity	File	Issue
C1	🔴 Critical	.env	Live secrets committed (Gmail password, SECRET_KEY, reCAPTCHA)
C2	🔴 Critical	
views.py
`change_password_view
FinTrack — Full OWASP Top 10 Security Audit
All 20 requested files were read completely. Here are all findings, exhaustive and specific.

🔴 CRITICAL
[C1] .env — Live Secrets Committed to Repository
File: .env OWASP: A02 Cryptographic Failures / A07 Authentication Failures

SECRET_KEY=^lcngywzqblm#2^l8j$pi111)-2zd*)05f1*#&030d_wvxjei(
EMAIL_HOST_USER=shreyashpatil655@gmail.com
EMAIL_HOST_PASSWORD=jcvtpqwojimtfswr        ← live Gmail App Password
RECAPTCHA_SITE_KEY=6LfgE8QsAAAAAOpuZNBG3x08ICllYqKpJfqT_fhG
RECAPTCHA_SECRET_KEY=6LfgE8QsAAAAALXtgIYBQAh3G9ssPET-SstxBKzR
BANK_WEBHOOK_SECRET=fintrack-mock-bank-secret-2026
Risk: Anyone with repo access has your Gmail app password, Django secret key, and reCAPTCHA secret. The exposed SECRET_KEY means session cookies, CSRF tokens, and all signed data can be forged. The Gmail app password can be used to send email as you.

Fix:

Immediately revoke the Gmail app password and generate a new one
Rotate the Django SECRET_KEY (invalidates all existing sessions — acceptable)
Verify .env is in .gitignore and not in git history: git log --all --full-history -- .env
If in history, purge with git filter-repo --path .env --invert-paths
[C2] 
views.py
 — change_password_view Has No @login_required
File: 
views.py
, function change_password_view (line ~200) OWASP: A07 Identification & Authentication Failures

@never_cache
def change_password_view(request):   # ← no @login_required
    ...
    username = form.cleaned_data.get("username")   # ← username from POST body
    user = User.objects.get(username=username)
    if not user.check_password(current_password):
        ...
    else:
        user.set_password(new_password)
The endpoint is fully unauthenticated and accepts the target username from user-supplied POST data. Any unauthenticated request can attempt to change any user's password by supplying their username and current password.

Fix: Add @login_required, remove the username field from the form, and use request.user:

@never_cache
@login_required(login_url='login')
def change_password_view(request):
    user = request.user  # never trust username from POST
    if not user.check_password(current_password):
        ...
[C3] 
views.py
 — logout_view Has No @login_required and Silently Ignores GET
File: 
views.py
, function logout_view OWASP: A01 Broken Access Control

def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect("login")   # GET silently does nothing, redirects to login
A GET request silently redirects without logging out. A user who clicks a logout link (GET) believes they are logged out but is not. Add @require_POST to make the contract explicit and prevent confusion:

from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")
🟠 HIGH
[H1] 
views.py
 — Login Has No CAPTCHA; axes Only Locks by IP
File: 
views.py
, login_view; 
settings_base.py
 OWASP: A07 Identification & Authentication Failures

django-axes is configured with AXES_LOCKOUT_PARAMETERS = ['ip_address'] only. A distributed brute-force attack (many IPs, one target username) bypasses this entirely. There is no CAPTCHA on the login form (only on registration).

Fix:

# settings_base.py
AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]  # lock on IP+username combo
Add reCAPTCHA to the login form after N failures, or unconditionally.

[H2] 
views.py
 — _get_client_ip Trusts X-Forwarded-For Unconditionally
File: 
views.py
, _get_client_ip OWASP: A07 Identification & Authentication Failures

def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()   # ← client-controlled header
X-Forwarded-For is a client-controlled header. An attacker bypasses all IP-based rate limits (registration, email verification, resend) by rotating this header value:

X-Forwarded-For: 1.1.1.1  → attempt 1
X-Forwarded-For: 1.1.1.2  → attempt 2  (new "IP", counter reset)
Fix: Only trust X-Forwarded-For from known trusted proxies. Use django-ipware with TRUSTED_PROXY_LIST, or take the rightmost IP (set by your proxy, not the client):

# Rightmost non-private IP is set by your trusted proxy
ips = [ip.strip() for ip in x_forwarded.split(',')]
return ips[-1]  # set by your proxy, not spoofable by client
[H3] 
views.py
 — Login Reveals Unverified Account Status (Credential Oracle)
File: 
views.py
, login_view OWASP: A07 Identification & Authentication Failures

if is_unverified_user(username, password):   # checks username + password match
    messages.error(request, 'Your email address is not verified...')
is_unverified_user returns True only when username exists, is inactive, AND the password is correct. This distinct error message confirms to an attacker that both the username and password are valid — a credential oracle.

Fix: Use authenticate() first, then check is_active:

user = authenticate(request, username=username, password=password)
if user is not None:
    if not user.is_active:
        messages.error(request, 'Your email address is not verified...')
    else:
        login(request, user)
        return redirect("dashboard")
else:
    messages.error(request, "Invalid username or password")
[H4] 
settings_base.py
 — SOCIALACCOUNT_LOGIN_ON_GET = True (OAuth CSRF)
File: 
settings_base.py
 OWASP: A01 Broken Access Control / CSRF

SOCIALACCOUNT_LOGIN_ON_GET = True
Allows OAuth login to be initiated via a GET request. An attacker can embed <img src="/social/google/login/"> on any page and silently initiate an OAuth flow for the victim, potentially linking the attacker's Google account to the victim's FinTrack session.

Fix:

SOCIALACCOUNT_LOGIN_ON_GET = False
[H5] 
middleware.py
 — CSP Uses 'unsafe-inline' for Scripts (Defeats XSS Protection)
File: 
middleware.py
, ContentSecurityPolicyMiddleware OWASP: A03 Injection (XSS)

"script-src 'self' 'unsafe-inline' cdn.jsdelivr.net ..."
'unsafe-inline' completely defeats the XSS protection that CSP is designed to provide. Any injected <script> tag will execute.

Fix: Use nonces:

import secrets

def __call__(self, request):
    nonce = secrets.token_urlsafe(16)
    request.csp_nonce = nonce
    response = self.get_response(request)
    csp = f"script-src 'self' 'nonce-{nonce}' cdn.jsdelivr.net www.google.com www.gstatic.com recaptcha.google.com; ..."
    response['Content-Security-Policy'] = csp
Then use nonce="{{ request.csp_nonce }}" on all inline <script> tags.

[H6] 
upload.py
 — No File Size Limit on CSV Upload (DoS)
File: 
upload.py
, settings_upload OWASP: A04 Insecure Design

decoded = csv_file.read().decode("utf-8")
...
request.session['csv_data'] = decoded   # entire file stored in session, no size check
No size limit on the uploaded CSV. The entire file is read into memory and stored in the session. With DB-backed sessions (the fallback), this writes unbounded data to django_session. The import loop also calls Expense.objects.create() once per row — no bulk insert, no row cap.

Fix:

MAX_CSV_BYTES = 1 * 1024 * 1024  # 1MB
if csv_file.size > MAX_CSV_BYTES:
    error = "CSV too large. Maximum 1MB / ~10,000 rows."
else:
    decoded = csv_file.read().decode("utf-8")
    ...
    rows = list(reader)
    if len(rows) > 5000:
        error = "Too many rows. Maximum 5,000 per import."
    else:
        # use bulk_create instead of per-row create()
        Expense.objects.bulk_create(expenses_to_create, batch_size=500)
[H7] 
webhook.py
 — No Rate Limiting on Webhook Endpoint
File: 
webhook.py
, bank_webhook OWASP: A04 Insecure Design / DoS

@csrf_exempt
@require_POST
def bank_webhook(request):
    token = request.headers.get('X-Bank-Token', '')
    token_obj = WebhookToken.verify(token)   # DB lookup on every unauthenticated request
No rate limiting. An attacker with a valid token can flood the endpoint and create thousands of Expense records. Even without a valid token, every request triggers a SHA-256 hash + DB lookup.

Fix:

from django.core.cache import cache

def bank_webhook(request):
    ip = request.META.get('REMOTE_ADDR', '')
    rate_key = f'webhook_rate_{ip}'
    hits = cache.get(rate_key, 0)
    if hits > 60:
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    cache.set(rate_key, hits + 1, timeout=60)
    ...
[H8] 
profile.py
 — Avatar Upload: WebP Magic Bytes Check is Wrong
File: 
profile.py
, profile, avatar upload block OWASP: A04 Insecure Design / File Upload

allowed_signatures = [
    b'\xff\xd8\xff',
    b'\x89PNG\r\n\x1a\n',
    b'GIF87a', b'GIF89a',
    b'RIFF',               # ← matches ANY RIFF container: WAV, AVI, etc.
]
b'RIFF' matches WAV audio, AVI video, and any other RIFF-based format. A WAV file passes this check and gets stored as an "avatar".

Fix:

header = avatar_file.read(12)
avatar_file.seek(0)
is_jpeg = header[:3] == b'\xff\xd8\xff'
is_png  = header[:8] == b'\x89PNG\r\n\x1a\n'
is_gif  = header[:6] in (b'GIF87a', b'GIF89a')
is_webp = header[:4] == b'RIFF' and header[8:12] == b'WEBP'  # correct WebP check
if not (is_jpeg or is_png or is_gif or is_webp):
    messages.error(request, 'Invalid file type.')
    return redirect('profile')
[H9] 
profile.py
 — Email Change Without Verification or Uniqueness Check
File: 
profile.py
, profile, profile update block OWASP: A07 Identification & Authentication Failures

user.email = request.POST.get("email", "").strip()
user.save()
A user can change their email to any value — including an email already owned by another user — without verifying ownership of the new address. No uniqueness check is performed.

Fix:

new_email = request.POST.get("email", "").strip()
if new_email != user.email:
    if User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
        messages.error(request, 'That email address is already in use.')
        return redirect('profile')
    # Ideally: send verification to new_email before applying the change
    # Store as pending_email in UserProfile, apply only after verification
🟡 MEDIUM
[M1] 
settings_prod.py
 — Rate Limiting Broken Without Redis (Multi-Worker)
File: 
settings_prod.py
 OWASP: A07 Identification & Authentication Failures

# NOTE: LocMemCache is per-process — rate limiting in accounts/views.py
# will not be shared across multiple Gunicorn workers.
The code documents this itself. With 4 Gunicorn workers and a limit of 3 attempts, an attacker gets 12 attempts per hour per IP. REDIS_URL is optional, making this a silent misconfiguration in production.

Fix: Make Redis mandatory in production, or add a startup assertion:

if not os.environ.get('REDIS_URL'):
    raise RuntimeError('REDIS_URL must be set in production for reliable rate limiting.')
[M2] 
views.py
 — resend_verification Rate Limit Keyed on User ID, Not IP
File: 
views.py
, resend_verification OWASP: A07 Identification & Authentication Failures

cache_key = f'resend_verification_{user_check.id}'   # per-user, not per-IP
attempts = cache.get(cache_key, 0)
if attempts >= 3:
    ...
_send_verification_email(request, user, token_obj.token)
cache.set(cache_key, attempts + 1, timeout=3600)   # incremented AFTER send
Two issues:

Rate limit is per-user-ID, not per-IP — an attacker can trigger 3 emails per user from any number of IPs
Counter is incremented after the email is sent — if the send raises an exception, the counter is never incremented
Fix: Key on IP, increment before sending:

ip = _get_client_ip(request)
ip_key = f'resend_ip_{ip}'
ip_attempts = cache.get(ip_key, 0)
if ip_attempts >= 5:
    messages.info(request, 'Too many attempts. Try again later.')
    return redirect('login')
cache.set(ip_key, ip_attempts + 1, timeout=3600)  # increment first
_send_verification_email(...)
[M3] 
webhook.py
 — date Field Not Validated (Arbitrary Past/Future Dates)
File: 
webhook.py
, bank_webhook OWASP: A03 Injection / A04 Insecure Design

txn_date = data.get('date', str(date.today()))
expense = Expense.objects.create(..., date=txn_date, ...)
No date validation. An attacker with a valid token can create expenses with "date": "1900-01-01" or "date": "2099-12-31", corrupting the user's financial history. On PostgreSQL, an invalid date string raises DataError (unhandled → 500).

Fix:

from datetime import datetime, date as date_type
date_str = data.get('date', str(date_type.today()))
try:
    txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    if txn_date > date_type.today():
        return JsonResponse({'error': 'Date cannot be in the future'}, status=400)
except ValueError:
    return JsonResponse({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)
[M4] 
settings_base.py
 — SESSION_COOKIE_SAMESITE and SESSION_COOKIE_AGE Not Set
File: 
settings_prod.py
 OWASP: A07 Identification & Authentication Failures

Django defaults: SESSION_COOKIE_SAMESITE = 'Lax', SESSION_COOKIE_AGE = 1209600 (2 weeks). For a financial app, 2-week sessions are too long and Lax is weaker than needed.

Fix:

# settings_prod.py
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600          # 1 hour
SESSION_SAVE_EVERY_REQUEST = True  # slide expiry on activity
[M5] 
views.py
 — _send_verification_email Logs Full Email Addresses (PII in Logs)
File: 
views.py
, _send_verification_email OWASP: A09 Security Logging and Monitoring Failures

logger.info(f"Attempting to send email to {user.email}")
logger.info(f"Email sent successfully to {user.email} via SendGrid API")
logger.info(f"Email sent successfully to {user.email} via SMTP")
Full email addresses logged at INFO level. Logs are often shipped to third-party services (Datadog, Papertrail) and retained long-term. Email addresses are PII.

Fix:

masked = user.email[:2] + '***@' + user.email.split('@')[1]
logger.info(f"Email sent to {masked} (user_id={user.pk})")
[M6] 
settings_base.py
 — ACCOUNT_EMAIL_VERIFICATION = 'none' for allauth
File: 
settings_base.py
 OWASP: A07 Identification & Authentication Failures

ACCOUNT_EMAIL_VERIFICATION = 'none'
allauth's own email verification is disabled. Any allauth-managed flows (password reset, email change via allauth social flows) bypass the custom email verification entirely.

Fix: Either use allauth's built-in 'mandatory' verification and remove the custom implementation, or audit every allauth URL to ensure none bypass your custom verification gate.

[M7] 
export.py
 — No Rate Limiting on Data Export
File: 
export.py
, export_data OWASP: A04 Insecure Design

The export endpoint streams all of a user's financial records as CSV with no rate limiting. A compromised session or malicious script can repeatedly dump all financial data or cause excessive DB load.

Fix: Add a cache-based rate limit (e.g., max 10 exports per hour per user).

[M8] 
views.py
 — change_password_view Doesn't Invalidate Other Sessions
File: 
views.py
, change_password_view OWASP: A07 Identification & Authentication Failures

user.set_password(new_password)
user.save()
return redirect("login")
After a password change, other active sessions (other devices) remain valid. Django provides update_session_auth_hash() for this, but since this view doesn't require login, the broader fix is to add @login_required (see C2) and then call:

from django.contrib.auth import update_session_auth_hash
update_session_auth_hash(request, user)  # keeps current session, invalidates others
[M9] 
webhook.py
 — merchant Field Not Length-Validated
File: 
webhook.py
, bank_webhook OWASP: A03 Injection

title=str(data['merchant']).strip(),
Expense.title has max_length=200. No explicit length check in the webhook handler. On PostgreSQL this raises an unhandled DataError (→ 500). On SQLite it silently truncates.

Fix:

merchant = str(data['merchant']).strip()
if not merchant or len(merchant) > 200:
    return JsonResponse({'error': 'Invalid merchant name'}, status=400)
🟢 LOW / INFORMATIONAL
[L1] 
urls.py
 — Unauthenticated Access to Media Files (Avatars)
File: 
urls.py
 OWASP: A01 Broken Access Control

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
In production without S3, avatar files at /media/avatars/<filename> are publicly accessible without authentication. Any URL-guessable avatar can be accessed by anyone.

Fix: Serve media through an authenticated view, or use nginx X-Accel-Redirect with an auth check, or use S3 with pre-signed URLs.

[L2] 
upload.py
 — CSV Preview Data Persists in Session Indefinitely
File: 
upload.py
, settings_upload OWASP: A04 Insecure Design

request.session['csv_data'] = decoded
If the user previews a CSV and navigates away without importing, the full CSV content stays in the session for up to 2 weeks (Django default). Financial data sitting in the session store longer than necessary.

Fix: Set a short expiry or use a temporary file reference with a cleanup task.

[L3] requirements.txt — Two Dependencies Use >= (Not Pinned)
File: requirements.txt OWASP: A06 Vulnerable and Outdated Components

psycopg2-binary>=2.9.10
requests>=2.32.0
Open version ranges can pull in future breaking changes or vulnerabilities automatically. Pin all dependencies to exact versions in production.

[L4] 
settings_base.py
 — AXES_COOLOFF_TIME = 0.25 (15 min) Too Short for Financial App
File: 
settings_base.py
 OWASP: A07 Identification & Authentication Failures

15-minute lockout is short for a financial application. Consider progressive lockout: 15 min → 1 hour → 24 hours.

[L5] 
models.py
 — WebhookToken.verify Has Redundant hmac.compare_digest
File: 
models.py
, WebhookToken.verify OWASP: A02 Cryptographic Failures (informational)

obj = cls.objects.get(token_hash=token_hash)   # already proves equality
if hmac.compare_digest(obj.token_hash, token_hash):  # always True here
    return obj
The hmac.compare_digest after a successful .get() is dead code — the hashes are already proven equal by the DB lookup. The timing-attack protection is correctly provided by hashing the input before the lookup. No security impact, just misleading code.

[L6] 
middleware.py
 — CSP Missing upgrade-insecure-requests in Production
File: 
middleware.py
 OWASP: A05 Security Misconfiguration

The same CSP is applied in dev and prod. Production should add upgrade-insecure-requests to force mixed content to HTTPS. Consider environment-aware CSP in the middleware.

Prioritized Fix Order
Priority	ID	Issue	Effort
1	C1	Rotate all secrets in .env, add to .gitignore, purge from git history	Low
2	C2	Add @login_required to change_password_view, remove username from form	Low
3	C3	Add @require_POST to logout_view	Low
4	H3	Fix login credential oracle (use authenticate() then check is_active)	Low
5	H4	Set SOCIALACCOUNT_LOGIN_ON_GET = False	Low
6	H2	Fix _get_client_ip to not blindly trust X-Forwarded-For	Medium
7	H5	Replace 'unsafe-inline' in CSP with nonces	Medium
8	H8	Fix WebP magic byte check (RIFF + WEBP at offset 8)	Low
9	H9	Add email uniqueness check + verification flow on email change	Medium
10	H6	Add size limit + row cap to CSV upload; use bulk_create	Low
11	H7	Add rate limiting to webhook endpoint	Low
12	M1	Make Redis mandatory in production or add startup assertion	Low
13	M3	Validate date field in webhook payload	Low
14	M4	Set SESSION_COOKIE_SAMESITE = 'Strict' and SESSION_COOKIE_AGE = 3600	Low
15	M5	Mask email addresses in logs