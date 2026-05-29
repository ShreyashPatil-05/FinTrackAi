# FinTrack — Full OWASP Top 10 Security Audit

---

## ✅ IMPLEMENTED FIXES

All items below have been confirmed in the codebase as of May 2026.

### Critical

| ID | Issue | Fix Applied |
|---|---|---|
| C2 | `change_password_view` missing `@login_required` | Added `@login_required`, removed `username` from form, uses `request.user` only. `update_session_auth_hash()` called to keep current session valid and invalidate others. |
| C3 | `logout_view` accepts GET silently | `require_POST` applied — GET requests now return 405. |

### High

| ID | Issue | Fix Applied |
|---|---|---|
| H1 | axes only locks by IP (distributed brute-force bypass) | `AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]` — locks on IP+username combo. |
| H2 | CSV upload no size limit (DoS) | 1MB file size limit + 5,000 row cap added in `upload.py`. |
| H3 | Webhook endpoint no rate limiting | 60 requests/minute per IP using cache-based rate limiter in `webhook.py`. |
| H5 | `SOCIALACCOUNT_LOGIN_ON_GET = True` (OAuth CSRF) | Set to `False` in `settings_base.py`. |
| H6 | `_get_client_ip` trusts first X-Forwarded-For (spoofable) | Uses rightmost IP (`ips[-1]`) — set by trusted proxy, not client-controlled. |
| H7 | WebP magic bytes check wrong (matched any RIFF container) | Fixed to check `header[8:12] == b'WEBP'` in `profile.py`. |
| H8 | Login credential oracle via `is_unverified_user` pre-check | `authenticate()` called first, then `user.is_active` checked — no pre-check that leaks valid credentials. |

### Medium

| ID | Issue | Fix Applied |
|---|---|---|
| M4 | Webhook date field not validated | `strptime` validation + future date rejection in `webhook.py`. |
| M5 | CSV import uses per-row `create()` (N+1 inserts) | Replaced with `bulk_create(batch_size=500)` in `upload.py`. |
| M6 | Email addresses logged as PII | Masked as `sh***@gmail.com (user_id=N)` in `_send_verification_email`. |
| M7 | Resend verification rate limit keyed on user ID, not IP; counter incremented after send | Keyed on IP (`resend_ip_{ip}`), counter incremented before sending. |
| M8 | Session cookie `SameSite` not set | `SESSION_COOKIE_SAMESITE = 'Strict'`, `CSRF_COOKIE_SAMESITE = 'Strict'` in `settings_prod.py`. |
| M10 | Email change without uniqueness check | Uniqueness check added in `profile.py` — rejects email already in use. |
| M11 | `SESSION_COOKIE_AGE` not set (2-week default) | `SESSION_COOKIE_AGE = 3600` (1 hour) + `SESSION_SAVE_EVERY_REQUEST = True` in `settings_prod.py`. |
| M12 | Webhook `merchant` field not length-validated | Explicit 1–200 char check returns 400 on violation. |

### Low / Informational

| ID | Issue | Fix Applied |
|---|---|---|
| L3 | Password change doesn't invalidate other sessions | `update_session_auth_hash(request, user)` called after password change. |

---

## ❌ NOT IMPLEMENTED / PENDING

| ID | Severity | Issue | Notes |
|---|---|---|---|
| C1 | 🔴 Critical | `.env` secrets in git history | **Manual action required** — rotate Gmail app password + Django `SECRET_KEY` on Railway. Run `git log --all --full-history -- .env` to check history. If present, purge with `git filter-repo --path .env --invert-paths`. |
| H4 | 🟠 High | CSP uses `unsafe-inline` (XSS protection defeated) | Nonce-based CSP was implemented but reverted — it broke all `onclick` handlers across templates. Proper fix requires converting every `onclick` attribute to `addEventListener` calls. Tracked as future refactor. |
| M1 | 🟡 Medium | `ACCOUNT_EMAIL_VERIFICATION = 'none'` for allauth | Intentional — custom email verification is used instead of allauth's built-in flow. |
| M2 | 🟡 Medium | Rate limiting broken without Redis (multi-worker) | Documented in `settings_prod.py`. Set `REDIS_URL` on Railway to fix. Without it, each Gunicorn worker has its own cache — rate limits multiply by worker count. |
| M3 | 🟡 Medium | No rate limiting on data export endpoint | Not implemented. Low risk — authenticated users only. |
| M9 | 🟡 Medium | Gemini API error logs raw response (200 chars) | Not fixed. Low risk — only triggered in error path. |
| L1 | 🟢 Low | Media files (avatars) publicly accessible without auth | Acceptable without S3. Fix: serve via authenticated view or use S3 with pre-signed URLs. |
| L2 | 🟢 Low | Redundant `hmac.compare_digest` in `WebhookToken.verify` | Dead code — no security impact. The hash comparison via `.get()` already proves equality. |
| L4 | 🟢 Low | CSP missing `upgrade-insecure-requests` in production | Minor. Can be added to middleware when CSP is refactored. |
| L5 | 🟢 Low | CSV preview data persists in session indefinitely | Minor. Data cleared on import via `session.pop()`, but stays if user navigates away. |
| L6 | 🟢 Low | `psycopg2-binary` and `requests` use `>=` (unpinned) | Minor. Pin to exact versions for reproducible production builds. |
| L7 | 🟢 Low | `verify_pending` leaks email from session | Very low risk. View is unauthenticated — email visible to anyone with the session cookie on a shared machine. |
| L8 | 🟢 Low | `AXES_COOLOFF_TIME = 0.25` (15 min lockout) | Short for a financial app. Consider progressive lockout: 15 min → 1 hour → 24 hours. |

---

## Additional Issues Found & Fixed (Not in Original Audit)

| Issue | Fix Applied |
|---|---|
| `ChangePasswordForm` had `username` field — view now uses `request.user` | `username` field removed from `ChangePasswordForm`. |
| "Forgot password?" link on login page pointed to `change_password_view` which requires login — created redirect loop | Link removed from login page. "Change password" button added to Profile page (shown only for non-OAuth users). |
| `auth.html` wiped to 0 bytes during nonce-removal script | Restored from git history (`823bdad`). |
| `logout_view` had duplicate `require_POST` import | Deduplicated import line. |
| `Code log/` folder being committed to git | Added `Code log/` to `.gitignore`. |

---

## Original Audit Findings (Full Detail)

> The complete original audit text is preserved below for reference.

---

### 🔴 CRITICAL

**[C1] `.env` — Live Secrets Committed to Repository**
OWASP: A02 Cryptographic Failures / A07 Authentication Failures

```
SECRET_KEY=^lcngywzqblm#2^l8j$pi111)-2zd*)05f1*#&030d_wvxjei(
EMAIL_HOST_USER=shreyashpatil655@gmail.com
EMAIL_HOST_PASSWORD=jcvtpqwojimtfswr        ← live Gmail App Password
RECAPTCHA_SITE_KEY=6LfgE8QsAAAAAOpuZNBG3x08ICllYqKpJfqT_fhG
RECAPTCHA_SECRET_KEY=6LfgE8QsAAAAALXtgIYBQAh3G9ssPET-SstxBKzR
BANK_WEBHOOK_SECRET=fintrack-mock-bank-secret-2026
```

**[C2] `views.py` — `change_password_view` Has No `@login_required`**
OWASP: A07 — ✅ FIXED

**[C3] `views.py` — `logout_view` Silently Ignores GET**
OWASP: A01 — ✅ FIXED

---

### 🟠 HIGH

**[H1] Login axes only locks by IP**
OWASP: A07 — ✅ FIXED

**[H2] CSV no size limit**
OWASP: A04 — ✅ FIXED

**[H3] Webhook no rate limiting**
OWASP: A04 — ✅ FIXED

**[H4] CSP uses `unsafe-inline`**
OWASP: A03 — ❌ PENDING (nonce refactor required)

**[H5] `SOCIALACCOUNT_LOGIN_ON_GET = True`**
OWASP: A01 — ✅ FIXED

**[H6] `_get_client_ip` trusts first X-Forwarded-For**
OWASP: A07 — ✅ FIXED

**[H7] WebP magic bytes wrong**
OWASP: A04 — ✅ FIXED

**[H8] Login credential oracle**
OWASP: A07 — ✅ FIXED

---

### 🟡 MEDIUM

**[M1] `ACCOUNT_EMAIL_VERIFICATION = 'none'`** — Intentional, custom flow used

**[M2] Rate limiting broken without Redis** — ❌ PENDING (set `REDIS_URL`)

**[M3] No rate limiting on export** — ❌ PENDING

**[M4] Webhook date not validated** — ✅ FIXED

**[M5] CSV per-row inserts** — ✅ FIXED (`bulk_create`)

**[M6] Email PII in logs** — ✅ FIXED (masked)

**[M7] Resend rate limit by user ID** — ✅ FIXED (by IP, pre-increment)

**[M8] Session cookie SameSite not set** — ✅ FIXED

**[M9] Gemini logs raw response** — ❌ PENDING (low risk)

**[M10] Email change no uniqueness check** — ✅ FIXED

**[M11] SESSION_COOKIE_AGE not set** — ✅ FIXED (1 hour)

**[M12] Webhook merchant not length-validated** — ✅ FIXED

---

### 🟢 LOW / INFORMATIONAL

**[L1]** Media files publicly accessible — ❌ PENDING

**[L2]** Redundant `hmac.compare_digest` — dead code, no impact

**[L3]** Password change doesn't invalidate other sessions — ✅ FIXED

**[L4]** CSP missing `upgrade-insecure-requests` — ❌ PENDING

**[L5]** CSV preview in session indefinitely — ❌ PENDING

**[L6]** Unpinned dependencies — ❌ PENDING

**[L7]** `verify_pending` leaks email — low risk, not fixed

**[L8]** `AXES_COOLOFF_TIME` 15 min — ❌ PENDING
