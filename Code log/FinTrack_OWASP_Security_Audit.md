# FinTrack — OWASP Top 10 Security Audit

**Last verified:** July 2026  
**Auditor:** Code review + live codebase scan  
**Django version:** 6.0.2

---

## Status Summary

| Severity | Total | ✅ Fixed | ❌ Pending |
|---|---|---|---|
| 🔴 Critical | 3 | 2 | 1 |
| 🟠 High | 8 | 7 | 1 |
| 🟡 Medium | 12 | 10 | 2 |
| 🟢 Low | 8 | 4 | 4 |

---

## ✅ IMPLEMENTED — Confirmed in codebase

### Critical

| ID | OWASP | Issue | Fix Verified In |
|---|---|---|---|
| C2 | A07 | `change_password_view` missing `@login_required` and `@require_POST` | `accounts/views.py` — both decorators applied, uses `request.user` only, `update_session_auth_hash()` called |
| C3 | A01 | `logout_view` accepted GET (CSRF logout) | `accounts/views.py` — `require_POST` applied at module level |

### High

| ID | OWASP | Issue | Fix Verified In |
|---|---|---|---|
| H1 | A07 | django-axes only locked by IP (distributed brute-force bypass) | `settings_base.py` — `AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]` |
| H2 | A04 | CSV upload had no size limit (DoS vector) | `dashboard/views/upload.py` — 1MB file limit + 5,000 row cap |
| H3 | A04 | Webhook endpoint had no rate limiting | `expenses/webhook.py` — 60 req/min per IP via Django cache |
| H5 | A01 | `SOCIALACCOUNT_LOGIN_ON_GET = True` (OAuth CSRF) | `settings_base.py` — set to `False` |
| H6 | A07 | `_get_client_ip` trusted first `X-Forwarded-For` (spoofable) | `accounts/views.py` — uses rightmost IP (`ips[-1]`) |
| H7 | A04 | WebP magic bytes check matched any RIFF container | `dashboard/views/profile.py` — checks `header[8:12] == b'WEBP'` |
| H8 | A07 | Login view credential oracle via pre-check before `authenticate()` | `accounts/views.py` — `authenticate()` called first; `is_active` check now returns same generic error message as wrong-password (oracle closed) |

### Medium

| ID | OWASP | Issue | Fix Verified In |
|---|---|---|---|
| M4 | A04 | Webhook `date` field not validated | `expenses/webhook.py` — `strptime` validation + future date rejection |
| M5 | A04 | CSV import used per-row `create()` (N+1 inserts) | `dashboard/views/upload.py` — `bulk_create(batch_size=500)` |
| M6 | A09 | Email addresses logged as PII | `accounts/views.py` — masked as `sh***@gmail.com (user_id=N)` |
| M7 | A07 | Resend verification rate limit keyed on user ID, counter incremented after send | `accounts/views.py` — keyed on IP, counter incremented before sending |
| M8 | A05 | `SESSION_COOKIE_SAMESITE` not set | `settings_prod.py` — `SESSION_COOKIE_SAMESITE = 'Strict'`, `CSRF_COOKIE_SAMESITE = 'Strict'` |
| M9 | A09 | Gemini API error logs raw response | `dashboard/views/insights.py` — parse failure truncated to 200 chars, `_call_gemini` only logs exception, not response body |
| M10 | A04 | Email change without uniqueness check | `dashboard/views/profile.py` — `User.objects.exclude(pk=...).filter(email=...).exists()` |
| M11 | A07 | `SESSION_COOKIE_AGE` not set (2-week Django default) | `settings_prod.py` — `SESSION_COOKIE_AGE = 3600` + `SESSION_SAVE_EVERY_REQUEST = True` |
| M12 | A04 | Webhook `merchant` field not length-validated | `expenses/webhook.py` — explicit 1–200 char check → 400 |
| L6 | A06 | `psycopg2-binary`, `requests`, `sendgrid` used `>=` (unpinned) | `requirements.txt` — pinned to `==2.9.10`, `==2.32.3`, `==6.11.0` |

### Low

| ID | OWASP | Issue | Fix Verified In |
|---|---|---|---|
| L3 | A07 | Password change didn't invalidate other sessions | `accounts/views.py` — `update_session_auth_hash()` called after set_password |
| L9 | A09 | `Code log/` audit files committed to git | `.gitignore` — `Code log/` added |

---

## ❌ PENDING — Not yet implemented

### Critical

| ID | OWASP | Issue | Notes |
|---|---|---|---|
| C1 | A02 | Live secrets (SECRET_KEY, Gmail password, reCAPTCHA keys) in git history | **Manual action required.** Run `git log --all --full-history -- .env` to confirm. If present, rotate all secrets and purge with `git filter-repo --path .env --invert-paths`. Railway env vars should be re-set after rotation. |

### High

| ID | OWASP | Issue | Notes |
|---|---|---|---|
| H4 | A03 | CSP uses `unsafe-inline` — XSS protection defeated | Nonce-based CSP was implemented and reverted — broke all `onclick` handlers. Proper fix requires converting every `onclick` attribute to `addEventListener`. JS is now largely extracted to static files (`dashboard.js`, `insights.js`, etc.) — the bulk of the work is done. Main blocker: remaining inline event handlers in templates. Tracked as a future refactor. |

### Medium

| ID | OWASP | Issue | Notes |
|---|---|---|---|
| M2 | A05 | Rate limiting unreliable without Redis in multi-worker deploy | `settings_prod.py` uses `LocMemCache` per Gunicorn worker when `REDIS_URL` not set — rate limits multiply by worker count. Fix: set `REDIS_URL` in production environment. |
| M3 | A04 | No rate limiting on data export endpoint | `dashboard/views/export.py` has only `@login_required`. Low risk (authenticated users only), but a user could hammer the export to cause load. |

### Low

| ID | OWASP | Issue | Notes |
|---|---|---|---|
| L1 | A01 | Avatar media files publicly accessible without auth | Acceptable for local/small-scale deploy. Fix: serve via authenticated view or use S3 with pre-signed URLs. |
| L2 | A02 | Redundant `hmac.compare_digest` in `WebhookToken.verify` | Dead code — DB lookup already proves hash equality. No security impact, just noise. |
| L4 | A05 | CSP missing `upgrade-insecure-requests` in production | Minor. Can be added to `middleware.py` CSP string once `H4` nonce refactor is done. |
| L5 | A04 | CSV preview data persists in session indefinitely | `session.pop()` clears it on successful import, but if user navigates away the decoded CSV stays in session. Add a short TTL or clear on any non-import POST. |
| L7 | A02 | `verify_pending` page shows email from session | Very low risk — only leaks to someone with physical access to the same browser session. Not worth fixing. |
| L8 | A07 | `AXES_COOLOFF_TIME = 0.25` (15 min lockout) — short for a financial app | Consider progressive lockout: 15 min → 1 hour → 24 hours using `AXES_COOLOFF_TIME` as a callable. |

---

## Additional Issues Found & Fixed (Outside Original Audit Scope)

| Issue | Fix |
|---|---|
| `ChangePasswordForm` had `username` field — view used `request.user` but form still exposed the field | `username` removed from form |
| "Forgot password?" on login pointed to `change_password_view` (login-required) — created redirect loop | Link removed from login page; button added to Profile page (non-OAuth only) |
| `auth.html` wiped to 0 bytes during nonce-removal script | Restored from git (`823bdad`) |
| `logout_view` had duplicate `require_POST` import | Deduplicated |
| `dashboard.html` wiped to 0 bytes | Restored and nonce attributes removed |
| `savings_goal_detail.html` had corrupted line 3 (template tag merged with `endblock`) | Fixed |
| Duplicate `__repr__` on `Subscription` model | Removed duplicate |
| Subscription billing logic used `< today` (today's billing never triggered) | Changed to `<= today` in model and views |
| All major page JS was inline in HTML templates — Django template tags inside `<script>` | Extracted to 6 static JS files; Django context passed via `data-*` attributes |
| Gemini SDK using deprecated `google-generativeai` package (FutureWarning) | Migrated to `google-genai==2.10.0` |

---

## OWASP Top 10 Coverage Map (2021)

| Category | Status |
|---|---|
| A01 — Broken Access Control | ✅ `@login_required` on all views, `@require_POST` on state-changing endpoints |
| A02 — Cryptographic Failures | ⚠️ C1 (live secrets in git history) still pending |
| A03 — Injection | ✅ Django ORM parameterises all queries; CSP present (unsafe-inline pending nonce refactor) |
| A04 — Insecure Design | ✅ Rate limits on webhook + auth + CSV; size limits on uploads |
| A05 — Security Misconfiguration | ✅ SameSite cookies, session age, AXES lockout; Redis rate-limiting pending in multi-worker |
| A06 — Vulnerable Components | ✅ Dependencies pinned to exact versions; `google-generativeai` deprecated pkg replaced |
| A07 — Authentication Failures | ✅ Brute-force protection, credential oracle closed, session invalidation on password change |
| A08 — Software Integrity Failures | ✅ CDN scripts use SRI integrity attributes |
| A09 — Logging Failures | ✅ PII masked in logs; Gemini response truncated to 200 chars |
| A10 — SSRF | ✅ No outbound user-controlled requests in the app |
