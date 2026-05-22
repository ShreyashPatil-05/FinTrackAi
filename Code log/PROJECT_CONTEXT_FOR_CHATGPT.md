# FinTrack Project Context for ChatGPT

Generated: 2026-05-13
Workspace: `e:\Projects\fintrack`

This file is a compact, ChatGPT-ready map of the whole project. It is meant to be pasted into another chat so that model can understand the codebase without reading every file directly.

Important privacy note: do not paste `.env`, raw webhook tokens, database contents, or production credentials into ChatGPT. This context intentionally describes secrets/configuration by name only.

## One-Sentence Summary

FinTrack is a Django personal finance web app for Indian users, with expense tracking, income, budgets, savings goals, subscriptions, CSV import/export, Google OAuth, email verification, a mock bank webhook, and Gemini-backed financial insights.

## Tech Stack

- Backend: Django 6.0.2, Python
- Database: SQLite in development, PostgreSQL in production via `DATABASE_URL`
- Frontend: Django templates, Bootstrap 5, Bootstrap Icons, Chart.js, vanilla JavaScript
- Auth: Django sessions, custom username/password auth, email verification, Google OAuth via `django-allauth`
- Security/rate limiting: `django-axes`, custom CSP middleware, CSRF on forms, token auth for webhook
- Email: console backend in dev, SMTP/SendGrid support in production code
- Static/media: local static/media in dev, WhiteNoise for prod static, optional S3 media storage
- AI insights: `google-generativeai` using `GEMINI_API_KEY`, with rule-based fallback
- Deployment: Railway/Nixpacks/Gunicorn

## Current Worktree Notes

At the time this context was generated, the git worktree already had modifications in:

- `dashboard/templates/dashboard/profile.html`
- `dashboard/templatetags/fintrack_filters.py`
- `dashboard/urls.py`
- `dashboard/views/__init__.py`
- `dashboard/views/profile.py`
- `fintrack/settings_base.py`
- `fintrack/settings_dev.py`
- `requirements.txt`
- `static/css/styles.css`

Untracked files included:

- `DSA_IN_PROJECT.md`
- `dashboard/templates/dashboard/insights.html`
- `dashboard/views/insights.py`

Treat these as user work. Do not revert them casually.

## High-Level App Structure

```text
accounts/      registration, login, logout, password change, email verification
dashboard/     dashboard, income, budgets, categories, subscriptions, savings, profile, export/upload, AI insights
expenses/      expense model, forms, list/filter/pagination, CRUD, bulk delete, bank webhook
fintrack/      Django project settings, URLs, WSGI/ASGI, custom middleware
templates/     global templates: base, navbar, footer, landing, 404, allauth overrides
static/        global CSS, JS utilities, logo
media/         user uploads such as avatars
```

## Main URL Map

Root URLs are defined in `fintrack/urls.py`.

- `/` -> landing page (`dashboard.views.landing`)
- `/dashboard/` -> main dashboard
- `/insights/` -> Gemini/rule-based AI financial insights
- `/expenses/` -> expense list, filters, pagination
- `/expenses/add/`, `/<pk>/edit/`, `/<pk>/delete/`, `/bulk-delete/`
- `/settings/` -> redirects to income settings
- `/settings/income/` plus income add/edit/delete
- `/settings/categories/`
- `/settings/budget/` and `/settings/budget/copy-last-month/`
- `/settings/upload/`
- `/subscriptions/` plus add/edit/delete
- `/savings-goals/` plus add/edit/detail/add-funds/delete
- `/profile/`, `/profile/delete/`
- `/export-data/`
- `/accounts/register/`, `/login/`, `/logout/`, `/change-password/`
- `/accounts/verify/<uuid:token>/`
- `/accounts/resend-verification/`
- `/accounts/verify-pending/`
- `/social/` -> django-allauth URLs
- `/api/webhook/bank/` -> mock bank webhook
- `/admin/` -> Django admin

## Settings and Deployment

`manage.py` loads `.env` and defaults to `fintrack.settings_dev`.

`fintrack/settings.py` auto-selects:

- production settings if `DJANGO_SETTINGS_MODULE` contains `prod` or `DATABASE_URL` exists
- development settings otherwise

`fintrack/settings_base.py` contains shared settings:

- installed apps: Django core, sites, allauth, Google provider, `accounts`, `expenses`, `dashboard`, `axes`
- auth backends: Axes, Django model backend, allauth backend
- middleware: Django core, allauth account middleware, Axes middleware, custom CSP middleware
- templates use repo-level `templates/` and app templates
- media/static settings
- login/logout redirects
- email settings from env
- reCAPTCHA env vars
- Axes lockout settings

`fintrack/settings_dev.py`:

- `DEBUG=True`
- hosts: `localhost`, `127.0.0.1`
- SQLite database at `db.sqlite3`
- console email backend
- disables HTTPS-only cookie/security enforcement

`fintrack/settings_prod.py`:

- `DEBUG=False`
- `ALLOWED_HOSTS` from env plus Railway healthcheck host
- `SITE_ID=2`
- SSL/cookie/HSTS security settings
- PostgreSQL via `DATABASE_URL` using `dj-database-url`, otherwise individual DB env vars
- inserts WhiteNoise middleware
- optional Redis cache/sessions via `REDIS_URL`
- optional S3 media storage via `USE_S3=true`

Deployment files:

- `Procfile`: Gunicorn command
- `railway.toml`: runs migrations pre-deploy, starts Gunicorn
- `nixpacks.toml`: placeholder build secret and `collectstatic` with prod settings

## Data Model

### `expenses.models.Expense`

Fields:

- `user`: owner
- `title`: expense name
- `category`: string category
- `amount`: decimal
- `date`: expense date
- `source`: `manual`, `bank`, or `subscription`

Default categories:

- `Food`, `Travel`, `Shopping`, `Bills`, `Transport`, `Entertainment`, `Savings`

The dynamic category list also includes custom categories and `Subscription`.

### `accounts.models.EmailVerificationToken`

- one-to-one with `User`
- UUID token
- created timestamp
- expires after 24 hours via `is_expired()`
- `clean()` rejects expired saved tokens

### `dashboard.models.UserProfile`

- one-to-one with `User`
- avatar image
- onboarding completion flag

### `dashboard.models.CustomCategory`

- user-owned category name
- unique per `(user, name)`

### `dashboard.models.Income`

- user, date, source, description, amount
- validates amount > 0 and date not in future
- indexed by `(user, -date)` and `(user, source)`

### `dashboard.models.CategoryBudget`

- user, category, limit, month, year
- month/year `0` means every month conceptually, but current views use specific month/year
- unique per `(user, category, month, year)`
- validates positive limit and month 0-12

### `dashboard.models.SavingsGoal`

- user, name, target, target date, icon, created timestamp
- properties: `saved`, `progress_pct`, `remaining`
- contributions are in `SavingsContribution`

### `dashboard.models.SavingsContribution`

- goal, amount, date
- validates amount > 0 and date not in future

### `dashboard.models.Subscription`

- user, name, amount, cycle, category, next billing date, status
- cycle: weekly/monthly/yearly
- status: active/paused/cancelled
- category: Streaming/Music/Software/Gaming/News/Fitness/Cloud/Other
- `monthly_cost` normalizes weekly/yearly subscriptions
- `advance_billing_date()` creates subscription expenses for elapsed cycles and advances `next_billing`

### `dashboard.models.WebhookToken`

- one-to-one with User
- stores only SHA-256 hash of raw token
- raw token is generated and shown once in admin
- `verify(raw_token)` hashes and compares in constant time

## Core User Flows

### Registration and Email Verification

Implemented in `accounts/views.py`.

1. User submits `MyUserCreationForm`.
2. Registration is rate-limited by IP: 3 attempts/hour.
3. reCAPTCHA is checked if configured.
4. User is created inactive in a DB transaction.
5. `EmailVerificationToken` is created.
6. Email is sent in a background thread.
7. User is redirected to `verify_pending`.
8. Verification link activates user and deletes token if valid and not expired.
9. Invalid verification attempts are rate-limited: 10 attempts/IP/hour.
10. Resend verification is rate-limited: 3 resends/user/hour and does not reveal whether an email exists.

Email sending:

- If `EMAIL_HOST_PASSWORD` starts with `SG.` and SendGrid is installed, the SendGrid HTTP API is used.
- Otherwise it falls back to Django `send_mail()`.
- Dev settings use console email.

### Login/Logout/Password Change

- Login uses custom `LoginForm` and Django `authenticate()`.
- If a user exists but is inactive and password matches, a verification warning is shown.
- Logout only logs out on POST, then redirects to login.
- Password change asks for username, current password, and new password; failure messages avoid username enumeration.

### Dashboard

Implemented in `dashboard/views/dashboard.py`.

The dashboard:

- creates/gets `UserProfile`
- auto-advances overdue active subscriptions
- supports month/year navigation and custom date range
- filters expenses by optional category
- sums income/expenses/balance
- calculates savings rate and health label/tip
- compares savings rate to previous month
- builds category breakdown, daily spending data, recent expenses
- produces current-month spending forecast
- shows budget alerts for categories above 80% or 100%
- shows onboarding tour until `/tour-complete/` marks profile onboarding complete

Charts are rendered client-side with Chart.js in `dashboard/templates/dashboard/dashboard.html`.

### Expense Management

Implemented in `expenses/views.py`.

Features:

- list expenses for selected month/year or custom date range
- text search on title
- multi-select category filter
- total and count summary
- pagination with 10/20/50 page size
- table/card view toggle in localStorage
- bulk delete for selected expense IDs
- add/edit/delete views scoped to current user

`ExpenseForm` builds category choices from defaults + user custom categories + `Subscription`.

### Income Settings

Implemented in `dashboard/views/income.py`, rendered through `dashboard/templates/dashboard/settings.html`.

Features:

- month/year navigation
- source text filter
- total amount and record count
- add/edit/delete income entries
- uses direct `request.POST` parsing rather than `dashboard/forms.py`

### Categories and Budgets

Implemented in `dashboard/views/budget.py`.

Categories:

- default categories are read-only
- custom categories can be added/deleted
- names are normalized with `.title()`
- duplicate custom/default names are prevented

Budgets:

- per-category limits for a selected month/year
- total budget goal is computed from all saved category limits
- budget rows include spent, limit, remaining, percent, status
- copy last month copies previous month limits into selected month
- dashboard only shows budget alerts for the current month and non-custom ranges

### Subscriptions

Implemented in `dashboard/views/subscriptions.py`.

Features:

- list all subscriptions
- active/paused/cancelled states
- total monthly/yearly normalized cost
- due today / due soon indicators
- auto-advance overdue active subscriptions
- add/edit/delete modals
- `advance_billing_date()` creates `Expense` rows with `source='subscription'`

Important model/view interaction:

- The model `Subscription.clean()` rejects `next_billing` in the past.
- `advance_billing_date()` is designed to handle overdue dates, but saving a subscription with a past date can conflict with model validation.

### Savings Goals

Implemented in `dashboard/views/savings.py`.

Features:

- list goals with progress
- create/edit/delete goals
- Bootstrap-icon picker plus custom icon text input in template
- detail page shows progress, milestones, add-funds form, recent contributions
- adding funds creates both `SavingsContribution` and a `Savings` category `Expense` in one transaction
- add-funds rejects zero/negative and amounts greater than remaining target

### Profile

Implemented in `dashboard/views/profile.py`.

Features:

- edit first name, last name, username, email
- avatar upload/remove
- avatar validation: max 2MB and magic-byte signature for JPEG/PNG/GIF/WebP-ish RIFF
- old avatar deleted safely
- account deletion requires password for normal users or a confirmation checkbox for OAuth users
- account delete logs out then deletes the user, cascading owned data

### CSV Upload

Implemented in `dashboard/views/upload.py`, rendered in settings page.

Features:

- upload CSV, preview first 5 rows, then import from session-stored CSV text
- required columns: `title`, `category`, `amount`, `date`
- row-level validation for title, positive amount, `YYYY-MM-DD` date
- unknown categories become `Other`
- reports skipped rows

### CSV Export

Implemented in `dashboard/views/export.py`.

Features:

- exports CSV with UTF-8 BOM for Excel
- filter modes: custom date range, month/year, full year
- optional category filters for expenses
- data type checkboxes: expenses, income, savings, subscriptions
- output sections: `=== EXPENSES ===`, `=== INCOME ===`, `=== SAVINGS GOALS ===`, `=== SUBSCRIPTIONS ===`

### AI Financial Insights

Implemented in `dashboard/views/insights.py`, template `dashboard/templates/dashboard/insights.html`.

Data gathered:

- last 3 months income/spent/saved/savings rate/top categories
- current-month budget status
- active subscriptions and normalized monthly subscription total
- savings goals
- anomalous recent expenses greater than 2x category average and > Rs.500

If `GEMINI_API_KEY` is set:

- calls `google.generativeai.GenerativeModel('gemini-2.5-flash')`
- prompts for exactly 5 JSON insights
- parses JSON, stripping markdown fences if needed

If Gemini is missing/fails:

- uses rule-based insights for savings trend, spending spikes, budget overages, subscriptions, goals near completion, anomalies, or a default empty-state insight

The template has a refresh button that fetches the same URL with `X-Requested-With: XMLHttpRequest` and replaces cards with returned JSON.

### Mock Bank Webhook

Implemented in `expenses/webhook.py`.

Endpoint:

- `POST /api/webhook/bank/`
- CSRF exempt
- requires header `X-Bank-Token`

Payload:

```json
{
  "merchant": "Merchant Name",
  "amount": 123.45,
  "category": "Food",
  "date": "2026-04-24"
}
```

Behavior:

- verifies token using `WebhookToken.verify()`
- requires merchant, amount, category
- amount must be positive
- category is title-cased and allowed only if in default categories + `Subscription`, otherwise `Other`
- creates an expense for token-bound user with `source='bank'`

`mock_bank_simulator.py` sends sample transactions every 8 seconds to a configured URL. The file currently contains a hardcoded token/production URL; treat that token as sensitive and rotate it if this repo is public or shared.

## Frontend Architecture

Most UI is server-rendered Django templates. There is a large central stylesheet:

- `static/css/styles.css`

It contains global layout, auth pages, landing page, dashboard, expense list/form, settings, subscription cards, savings goals, profile, export, mobile fixes, dark mode, and AI insights styles.

Global JS:

- `static/js/utils.js`: `window.inrJS()` Indian currency formatter
- `static/js/filters.js`: expense category dropdown selected-count behavior

Common template:

- `templates/base.html`: Bootstrap, Bootstrap Icons, Inter font, custom CSS/JS, navbar/footer, Django message toasts, theme toggle, dynamic colors for custom category badges, auto-dismiss toasts
- `templates/navbar.html`: authenticated nav, avatar dropdown, theme toggle, unauthenticated sign in/register buttons
- `templates/footer.html`
- `templates/landing.html`: marketing landing page
- `templates/404.html`: standalone custom 404 page

Templates use `dashboard/templatetags/fintrack_filters.py`:

- `inr`: formats Indian currency as Rs-style display using the rupee symbol and L/Cr abbreviations
- `split`
- `json_monthly_labels`, `json_monthly_income`, `json_monthly_spent`, `json_monthly_saved`

## Forms

`accounts/forms.py` is actively used:

- `MyUserCreationForm`: username/email/password registration, email uniqueness, username uniqueness/length/regex
- `LoginForm`
- `ChangePasswordForm`

`expenses/forms.py` is actively used:

- `ExpenseForm`
- `get_category_choices(user)`

`dashboard/forms.py` exists but appears not fully integrated into the current views. It also appears stale relative to current model field names:

- `SubscriptionForm` uses `billing_cycle`, but model uses `cycle`
- `SavingsGoalForm` uses `target_amount`, but model uses `target`

Future work should either integrate and fix these forms or remove them to avoid confusion.

## Admin

`dashboard/admin.py` unregisters Django `User` and registers a custom `FinTrackUserAdmin` with inlines:

- `UserProfile`
- `Income`
- `Expense`
- `CategoryBudget`
- `Subscription`
- `SavingsGoal`
- `CustomCategory`

It also registers `WebhookTokenAdmin`, showing the raw token once after creation.

`expenses/admin.py` sets admin site title/header/index title.

`accounts/admin.py` is currently empty.

## Tests

`dashboard/tests.py` has broad Django `TestCase` coverage for:

- savings goal model properties
- subscription monthly cost and billing advancement
- login/register/logout/password change
- dashboard login and month handling
- expense CRUD and pagination
- savings goal views and add-funds behavior
- income views
- budget persistence and dashboard alerts
- profile/account deletion
- subscriptions
- custom 404

`accounts/tests.py` and `expenses/tests.py` are placeholders.

Potential issue: several tests create models with hardcoded 2026 dates. As real current date moves beyond those dates, model validation that rejects past/future dates may affect stability. On 2026-05-13, some `2026-03-01` dates are in the past, which is fine for income/expense/contribution date validation except `SavingsGoal.target_date` and `Subscription.next_billing` rules.

## Known Gotchas / Important Observations

- Encoding appears mojibake in several files when read from this environment: rupee symbols, arrows, emoji, and box-drawing characters appear as sequences like `â‚¹`. The actual files may be UTF-8 interpreted incorrectly by PowerShell output, but check before editing text.
- `dashboard/templates/dashboard/savings_goal_detail.html` appears malformed near the top: it has `{% load fintrack_filters %} — FinTrack{% endblock %}` without a visible `{% block title %}` start. This may cause a template syntax error.
- `dashboard/forms.py` is not integrated and has stale field names.
- `Subscription.clean()` disallows past `next_billing`, while subscription auto-advance logic expects overdue dates to exist. Be careful when editing this area.
- `Subscription` has duplicate `__repr__` methods; the second overwrites the first.
- `mock_bank_simulator.py` has a hardcoded webhook token and production URL. Redact/rotate before sharing publicly.
- `accounts/views.py` sends email in a background daemon thread. This is fine for demos/low traffic but not durable; Celery/RQ would be safer.
- `bank_webhook` accepts the date string directly; invalid date format is not explicitly validated before `Expense.objects.create()`.
- `settings_prod.py` uses `LocMemCache` fallback for rate limiting if Redis is missing; this is per process and not shared across Gunicorn workers.
- `logout_view` redirects to login even for GET; only POST performs logout.
- `.env`, `db.sqlite3`, media, staticfiles, and caches should not be committed or pasted.

## File-by-File Guide

### Repo Root

- `.env`: local secrets; do not share.
- `.gitignore`: ignores Python caches, SQLite DB, logs, media, staticfiles, envs, VS Code, debug scripts.
- `manage.py`: loads dotenv and defaults to dev settings.
- `requirements.txt`: Django, allauth, axes, dotenv, Postgres, WhiteNoise, Redis, Railway/prod dependencies, S3, requests, SendGrid, Gemini.
- `Readme.md`: user-facing setup/features/deployment overview.
- `DEVELOPMENT_NOTES.md`: historical/current production notes.
- `CURRENT_STATUS.md`: status and completed tasks.
- `CODE_REVIEW_SENIOR.md`: senior review document.
- `FINTRACK_FEATURES_COMPREHENSIVE.md`: comprehensive feature documentation.
- `TESTING_GUIDE.md`, `TESTING_CHECKLIST.md`: testing documentation.
- `MOSCOW.md`: prioritization analysis.
- `DSA_IN_PROJECT.md`: untracked document, likely data-structures/algorithms notes.
- `mock_bank_simulator.py`: standalone transaction simulator for webhook.
- `locustfile.py`: load testing script for Railway host.
- `Procfile`, `railway.toml`, `nixpacks.toml`: deployment files.
- `db.sqlite3`: local database; do not paste/share.

### `fintrack/`

- `__init__.py`: package marker.
- `settings.py`: environment-aware settings entry point.
- `settings_base.py`: shared settings.
- `settings_dev.py`: development settings.
- `settings_prod.py`: production settings.
- `urls.py`: root URL includes and webhook route.
- `middleware.py`: custom CSP and Referrer-Policy middleware.
- `wsgi.py`, `asgi.py`: Django application entry points.

### `accounts/`

- `models.py`: `EmailVerificationToken`.
- `forms.py`: register/login/change-password forms.
- `views.py`: registration, email verification, resend, login, logout, password change, reCAPTCHA, email sending.
- `urls.py`: auth URL patterns.
- `admin.py`: empty.
- `apps.py`: app config.
- `tests.py`: placeholder.
- `management/commands/cleanup_expired_tokens.py`: deletes tokens older than 24 hours, supports `--dry-run`.
- `templates/accounts/auth.html`: full auth UI for login/register/change password, Google sign-in button, reCAPTCHA, password strength/match JS, dark mode.
- `templates/accounts/verify_pending.html`: check-email page and resend form.
- `templates/accounts/resend_verification.html`: resend form.

### `expenses/`

- `models.py`: `Expense`, default categories.
- `forms.py`: dynamic expense form and category choice builder.
- `views.py`: list, add, edit, delete, bulk delete.
- `urls.py`: expense URL patterns.
- `webhook.py`: mock bank webhook endpoint.
- `admin.py`: admin title/header.
- `apps.py`: app config.
- `tests.py`: placeholder.
- `templates/expenses/expense_list.html`: filters, table/card views, pagination, bulk delete JS.
- `templates/expenses/expense_form.html`: add/edit expense UI with category warnings.
- `templates/expenses/expense_confirm_delete.html`: delete confirmation.
- `migrations/`: expense schema history, including source field and subscription source migration.

### `dashboard/`

- `models.py`: profile, custom categories, income, budgets, savings goals/contributions, subscriptions, webhook tokens.
- `forms.py`: model forms, currently stale/not integrated.
- `utils.py`: month navigation, date range parsing, currency formatting, savings rate/health, available years.
- `urls.py`: dashboard/settings/subscriptions/savings/profile/export/insights routes.
- `admin.py`: custom `UserAdmin` with inlines and webhook token admin.
- `apps.py`: app config.
- `tests.py`: main automated test suite.
- `templatetags/fintrack_filters.py`: currency and Chart.js JSON filters.
- `views/__init__.py`: re-exports split view modules.
- `views/landing.py`: landing page, redirect authenticated users.
- `views/dashboard.py`: main dashboard and tour completion endpoint.
- `views/insights.py`: Gemini/rule-based financial insights.
- `views/profile.py`: profile/avatar/account deletion.
- `views/income.py`: income settings CRUD.
- `views/budget.py`: categories and budget settings.
- `views/subscriptions.py`: subscription CRUD and summaries.
- `views/savings.py`: savings goals CRUD/detail/add-funds.
- `views/export.py`: CSV export.
- `views/upload.py`: CSV import preview/import.
- `views/settings.py`: redirects to income settings.
- `templates/dashboard/dashboard.html`: dashboard UI, charts, forecast, budget alerts, onboarding tour.
- `templates/dashboard/settings.html`: multipurpose settings page for income/categories/budget/upload.
- `templates/dashboard/subscriptions.html`: subscription cards/modals.
- `templates/dashboard/savings_goals.html`: goal cards/modals/icon picker.
- `templates/dashboard/savings_goal_detail.html`: goal detail/deposit/history; likely malformed top block.
- `templates/dashboard/profile.html`: profile/avatar/export/delete account UI.
- `templates/dashboard/export.html`: CSV export UI.
- `templates/dashboard/insights.html`: AI insights UI, trend chart, AJAX refresh.
- `migrations/`: dashboard schema history, latest visible migration `0015_add_model_validation.py`.

### `templates/`

- `base.html`: global shell, CSS/JS imports, theme toggle, toasts, dynamic category badge styles.
- `navbar.html`: top nav and user dropdown.
- `footer.html`: global footer.
- `landing.html`: public marketing landing page.
- `404.html`: standalone custom not-found page.
- `socialaccount/signup.html`: allauth Google signup completion.
- `socialaccount/connections.html`: allauth connected accounts management.

### `static/`

- `css/styles.css`: large shared stylesheet for all pages, light/dark mode, mobile fixes.
- `js/utils.js`: global Indian currency JS formatter.
- `js/filters.js`: category dropdown selection behavior.
- `images/logo.png`: app logo.

## How to Run Locally

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Dev defaults:

- settings module: `fintrack.settings_dev`
- database: `db.sqlite3`
- email: console backend

## Useful Commands

```powershell
python manage.py check
python manage.py test
python manage.py test dashboard
python manage.py cleanup_expired_tokens --dry-run
python manage.py cleanup_expired_tokens
python manage.py collectstatic --noinput --settings=fintrack.settings_prod
```

## Environment Variables

Common variables:

- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `RECAPTCHA_SITE_KEY`
- `RECAPTCHA_SECRET_KEY`
- `GEMINI_API_KEY`
- `REDIS_URL`
- `USE_S3`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME`

Never paste actual values into ChatGPT.

## Recommended Next Maintenance Tasks

1. Fix `dashboard/templates/dashboard/savings_goal_detail.html` top block syntax if it fails rendering.
2. Rotate/remove hardcoded webhook token in `mock_bank_simulator.py`.
3. Decide whether to fix and integrate `dashboard/forms.py` or delete it.
4. Add targeted tests for email verification/resend, webhook validation, insights fallback, and CSV upload edge cases.
5. Consider replacing background email threads with a proper job queue before significant production traffic.
6. Add stricter date validation to bank webhook payload.
7. Revisit subscription past-date validation versus auto-advance behavior.
