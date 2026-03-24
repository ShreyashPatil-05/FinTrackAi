# FinTrack — MoSCoW Analysis

## Project Overview

FinTrack is a personal finance management web application built as a college-level project using **Django 6** (Python), **SQLite**, **Bootstrap 5**, **Chart.js**, and vanilla JavaScript. It allows users to track expenses, income, subscriptions, savings goals, and budgets — all scoped per authenticated user.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 6 (Python) |
| Database | SQLite (via Django ORM) |
| Frontend CSS | Bootstrap 5.3 + Custom CSS (styles.css) |
| Icons | Bootstrap Icons 1.11 |
| Charts | Chart.js (CDN) |
| Fonts | Google Fonts — Inter |
| Media Storage | Local filesystem (`/media/avatars/`) |
| Auth | Django built-in `django.contrib.auth` |
| Date Utilities | `python-dateutil` (`relativedelta`) |
| Admin | Django Admin (customised) |
| Static Files | Django `staticfiles` |

---

## Project Structure

```
fintrack/           → Django project config (settings, root URLs, WSGI/ASGI)
accounts/           → Authentication app (register, login, logout, change password)
expenses/           → Expense tracking app (CRUD, bulk delete, filters)
dashboard/          → Core app (dashboard, income, budgets, subscriptions, savings, export, profile)
templates/          → Global templates (base, navbar, footer, landing)
static/             → CSS, JS, images
media/              → User-uploaded files (avatars)
```

---

## Apps & Their Responsibilities

### `fintrack/` — Project Config
- `settings.py` — installed apps, middleware, DB, static/media paths, auth redirects
- `urls.py` — root URL dispatcher; includes `accounts/`, `dashboard/`, `expenses/`; serves media in dev
- `wsgi.py` / `asgi.py` — deployment entry points

### `accounts/` — Authentication
- **Models:** none (uses Django's built-in `User`)
- **Forms:** `MyUserCreationForm`, `LoginForm`, `ChangePasswordForm`
- **Views:** `register_view`, `login_view`, `logout_view`, `change_password_view`
- **Template:** `auth.html` — single template handles all 3 page types via `page_type` context variable
- **URLs:** `/accounts/register/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/change-password/`

### `expenses/` — Expense Tracking
- **Model:** `Expense` — `user`, `title`, `category`, `amount`, `date`, `created_at`
- **Default categories:** Food, Travel, Shopping, Bills, Transport, Entertainment, Savings (+ Subscription added dynamically)
- **Forms:** `ExpenseForm` (ModelForm), `get_category_choices()` — merges default + custom categories per user
- **Views:** `expense_list`, `add_expense`, `edit_expense`, `delete_expense`, `bulk_delete_expenses`
- **Templates:** `expense_list.html`, `expense_form.html`, `expense_confirm_delete.html`
- **URLs:** `/expenses/`, `/expenses/add/`, `/expenses/<pk>/edit/`, `/expenses/<pk>/delete/`, `/expenses/bulk-delete/`

### `dashboard/` — Core Feature App
All primary features live here. See detailed breakdown below.

---

## Dashboard App — Models

### `UserProfile`
Extends Django's `User` with a one-to-one relationship.
- `monthly_income` — DecimalField (legacy, not actively used in views)
- `avatar` — ImageField, uploaded to `media/avatars/`
- `onboarding_complete` — BooleanField, tracks whether the product tour has been completed

### `CustomCategory`
User-defined expense categories.
- `user` FK, `name` CharField
- Unique together: `(user, name)`
- Merged with `DEFAULT_CATEGORIES` in `get_category_choices()`

### `Income`
Monthly income entries per user.
- `user` FK, `date`, `source` (Salary/Freelance/Business/Investment/Gift/Other), `description`, `amount`
- Used to compute balance, savings rate, and spending forecast on the dashboard

### `CategoryBudget`
Per-user, per-category monthly spending limits.
- `user` FK, `category`, `limit`, `month`, `year`
- Unique together: `(user, category, month, year)`
- `month=0 / year=0` reserved for "every month" (not currently used in UI)

### `SavingsGoal`
A financial target the user is saving toward.
- `user` FK, `name`, `target`, `saved`, `target_date`, `icon`, `created_at`
- `ICON_CHOICES` — 10 preset Bootstrap Icons (piggy-bank, house, car-front, etc.)
- `progress_pct` property — safe division, clamps 0–100, handles None target/saved
- `remaining` property — `max(target - saved, 0)`, handles None

### `SavingsContribution`
Individual deposit records linked to a `SavingsGoal`.
- `goal` FK, `amount`, `date`, `created_at`
- Ordered by `-date, -created_at` (newest first)
- Each deposit also creates an `Expense` with category `'Savings'`

### `Subscription`
Recurring billing tracker.
- `user` FK, `name`, `amount`, `cycle` (weekly/monthly/yearly), `category`, `next_billing`, `status` (active/paused/cancelled)
- `monthly_cost` property — normalises weekly/yearly to monthly equivalent
- `advance_billing_date()` — advances `next_billing` past today using `dateutil.relativedelta`, creates an `Expense` per elapsed cycle with category `'Subscription'`

---

## Dashboard App — Views

### `landing`
Public landing page. Redirects authenticated users straight to dashboard.

### `dashboard_view`
The main analytics page.
- Month/year navigation via `?month=&year=` query params
- Custom date range via `?start_date=&end_date=`
- Category filter via `?filter_cat=`
- Computes: total spend, balance, savings rate, financial health label/tip
- Previous month comparison → `savings_delta`
- Category breakdown (Chart.js doughnut)
- Daily spending (Chart.js line chart)
- Top 5 categories list
- Recent 5 expenses
- **Spending Forecast** — only shown for current month (not custom range, not past months). Uses daily average × days in month to project end-of-month spend. Three statuses: `good` (purple), `warning` (amber), `danger` (rose-red)
- **Product Tour** — passes `show_tour` flag if `onboarding_complete=False`

### `tour_complete`
POST-only endpoint at `/tour-complete/`. Sets `onboarding_complete=True` on `UserProfile`. Returns JSON `{ok: true}`.

### `export_data`
GET → renders filter page (`export.html`).
POST → generates and streams a UTF-8 BOM CSV file.
- Three date filter modes: Custom Range, Month/Year, Full Year
- Data type checkboxes: Expenses, Income, Savings Goals, Subscriptions
- Category multi-select (for expenses)
- UTF-8 BOM (`\ufeff`) ensures correct rendering in Excel

### `profile`
Handles three POST actions via `action` field:
- `avatar` — uploads new avatar image, deletes old file from disk
- `remove_avatar` — deletes avatar file and clears field
- default — updates `first_name`, `last_name`, `username`, `email`

### `settings` → redirects to `settings_income`

### `settings_income`
Lists income entries with filters (date range, source search). Shows total amount and record count.

### `income_add`, `income_edit`, `income_delete`
Standard CRUD for `Income` model. All redirect back to `settings_income` with toast messages.

### `settings_categories`
Add/delete custom categories. Validates against duplicates and default category names.

### `settings_budget`
Month/year navigable budget management.
- Saves `CategoryBudget` per category per month/year
- Computes spent vs limit per category → status: `ok` / `warning` (≥80%) / `danger` (≥100%)
- Computes total budget goal and total spent summary row

### `settings_upload`
CSV import for expenses.
- Two-step: preview (stores decoded CSV in session) → import
- Validates required columns: `title`, `category`, `amount`, `date`
- Invalid categories fall back to `'Other'`
- Shows first 5 rows as preview before confirming import

### `subscriptions`
Lists all subscriptions. Auto-advances overdue billing dates on page load. Shows monthly/yearly totals, active count, upcoming billing count (within 7 days).

### `subscription_add`, `subscription_edit`, `subscription_delete`
CRUD for `Subscription`. Add view separates creation from billing advance — billing advance failure is silently ignored so it doesn't affect the success toast.

### `savings_goals`
Lists all savings goals with total saved summary.

### `savings_goal_add`, `savings_goal_edit`, `savings_goal_delete`
CRUD for `SavingsGoal`.

### `savings_goal_detail`
Shows goal progress and full contribution history timeline.

### `savings_goal_add_funds`
Deposits funds into a goal:
1. Validates `amount > 0` (shows error toast if not)
2. Increments `goal.saved`
3. Creates a `SavingsContribution` record
4. Creates an `Expense` with category `'Savings'`

---

## Dashboard App — Templates & UI Components

### `base.html`
Global layout shell.
- Includes navbar, footer, Bootstrap 5 CSS/JS, Bootstrap Icons, Inter font, custom CSS/JS
- Toast container — renders Django `messages` framework toasts, auto-dismiss after 3.5s with slide-in animation
- Theme toggle script — persists `light`/`dark` in `localStorage`, applies `data-theme` attribute on `<html>`
- Dynamic category colour script — assigns palette colours to unknown/custom category badges at runtime

### `navbar.html`
- Brand logo + name
- Nav links: Dashboard, Expenses, Subscriptions, Savings Goals, Settings
- User avatar (or initials fallback) with dropdown: Profile, Export Data, Change Password, Logout
- Theme toggle button (moon/sun icon)
- Responsive collapse for mobile

### `footer.html`
Simple footer with brand name and copyright.

### `landing.html`
Public marketing page shown to unauthenticated users. Links to Register and Login.

### `dashboard/dashboard.html`
Main dashboard page. Key sections:
- Month/year navigation bar with prev/next arrows and dropdowns
- Custom date range filter + category filter
- Summary cards: Total Spent, Balance, Savings Rate (with delta vs prev month), Financial Health
- Category breakdown doughnut chart (Chart.js)
- Daily spending line chart (Chart.js)
- Top 5 categories list with coloured badges
- Recent 5 expenses table
- **Spending Forecast card** — projected spend, daily average, days left, progress bar, status-coloured theme
- **Product Tour** — JS tooltip-based overlay tour (5 steps), fires POST to `/tour-complete/` on completion

### `dashboard/settings.html`
Multi-section settings page controlled by `section` context variable. Sections:
- **Income** — filterable table, add/edit/delete modals
- **Categories** — default category chips, custom category add/delete
- **Budget** — month-navigable budget cards per category with progress bars and status colours
- **Upload** — CSV upload with preview step

### `dashboard/subscriptions.html`
Subscription tracker with summary stats, add/edit/delete modals, status badges, due-soon highlighting.

### `dashboard/savings_goals.html`
Goal cards with circular icon, progress bar, Add Funds button, edit/delete. Icon picker modal with preset grid + custom Bootstrap Icons input with live preview.

### `dashboard/savings_goal_detail.html`
Goal detail page: progress ring, stats, deposit form, contribution history timeline.

### `dashboard/profile.html`
Profile page: avatar upload/remove, edit name/username/email, link to Export Data page.

### `dashboard/export.html`
Export data page with three filter modes (Custom Range, Month/Year, Full Year), data type checkboxes, category multi-select, download button.

### `expenses/expense_list.html`
Expense list with month/year navigation, search, category multi-filter, custom date range, bulk delete checkboxes, total and count summary.

### `expenses/expense_form.html`
Add/Edit expense form. Inline JS warning shown when category is `'Savings'` or `'Subscription'` — links user to the relevant page.

### `expenses/expense_confirm_delete.html`
Simple delete confirmation page.

### `accounts/auth.html`
Single template for Register, Login, and Change Password — switches content based on `page_type` context variable.

---

## Frontend — `static/css/styles.css`

Custom CSS built on top of Bootstrap 5. Key sections:
- CSS custom properties (`--bg`, `--card`, `--text`, `--border`, `--accent`) for light/dark theming
- `[data-theme="dark"]` overrides for all components
- Dashboard summary cards (`.db-card`)
- Expense list styles (`.el-*`)
- Expense form styles (`.ef-*`, `.ef-warn` — category warning banner)
- Budget card styles (`.bc-*`) — accent border, hover lift, status colours
- Savings goal card styles (`.sg-*`)
- Subscription styles
- Forecast card styles (`.fc-*`) — gradient top border, status-coloured icon box and progress bar
- Toast notification styles (`.ft-toast*`) — slide-in animation, colour variants, dark mode, mobile full-width
- Product tour styles (`.tour-*`) — spotlight overlay, popover
- Mobile responsive breakpoints at 991px, 768px, 480px — touch targets min 44px, horizontal scroll on tables

## Frontend — `static/js/filters.js`
Client-side filter helpers for the expense list page (category multi-select, search, date range interactions).

---

## Admin Panel — `dashboard/admin.py`

Custom `FinTrackUserAdmin` extends Django's `BaseUserAdmin`:
- All user data shown as inlines on the User detail page (not separate list pages)
- Inlines: `UserProfileInline` (stacked), `IncomeInline`, `ExpenseInline`, `CategoryBudgetInline`, `SubscriptionInline`, `SavingsGoalInline`, `CustomCategoryInline` (all tabular)
- Income/Expense/Subscription/SavingsGoal inlines are read-only (no accidental edits)
- Actions: `deactivate_users`, `activate_users` (deactivate skips superusers)
- User list columns: `username`, `email`, `date_joined`, `last_login`, `is_active`
- Default ordering: `date_joined` ascending

`expenses/admin.py` — only sets site header/title/index_title. No separate Expense registration (all shown under User).

---

---

# MoSCoW Prioritisation

## M — Must Have
*Core features without which the application cannot function as a personal finance tracker.*

| # | Feature | Description |
|---|---|---|
| M1 | User Registration & Login | `MyUserCreationForm`, `LoginForm`, Django `authenticate`/`login`. Required to scope all data per user. |
| M2 | Logout | `logout_view` — clears session, redirects to login. |
| M3 | Expense CRUD | Add, edit, delete individual expenses with title, category, amount, date. Core data entry. |
| M4 | Expense List with Filters | Month/year navigation, search by title, filter by category, custom date range. |
| M5 | Dashboard — Spend Summary | Total spent, balance (income − spend), savings rate for the selected period. |
| M6 | Income Entry | Add/edit/delete income records. Without income, balance and savings rate are meaningless. |
| M7 | Category System | Default categories + user-defined custom categories merged at query time via `get_category_choices()`. |
| M8 | User-scoped Data | Every model has a `user` FK. Every view filters by `request.user`. No data leakage between users. |
| M9 | Django ORM & SQLite | Persistent storage. All models use `DecimalField` for monetary values to avoid float precision errors. |
| M10 | Base Template & Navigation | `base.html`, `navbar.html` — consistent layout, auth-aware nav links across all pages. |

---

## S — Should Have
*Important features that significantly improve usability but the app can technically run without them.*

| # | Feature | Description |
|---|---|---|
| S1 | Budget Limits per Category | `CategoryBudget` model. Per-month, per-category spending limits with progress bars and warning/danger status. |
| S2 | Subscription Tracker | `Subscription` model with billing cycle, auto-advance of `next_billing`, automatic `Expense` creation per elapsed cycle. |
| S3 | Savings Goals | `SavingsGoal` + `SavingsContribution`. Target, progress bar, deposit form, contribution history timeline. |
| S4 | Spending Forecast | Projects end-of-month spend from daily average. Only shown for current month. Three statuses: good/warning/danger. |
| S5 | Financial Health Indicator | Savings rate bucketed into Excellent/Good/Fair/Over Budget with colour and tip text. |
| S6 | Previous Month Comparison | `savings_delta` — difference in savings rate vs prior month shown on dashboard. |
| S7 | Toast Notifications | Django `messages` framework rendered as auto-dismissing slide-in toasts. All CRUD actions produce feedback. |
| S8 | Dark Mode | CSS custom properties + `data-theme="dark"` toggle. Persisted in `localStorage`. Full dark mode coverage across all components. |
| S9 | Profile Page | Edit name, username, email. Avatar upload/remove with old file cleanup. |
| S10 | Change Password | `ChangePasswordForm` — username lookup + new password with confirmation. Accessible from navbar dropdown. |
| S11 | Bulk Delete Expenses | Checkbox selection + bulk delete POST action on expense list. |
| S12 | Category Warning on Expense Form | Inline JS warning when user picks `'Savings'` or `'Subscription'` category — links to the correct dedicated page. |

---

## C — Could Have
*Nice-to-have features that improve the experience but are lower priority.*

| # | Feature | Description |
|---|---|---|
| C1 | Product Tour | JS tooltip-based 5-step tour on first login. Spotlight overlay + popover. Completion POSTs to `/tour-complete/`. |
| C2 | Export Data Page | Full filter page — Custom Range / Month-Year / Full Year, data type checkboxes, category filter. Downloads UTF-8 BOM CSV (Excel-compatible). |
| C3 | CSV Import (Upload Data) | Two-step preview → import flow. Validates columns, maps invalid categories to `'Other'`. |
| C4 | Chart.js Visualisations | Doughnut chart (category breakdown) + line chart (daily spending) on dashboard. Data passed via `data-` attributes to avoid Django tags in `<script>` blocks. |
| C5 | Month/Year Navigation | Prev/next arrows + dropdown selectors on dashboard, expense list, and budget settings. |
| C6 | Top 5 Categories | Ranked list of highest-spend categories for the selected period. |
| C7 | Recent Expenses Widget | Last 5 expenses shown on dashboard for quick reference. |
| C8 | Subscription Monthly/Yearly Cost Summary | `monthly_cost` property normalises weekly/yearly cycles. Total monthly and yearly cost shown on subscriptions page. |
| C9 | Savings Goal Icon Picker | Preset icon grid (10 Bootstrap Icons) + custom icon input with live preview in the add/edit modal. |
| C10 | Admin Panel — User-Centric Inlines | All user data (income, expenses, budgets, subscriptions, goals) shown as read-only inlines on the User admin page. Activate/deactivate user actions. |
| C11 | Mobile Responsive Design | Breakpoints at 991px, 768px, 480px. Touch targets ≥44px. Horizontal scroll on tables. Stacked layouts on small screens. |
| C12 | Dynamic Category Colours | Runtime JS assigns palette colours to unknown/custom category badges that don't have predefined CSS classes. |
| C13 | Avatar Upload | `ImageField` on `UserProfile`. Old file deleted from disk on replacement or removal. Shown in navbar. |

---

## W — Won't Have (for now)
*Features that are out of scope for this version of the project.*

| # | Feature | Reason |
|---|---|---|
| W1 | Email Verification on Register | No email backend configured. Would require SMTP setup. |
| W2 | Password Reset via Email | Same — no email backend. Change password is done by username lookup only. |
| W3 | Multi-currency Support | All amounts are stored as plain decimals. No currency conversion logic. |
| W4 | Recurring Expense Rules | Subscriptions auto-create expenses, but general recurring expenses (e.g. rent) have no automation. |
| W5 | Notifications / Reminders | No push/email notifications for upcoming subscription billing or budget overruns. |
| W6 | Data Sharing / Multi-user Households | All data is strictly per-user. No shared budgets or household accounts. |
| W7 | Bank / API Integration | No Plaid, Open Banking, or any external financial data source integration. |
| W8 | Production Deployment Config | `DEBUG=True`, `SECRET_KEY` is hardcoded, `ALLOWED_HOSTS=[]`. Not production-ready. |
| W9 | Automated Tests | `tests.py` files exist in all apps but are empty. No unit or integration tests written. |
| W10 | Pagination | Expense list and income list load all records for the selected period with no pagination. |
| W11 | PDF Export | Only CSV export is supported. No PDF reports. |
| W12 | Two-Factor Authentication | No 2FA support. |

---

## Summary Table

| Priority | Count | Key Theme |
|---|---|---|
| Must Have | 10 | Auth, expense CRUD, income, categories, data scoping |
| Should Have | 12 | Budgets, subscriptions, savings, forecast, UX polish |
| Could Have | 13 | Charts, export, import, tour, admin, mobile, icons |
| Won't Have | 12 | Email, multi-currency, integrations, production hardening |
