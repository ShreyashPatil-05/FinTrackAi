# FinTrack — Personal Finance Tracker

A full-stack web application built with Django that helps users track expenses, manage income, set savings goals, and monitor subscriptions — all in one place.

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
- Expense tracking with categories, search, and month-based navigation
- Income management with monthly view and source tracking
- Interactive dashboard with spending charts, financial health score, and month-end forecast
- Category-wise budget limits with live progress bars and alerts
- Savings goals with contribution history and progress tracking
- Subscription tracker with auto-billing date advancement

### Auth & Security
- Register / Login / Logout
- Google OAuth 2.0 sign-in
- Email verification on registration (Gmail SMTP)
- Brute force protection — account locked after 5 failed login attempts
- Change password requires current password verification
- Session-based authentication with `@login_required` route protection

### Data
- CSV import with per-row error reporting
- CSV export with date range and category filters
- Indian currency formatting (₹, L, Cr) across all pages
- Pagination with 10 / 20 / 50 rows per page selector

### UX
- Light and dark mode
- Responsive design
- Onboarding tour for new users
- Custom 404 error page
- Budget alerts banner on dashboard
- Empty state for new users

---

## Project Structure

```
fintrack/
├── accounts/          # Auth — register, login, logout, email verification
├── expenses/          # Expense CRUD, bulk delete, pagination
├── dashboard/         # Dashboard, income, budget, savings, subscriptions, profile
│   └── templatetags/  # Custom template filters (inr currency formatter)
├── templates/         # Global templates — base, navbar, footer, landing, 404
├── static/
│   ├── css/styles.css # All styles (light + dark mode)
│   └── js/utils.js    # Shared JS utilities (inrJS formatter)
├── fintrack/          # Django project config — settings, urls, wsgi
├── .env               # Environment variables (not committed)
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

### 3. Create `.env` file
```
SECRET_KEY=your-secret-key-here
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
```

> Generate a secret key at [djecrety.ir](https://djecrety.ir)
> Get a Gmail App Password at myaccount.google.com → Security → App Passwords

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Start the server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

---

## Running Tests

```bash
python manage.py test dashboard
```

54 tests covering models, views, auth, pagination, budget alerts, savings goals, and subscriptions.

---

## Google OAuth Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → APIs & Services → Credentials → OAuth 2.0 Client ID
3. Add redirect URI: `http://localhost:8000/social/google/login/callback/`
4. In Django admin → Sites → set domain to `localhost:8000`
5. Social Applications → Add → Google → paste Client ID and Secret

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key for cryptographic signing |
| `EMAIL_HOST_USER` | Gmail address used to send verification emails |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (not your real Gmail password) |

---

## Future Scope

- **Celery + Redis** — scheduled email reminders for subscription renewals and budget alerts
- **Django REST Framework** — REST API for mobile app or Power BI integration
- **Mock Bank Webhook** — simulate real-time transaction feeds from a bank
- **PostgreSQL** — replace SQLite for multi-user production deployment
