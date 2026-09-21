# FinTrack — AI-Powered Personal Finance Tracker

A full-stack Django web application for tracking expenses, managing income, setting savings goals, monitoring subscriptions, and getting AI-powered financial insights — with a built-in SaaS monetisation layer.

**Live:** [web-production-95045.up.railway.app](https://web-production-95045.up.railway.app)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.2 |
| Database | PostgreSQL (production) / SQLite (development) |
| Frontend | HTML5, CSS3, Bootstrap 5.3, Chart.js |
| Auth | Django sessions + Google OAuth 2.0 (django-allauth) |
| AI | Google Gemini 2.5 Flash (`google.genai`) |
| Payments | Razorpay (UPI, cards, net banking) |
| Email | SendGrid HTTP API (production) / SMTP (development) |
| Security | django-axes, reCAPTCHA v2, CSP headers |
| Deployment | Railway (Nixpacks, PostgreSQL, cron jobs) |
| Static files | WhiteNoise |

---

## Features

### Core Financial Tracking
- **Expense tracking** — CRUD, categories, search, month navigation, AJAX pagination
- **Income management** — multiple sources, monthly view
- **Dashboard** — spending charts, category breakdown, financial health score, month-end forecast, budget alerts
- **Budget management** — per-category monthly limits with live progress bars
- **Savings goals** — target amounts, contribution history, predicted completion date
- **Subscription tracker** — auto-billing date advancement, overdue detection
- **CSV import / export** — bulk import with per-row validation, filtered export

### AI Insights *(Pro)*
- Powered by **Google Gemini 2.5 Flash**
- Analyses last 3 months of transactions and generates 5 personalised, actionable insights
- Rule-based fallback insights for free users or when API key is not set
- 15-minute response cache + 10 calls/hour rate limit per user
- Month-over-month comparison, budget status bars, anomaly detection, savings goal progress

### SaaS / Monetisation
- **Free plan** — 50 expenses/mo, 20 income/mo, 2 savings goals, 3 subscriptions, 3 budget categories
- **Pro plan** — unlimited everything + AI Insights, CSV import/export, bank webhook
- Pricing: ₹49/month or ₹499/year
- **Razorpay** payment integration (UPI, cards, net banking)
  - Server-side HMAC-SHA256 payment verification
  - Server-to-server webhook handler with signature verification and idempotency
  - Dual activation path: frontend callback + webhook fallback
- Plan expiry management (`expire_plans` management command)
- Pro plan email notifications (payment success, expiry reminder, plan expired)

### Authentication & Security
- Email/password registration with email verification (SendGrid)
- Google OAuth 2.0 (django-allauth)
- Forgot password / reset password flow (1-hour token expiry)
- Remember Me (30-day session)
- Brute force protection (django-axes — 5 attempts = 15-min lockout)
- reCAPTCHA v2 on registration
- Rate limiting on registration, verification, and resend endpoints
- CSRF protection on all state-changing endpoints
- `@require_POST` on all delete views — no GET-triggered deletions
- SHA-256 hashed webhook tokens
- Avatar file type validated by magic bytes
- `SECURE_HSTS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in production

### Bank Webhook API
- `POST /api/webhook/bank/` — receives simulated bank transactions
- Per-user tokens, rate-limited (60 req/min per user)
- Auto-categorisation with fallback to "Other"
- Expenses tagged with a `🏦 Auto` badge in the list
- Standalone `mock_bank_simulator.py` for local testing *(Pro feature)*

### UX
- Light and dark mode (shared `theme.js`, no inline scripts)
- Animated auth/login/register page (particles, gradient shift, slide-in form)
- Responsive design (mobile-first)
- AJAX pagination on expense list (no full-page reloads)
- Onboarding tour for new users
- Custom 404 page

---

## Project Structure

```
fintrack/
├── accounts/               # Auth — register, login, email verification, password reset
│   ├── services/
│   │   └── auth_service.py
│   └── migrations/
├── expenses/               # Expense CRUD, bulk delete, AJAX pagination, webhook
│   └── webhook.py
├── dashboard/              # Dashboard, income, budget, savings, subscriptions, insights
│   ├── services/
│   │   ├── plan_service.py     # SaaS plan limits
│   │   ├── email_service.py    # Payment / expiry emails
│   │   ├── budget_service.py
│   │   ├── expense_service.py  # Forecasting, anomaly detection
│   │   ├── income_service.py
│   │   ├── savings_service.py
│   │   └── subscription_service.py
│   ├── views/
│   │   ├── dashboard.py
│   │   ├── insights.py         # AI insights (Gemini)
│   │   ├── payment.py          # Razorpay create_order, verify_payment, webhook
│   │   ├── income.py
│   │   ├── savings.py
│   │   ├── subscriptions.py
│   │   ├── budget.py
│   │   ├── export.py
│   │   ├── upload.py
│   │   └── profile.py
│   ├── management/commands/
│   │   └── expire_plans.py     # Daily cron — expire Pro plans
│   └── decorators.py           # @plan_required decorator
├── templates/              # Global templates — base, navbar, landing
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── theme.js            # Shared dark/light mode toggle
│       ├── dashboard.js
│       ├── insights.js
│       ├── expense_list.js     # AJAX pagination
│       ├── pricing.js          # Razorpay checkout
│       └── ...
├── fintrack/               # Django project config
│   ├── settings_base.py
│   ├── settings_prod.py    # Railway production settings
│   └── settings_dev.py
├── Feature implementation/ # Feature planning docs
├── code_log/               # Development session logs (gitignored)
├── mock_bank_simulator.py
├── railway.toml
├── nixpacks.toml
└── requirements.txt
```

---

## Local Setup

### 1. Clone
```bash
git clone https://github.com/ShreyashPatil-05/FinTrackAi.git
cd FinTrackAi
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create `.env`
```env
SECRET_KEY=your-secret-key-here

# Email — use SMTP for local dev
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password

# Google OAuth (optional for local)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# reCAPTCHA (optional for local)
RECAPTCHA_SITE_KEY=
RECAPTCHA_SECRET_KEY=

# Gemini AI — enables Pro AI Insights
GEMINI_API_KEY=

# Razorpay — enables payment flow
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
```

> Generate a secret key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### 4. Migrate and run
```bash
python manage.py migrate
python manage.py runserver
```

Visit http://127.0.0.1:8000

---

## Production Deployment (Railway)

The project is configured for Railway with Nixpacks:

- `nixpacks.toml` — runs `collectstatic` at **build time** (baked into image)
- `railway.toml` — runs `migrate` at **pre-deploy** (before traffic switches)
- Gunicorn start command configured in `railway.toml`

### Required Railway environment variables
```
SECRET_KEY, DEBUG, ALLOWED_HOSTS, SITE_ID
DATABASE_URL
EMAIL_HOST_PASSWORD          # SendGrid API key (SG.xxx...)
DEFAULT_FROM_EMAIL
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY
GEMINI_API_KEY               # optional
RAZORPAY_KEY_ID              # required for payments
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
```

### Recommended cron jobs (Railway)
```bash
0 0 * * *   python manage.py expire_plans
0 3 * * *   python manage.py cleanup_expired_tokens
```

---

## Razorpay Setup

1. Add `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` to `.env`
2. In Razorpay Dashboard → Settings → Webhooks:
   - URL: `https://your-domain.com/payment/webhook/`
   - Events: `payment.captured`, `payment.failed`
   - Secret: same value as `RAZORPAY_WEBHOOK_SECRET`
3. Use test card `4111 1111 1111 1111` / any future expiry / CVV `123` / OTP `1234`

---

## Mock Bank API

```bash
# Terminal 1
python manage.py runserver

# Terminal 2
python mock_bank_simulator.py
```

1. Go to Django Admin → Webhook Tokens → create one for your user
2. Copy the token into `mock_bank_simulator.py` as `WEBHOOK_SECRET`
3. Expenses auto-appear in the dashboard with a `🏦 Auto` badge every 8 seconds

---

## Plan Limits

| Feature | Free | Pro |
|---|---|---|
| Expenses / month | 50 | Unlimited |
| Income entries / month | 20 | Unlimited |
| Savings goals | 2 | Unlimited |
| Subscriptions | 3 | Unlimited |
| Budget categories | 3 | Unlimited |
| AI Insights | ❌ | ✅ Gemini |
| CSV Import / Export | ❌ | ✅ |
| Bank Webhook | ❌ | ✅ |

---

## Google OAuth Setup

1. [Google Cloud Console](https://console.cloud.google.com) → Create project → APIs & Services → Credentials → OAuth 2.0 Client ID
2. Redirect URIs: `http://localhost:8000/social/google/login/callback/`
3. Django Admin → Sites → set domain to `localhost:8000`
4. Django Admin → Social Applications → Add → Google → paste Client ID and Secret

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Django cryptographic signing key |
| `DATABASE_URL` | Production | PostgreSQL connection string |
| `EMAIL_HOST_PASSWORD` | ✅ | SendGrid API key (`SG.xxx`) or Gmail app password |
| `DEFAULT_FROM_EMAIL` | Production | Sender email address |
| `GOOGLE_CLIENT_ID` | OAuth | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth | Google OAuth client secret |
| `RECAPTCHA_SITE_KEY` | Registration | reCAPTCHA v2 site key |
| `RECAPTCHA_SECRET_KEY` | Registration | reCAPTCHA v2 secret key |
| `GEMINI_API_KEY` | AI Insights | Google Gemini API key |
| `RAZORPAY_KEY_ID` | Payments | Razorpay key ID (`rzp_test_` or `rzp_live_`) |
| `RAZORPAY_KEY_SECRET` | Payments | Razorpay key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Payments | Razorpay webhook signature secret |
