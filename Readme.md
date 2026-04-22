# FinTrack — Personal Finance Tracker

A full-stack web application built with Django that helps users track expenses, manage income, set savings goals and monitor subscriptions — all in one place.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.2 |
| Database | SQLite |
| Frontend | HTML, CSS, Bootstrap 5, Chart.js |
| Auth | Django sessions + Google OAuth 2.0 (django-allauth) |
| Security | django-axes (brute force protection) |
| Email | Gmail SMTP |
| Testing | Django TestCase (54 tests) |

---

## Features

### Core
- Expense tracking with categories, search and month-based navigation
- Income management with monthly view and source tracking
- Interactive dashboard with spending charts, financial health score and month-end forecast
- Category-wise budget limits with live progress bars and alerts
- Savings goals with contribution history and progress tracking
- Subscription tracker with auto-billing date advancement
- Pagination with 10 / 20 / 50 rows per page selector
- Indian currency formatting across all pages (Rs., L, Cr)

### Mock Bank API
- Webhook endpoint at POST /api/webhook/bank/
- Per-user webhook token stored in DB — token is bound to a specific user, no cross-user posting possible
- Token can be regenerated via Django admin (WebhookToken model)
- Standalone simulator script that sends fake transactions every 8 seconds
- Auto-imported expenses tagged with a bank badge in the expense list

### Auth and Security
- Register / Login / Logout (logout via POST only — CSRF safe)
- Google OAuth 2.0 sign-in
- Email verification on registration (Gmail SMTP) with 24-hour token expiry
- Brute force protection — account locked after 5 failed login attempts
- Change password requires current password — same error message whether username exists or not (prevents enumeration)
- Account deletion requires password confirmation
- Avatar upload validates file type via magic bytes and enforces 2MB size limit
- Per-user webhook tokens bound to a specific user — no cross-user posting
- Session-based authentication with login_required route protection
- never_cache on all edit/form views — prevents stale data on browser back
- SECRET_KEY loaded from environment variable

### Data
- CSV import with per-row error reporting for invalid data
- CSV export with date range and category filters
- Account deletion with full data cascade

### UX
- Light and dark mode
- Responsive design
- Onboarding tour for new users
- Custom 404 error page
- Budget alerts banner on dashboard
- Empty state for new users with zero expenses

---

## Project Structure

```
fintrack/
├── accounts/           # Auth — register, login, logout, email verification
├── expenses/           # Expense CRUD, bulk delete, pagination, webhook
│   └── webhook.py      # Mock bank webhook receiver
├── dashboard/          # Dashboard, income, budget, savings, subscriptions, profile
│   └── templatetags/   # Custom template filters (inr currency formatter)
├── templates/          # Global templates — base, navbar, footer, landing, 404
├── static/
│   ├── css/styles.css  # All styles (light + dark mode)
│   └── js/utils.js     # Shared JS utilities (inrJS formatter)
├── fintrack/           # Django project config — settings, urls, wsgi
├── mock_bank_simulator.py  # Standalone script to simulate bank transactions
├── .env                # Environment variables (not committed)
├── MOSCOW.md           # MoSCoW prioritization analysis
└── requirements.txt
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/ShreyashPatil-05/FinTrackAi.git
cd FinTrackAi
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create .env file
```
SECRET_KEY=your-secret-key-here
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
BANK_WEBHOOK_SECRET=fintrack-mock-bank-secret-2026
```

> Generate a secret key at https://djecrety.ir
> Get a Gmail App Password at myaccount.google.com > Security > App Passwords

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Start the server
```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000

---

## Mock Bank API — Demo

The mock bank simulator sends fake transactions to your app automatically, simulating how a real bank would push transaction data. Each user has their own webhook token stored in the database — the token is bound to that user so no cross-user posting is possible.

### Step 1 — Create a webhook token for your user
- Go to http://127.0.0.1:8000/admin/
- Dashboard > Webhook Tokens > Add
- Select your user and save
- Copy the generated token

### Step 2 — Update the simulator
Open mock_bank_simulator.py and set your token:
```python
WEBHOOK_SECRET = 'paste-your-token-here'
```
Remove or ignore the `USER_ID` line — the token identifies the user automatically.

### Step 3 — Open two terminals

Terminal 1 — run Django:
```bash
python manage.py runserver
```

Terminal 2 — run the simulator:
```bash
python mock_bank_simulator.py
```

### Step 4 — Watch it work
You will see output like this in Terminal 2:
```
[SENT]  Swiggy                    Food            Rs.347.00
[SENT]  Netflix                   Subscription    Rs.649.00
[SENT]  Uber                      Transport       Rs.168.00
```

Every 8 seconds a new expense appears on your dashboard and expense list with a purple "Auto" badge showing it came from the bank.

Press Ctrl+C in Terminal 2 to stop the simulator.

---

## Running Tests

```bash
python manage.py test dashboard
```

54 tests covering models, views, auth, pagination, budget alerts, savings goals, and subscriptions.

---

## Google OAuth Setup

1. Go to https://console.cloud.google.com
2. Create a project > APIs and Services > Credentials > OAuth 2.0 Client ID
3. Add redirect URI: http://localhost:8000/social/google/login/callback/
4. Also add: http://127.0.0.1:8000/social/google/login/callback/
5. In Django admin > Sites > set domain to localhost:8000
6. Social Applications > Add > Google > paste Client ID and Secret

---

## Environment Variables

| Variable | Description |
|---|---|
| SECRET_KEY | Django secret key for cryptographic signing |
| EMAIL_HOST_USER | Gmail address used to send verification emails |
| EMAIL_HOST_PASSWORD | Gmail App Password (not your real Gmail password) |

---

## Future Scope

- Celery + Redis — scheduled email reminders for subscription renewals and budget alerts
- Django REST Framework — REST API for mobile app or Power BI integration
- Real bank API integration using Setu or Finvu (India)
- PostgreSQL — replace SQLite for multi-user production deployment
