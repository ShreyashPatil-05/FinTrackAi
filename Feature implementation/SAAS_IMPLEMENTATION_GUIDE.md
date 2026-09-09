# FinTrack — SaaS Freemium Implementation Guide (v3)

**Last reviewed:** September 8, 2026
**Status:** Fully implemented. Pending production credentials only.

---

## Implementation Progress

| Phase | Description | Status |
|---|---|---|
| Phase 1 | UserProfile plan fields + Payment model + migration | ✅ Complete |
| Phase 2 | `plan_service.py` — limit checks | ✅ Complete |
| Phase 3 | `@plan_required` decorator | ✅ Complete |
| Phase 4 | Razorpay payment integration | ✅ Complete |
| Phase 5 | Plan expiry management command | ✅ Complete |
| Phase 6 | Email notifications | ✅ Complete |
| Phase 7 | Pricing page UI | ✅ Complete |
| Phase 8 | Admin plan controls | ✅ Complete |

**All phases are implemented.** The only remaining steps are:
1. Add production credentials to `.env` (see Environment Variables below)
2. Configure the webhook URL in the Razorpay Dashboard
3. Run `pip install razorpay==1.4.1` if not yet installed
4. Schedule `python manage.py expire_plans` as a daily cron/Railway job

---

## Tier Comparison

| Feature | Free | Pro |
|---|---|---|
| Expenses | 50 / month | Unlimited |
| Income entries | 20 / month | Unlimited |
| Savings goals | 2 total | Unlimited |
| Subscriptions | 3 total | Unlimited |
| Budget categories | 3 total | Unlimited |
| CSV import | ❌ Locked | ✅ |
| Data export | ❌ Locked | ✅ |
| AI Insights (Gemini) | ❌ Blurred preview | ✅ Full |
| Webhook (bank sim) | ❌ Locked | ✅ |

## Pricing Plans

| Plan | Price | Best For |
|---|---|---|
| Free | ₹0 / forever | Getting started |
| Monthly | ₹49 / month | Flexibility |
| Yearly | ₹499 / year | Best value (~30% off monthly) |

---

## Phase 1 — Model Changes ✅

### Implemented in `dashboard/models.py`

`UserProfile` extended with:
- `plan` — CharField: `free` / `monthly` / `yearly` (default: `free`)
- `plan_expires_at` — DateTimeField, nullable
- `is_pro()` — checks plan and expiry

`Payment` model added:
- `user` (FK), `plan`, `amount`, `razorpay_order_id` (unique), `razorpay_payment_id`, `razorpay_signature`, `status`, `created_at`, `updated_at`
- Status choices: `pending` / `captured` / `failed` / `refunded`

### Migration

`dashboard/migrations/0016_saas_plan_payment_model.py` — applied ✅

---

## Phase 2 — Plan Service ✅

**File:** `dashboard/services/plan_service.py`

Implemented:
- `is_pro(user)` — safe, never raises
- `check_limit(user, resource)` → `(allowed: bool, message: str)`
- `get_usage(user)` → dict with current counts and limits

Resources enforced:
- `expense` — 50/month free limit
- `income` — 20/month free limit
- `savings_goal` — 2 total free limit
- `subscription` — 3 total free limit
- `budget_category` — 3 total free limit
- `csv_import`, `export`, `webhook`, `ai_insights` — Pro-only locked features

---

## Phase 3 — `@plan_required` Decorator ✅

**File:** `dashboard/decorators.py`

Implemented `plan_required(resource)` decorator factory.
Applied to views:
- `export_data` → `@plan_required('export')`
- `settings_upload` → `@plan_required('csv_import')`
- `insights_view` → checked via `check_limit` inside AJAX branch
- `add_expense` → `check_limit` inside POST block
- `income_add` → `check_limit` inside POST block
- `subscription_add` → `check_limit` inside POST block
- `savings_goal_add` → `check_limit` inside POST block

All limit violations redirect to `/pricing/` with a user-facing error message.

---

## Phase 4 — Razorpay Payment Integration ✅

**File:** `dashboard/views/payment.py`

### What is implemented

#### `PLAN_CONFIG` (single source of truth)
```python
PLAN_CONFIG = {
    'monthly': {'amount': 4900,  'days': 31,  'label': '₹49 / month'},
    'yearly':  {'amount': 49900, 'days': 365, 'label': '₹499 / year'},
}
```

#### `_get_razorpay_client()` helper
- Reads `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` from environment
- Raises `ValueError` if keys are missing (never hardcoded)

#### `_activate_pro(user, plan)` helper
- Sets `profile.plan` and `profile.plan_expires_at`
- Called from both `verify_payment` and `_handle_payment_captured`

#### `create_order` view — `POST /payment/create-order/`
- Requires `@login_required` + `@require_POST`
- Creates Razorpay order via API
- Saves `Payment(status='pending')` record for audit trail
- Returns `{order_id, amount, plan, label}` JSON

#### `verify_payment` view — `POST /payment/verify/`
- Requires `@login_required` + `@require_POST`
- Verifies HMAC-SHA256 signature via `client.utility.verify_payment_signature()`
- **Frontend is never trusted** — signature failure marks payment as `failed` and rejects
- Idempotent — skips activation if payment already `captured` (webhook may arrive first)
- Updates `Payment` to `captured`, calls `_activate_pro`, sends confirmation email
- Failed signature → `Payment.status = 'failed'`, redirects to `/pricing/`

#### `razorpay_webhook` view — `POST /payment/webhook/`
- `@csrf_exempt` — server-to-server, no browser session
- Verifies `X-Razorpay-Signature` HMAC-SHA256 using `RAZORPAY_WEBHOOK_SECRET`
- Rejects (400) any request with invalid or missing signature
- Returns 200 for unknown events (prevents Razorpay retries)
- **Handles `payment.captured`:**
  - Idempotent — skips if already `captured`
  - Updates `Payment` record, calls `_activate_pro`, sends email
  - Handles case where webhook arrives before frontend (logs warning, safe)
- **Handles `payment.failed`:**
  - Marks matching `pending` Payment as `failed`

### URLs registered in `dashboard/urls.py`
```
/pricing/                 → pricing
/payment/create-order/    → create_order
/payment/verify/          → verify_payment
/payment/webhook/         → razorpay_webhook
```

### Frontend (`dashboard/templates/dashboard/pricing.html` + `static/js/pricing.js`)
- Monthly/Yearly toggle
- `startPayment()` calls `create_order` via fetch, opens Razorpay checkout
- On success, submits hidden form to `verify_payment`
- Upgrade button re-enabled on modal dismiss
- Shows "Payment not configured" if `RAZORPAY_KEY_ID` is not set
- Payment history table shown to Pro users

### Requirements
`razorpay==1.4.1` added to `requirements.txt` ✅

---

## Phase 5 — Plan Expiry Management Command ✅

**File:** `dashboard/management/commands/expire_plans.py`

- Expires overdue Pro plans → sets to `free`, sends expiry email
- Sends 7-day renewal reminder emails
- `--dry-run` flag for safe testing
- Schedule as daily cron:

```bash
# Railway cron (recommended)
0 0 * * * python manage.py expire_plans --settings=fintrack.settings_prod

# Or add to Railway cron jobs in dashboard
```

---

## Phase 6 — Email Notifications ✅

**File:** `dashboard/services/email_service.py`

All emails use the same SendGrid/SMTP background thread pattern as `accounts/views.py`:

| Function | Trigger | Content |
|---|---|---|
| `send_payment_success_email(user, payment)` | After `verify_payment` or `payment.captured` webhook | Plan, amount, expiry date, features unlocked |
| `send_expiry_reminder_email(user)` | `expire_plans` command (7 days before expiry) | Days left, renewal link |
| `send_plan_expired_email(user)` | `expire_plans` command (on expiry) | Plan ended, renewal CTA |

---

## Phase 7 — Pricing Page UI ✅

**File:** `dashboard/templates/dashboard/pricing.html`

- Authenticated — requires `@login_required`
- Usage meters (free users) — shows current vs limit for each resource
- Plan cards — Free and Pro with feature comparison
- Monthly/Yearly toggle with price update
- Razorpay checkout button (hidden if `RAZORPAY_KEY_ID` not set)
- Payment history table (Pro users only)
- Hidden form for `verify_payment` POST submission

---

## Phase 8 — Admin Controls ✅

**File:** `dashboard/admin.py`

- `FinTrackUserAdmin` — `UserProfileInline` shows plan/expiry inline on User
- Actions: `grant_monthly_pro`, `grant_yearly_pro`, `revoke_pro`
- `PaymentAdmin` — list/filter/search payments, all Razorpay IDs are readonly
- `list_display` on User admin includes `get_plan` column

---

## Environment Variables Required

Add to `.env` (development) and Railway environment variables (production):

```bash
# Required to activate Razorpay payments
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx       # use rzp_live_... in production
RAZORPAY_KEY_SECRET=your_key_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here

# Already configured
GEMINI_API_KEY=AIza...                       # enables AI insights for Pro users
```

**Never commit these to git.** `.env` is in `.gitignore`. ✅

---

## Razorpay Dashboard Configuration (Manual Steps)

After deploying to production:

1. **Create a webhook** in Razorpay Dashboard → Settings → Webhooks:
   - URL: `https://your-domain.com/payment/webhook/`
   - Events to subscribe: `payment.captured`, `payment.failed`
   - Secret: copy the value you set as `RAZORPAY_WEBHOOK_SECRET`

2. **Switch from test to live keys** when ready for real payments:
   - Replace `rzp_test_...` with `rzp_live_...` in `RAZORPAY_KEY_ID`
   - Replace the test secret with the live secret in `RAZORPAY_KEY_SECRET`

3. **Test the webhook** using Razorpay's webhook test tool before going live.

---

## Test Cards (Razorpay Test Mode)

```
Card:   4111 1111 1111 1111
Expiry: Any future date
CVV:    Any 3 digits
OTP:    1234
UPI:    success@razorpay    (success)
        failure@razorpay    (failure)
```

---

## Complete Payment Flow

```
User clicks "Upgrade to Pro"
    │
    ▼
startPayment() [pricing.js]
    │  POST /payment/create-order/
    ▼
create_order [payment.py]
    │  Creates Payment(status='pending') in DB
    │  Returns {order_id, amount} JSON
    ▼
Razorpay Checkout opens [browser]
    │
    ├─ User cancels → modal closes, button re-enabled
    │
    └─ User pays
           │
           ├─ [Frontend path] Razorpay calls handler()
           │       POST /payment/verify/
           │       verify_payment() verifies HMAC signature
           │       Updates Payment(status='captured')
           │       Calls _activate_pro(user, plan)
           │       Sends confirmation email
           │       Redirects to /dashboard/
           │
           └─ [Webhook path — server to server]
                   POST /payment/webhook/
                   razorpay_webhook() verifies X-Razorpay-Signature
                   _handle_payment_captured() idempotent activation
                   (safe even if verify_payment already ran)
```

---

## Remaining Work

| Item | Type | Notes |
|---|---|---|
| Add `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` to `.env` | Config | Required to activate |
| Configure webhook URL in Razorpay Dashboard | Config | Required for server-side payment confirmation |
| Schedule `expire_plans` cron on Railway | Ops | `0 0 * * * python manage.py expire_plans` |
| Switch to live Razorpay keys for production | Config | Replace `rzp_test_` with `rzp_live_` |
| Consider Celery for email reliability | Future | Low priority — current daemon threads work for low traffic |
