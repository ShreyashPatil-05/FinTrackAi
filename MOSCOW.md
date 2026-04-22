# MoSCoW Analysis — FinTrack

MoSCoW is a prioritization framework used in software development to decide what gets built and when. Each feature is placed into one of four categories based on its importance to the product.



## Must Have

Core features. Without these, FinTrack does not work as a product.

| Feature | Status | Notes |
|---|---|---|
| User registration and login | ✅ Done | `accounts/views.py` — `register_view`, `login_view` |
| Expense add, edit, delete | ✅ Done | `expenses/views.py` — full CRUD including bulk delete |
| Dashboard with balance and totals | ✅ Done | `dashboard/views.py` — income, expenses, balance all shown |
| Category-based expense tracking | ✅ Done | Default 7 categories + custom categories per user |
| Income entry | ✅ Done | `Income` model with source choices; add/edit/delete in settings |
| Session management and logout | ✅ Done | `accounts/views.py` — `logout_view` |
| Responsive UI | ✅ Done | CSS-based responsive layout across all pages |



## Should Have

Important features that add real value but the app still functions without them.

| Feature | Status | Notes |
|---|---|---|
| Monthly budget limits per category | ✅ Done | `CategoryBudget` model; per-category, per-month limits with progress tracking |
| Savings goals with progress tracking | ✅ Done | `SavingsGoal` + `SavingsContribution` models; detail view, add-funds flow |
| Subscription tracker with auto-billing | ✅ Done | `Subscription` model; weekly/monthly/yearly cycles; auto-advances billing date on overdue subs |
| CSV import | ✅ Done | `settings_upload` view; preview + validate + import with skip-log |
| CSV export | ✅ Done | `export_data` view; exports expenses, income, savings goals, subscriptions |
| Budget alerts on dashboard | ✅ Done | `budget_alerts` injected into dashboard context at 80% and 100% of limit |
| Dark mode | ✅ Done | Toggle implemented in UI |
| Month-end spending forecast | ✅ Done | `forecast` dict computed in `dashboard_view` based on daily average |



## Could Have

Nice-to-have features that improve polish and experience.

| Feature | Status | Notes |
|---|---|---|
| Google OAuth login | ✅ Done | `django-allauth` — `allauth.socialaccount.providers.google`; PKCE enabled; "Continue with Google" button on login/register page |
| Email verification on registration | ✅ Done | `EmailVerificationToken` model; user set `is_active=False` until link is clicked |
| Onboarding tour for new users | ✅ Done | `UserProfile.onboarding_complete` flag; `tour_complete` API endpoint |
| Indian currency formatting (₹) | ✅ Done | ₹ formatting used throughout dashboard, budgets, forecasts |
| Contribution history on savings goals | ✅ Done | `savings_goal_detail` view shows last 3 contributions + total count |
| Copy budget from last month | ✅ Done | `budget_copy_last_month` view copies all limits from previous month |
| Financial health score | ✅ Done | Savings rate → Excellent / Good / Fair / Over Budget label + colour + tip |
| Pagination with per-page selector | ✅ Done | `expense_list` — paginated with 10/20/50 per-page selector |
| Profile avatar upload | ✅ Done | `UserProfile.avatar` field; upload and remove via profile page |
| Account deletion | ✅ Done | `delete_account` view — requires password confirmation, logs out and deletes the user row |
| Per-user webhook token | ✅ Done | `WebhookToken` model — token bound to user, regeneratable, no cross-user posting |
| Avatar file validation | ✅ Done | Magic bytes check for real image type + 2MB size limit |
| Email token expiry | ✅ Done | Verification tokens expire after 24 hours |
| never_cache on edit views | ✅ Done | Prevents stale form data on browser back button |



## Won't Have

Out of scope for this version. Identified as future upgrades.

| Feature | Reason |
|---|---|
| Real bank API integration | Requires RBI-approved fintech licensing in India — a per-user webhook token system + simulator (`mock_bank_simulator.py`) is included instead, demonstrating the full architecture with proper token binding |
| Mobile app (Android or iOS) | Needs React Native or Flutter — separate project |
| Celery and Redis for background tasks | Infrastructure overhead not justified at this scale; subscription auto-advance runs synchronously on page load |
| Multi-user household budgeting | Requires shared data model redesign |
| AI-based spending insights | Needs ML pipeline and sufficient historical data |
| PostgreSQL migration | SQLite is sufficient for single-user deployment |
| Payment gateway integration | Out of scope for a tracking app |
| Real-time notifications | Requires WebSockets or push notification service |

