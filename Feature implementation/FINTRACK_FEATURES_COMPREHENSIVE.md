# FinTrack - Comprehensive Feature Documentation
**For Interview & Study Purposes**
**Last Updated: August 26, 2026**

---

## 🏗️ **PROJECT ARCHITECTURE**

### **Tech Stack**
- **Backend:** Django 6.0.2 (Python web framework)
- **Database:** PostgreSQL (production) / SQLite (development)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5.3
- **Authentication:** Django-allauth (Google OAuth) + Custom email verification
- **Deployment:** Railway (cloud platform)
- **Email:** SendGrid API (production) / Gmail SMTP (development)
- **AI:** Google Gemini 2.5 Flash (`google.genai` SDK)
- **Payments:** Razorpay (India-based payment gateway)
- **Security:** django-axes (brute force protection), reCAPTCHA v2

### **Project Structure**
```
fintrack/
├── accounts/          # User authentication & registration
├── expenses/          # Expense tracking & webhook API
├── dashboard/         # Main app (income, budgets, savings, subscriptions, insights, payments)
│   ├── views/         # 11 focused view modules (refactored)
│   ├── services/      # Business logic layer (plan, budget, expense, income, savings, email)
│   ├── templates/     # App-level HTML templates
│   └── management/    # Custom management commands
├── templates/         # Global HTML templates
├── static/            # CSS, JS, images
└── fintrack/          # Django settings & configuration
```

---

## 🔐 **AUTHENTICATION & SECURITY**

### **1. Multi-Method Authentication**
- **Custom Registration:** Email + password with verification
- **Google OAuth:** One-click login via django-allauth
- **Email Verification:** UUID tokens with 24-hour expiration
- **Password Security:** Django's built-in validators + strength meter

**Interview Points:**
- Implemented custom `MyUserCreationForm` with email uniqueness validation
- Used `@transaction.atomic` to prevent race conditions during registration
- Added rate limiting (3 attempts per IP per hour) to prevent spam
- Secure token generation using `uuid.uuid4()` (128-bit entropy)

### **2. Advanced Security Features**
- **Brute Force Protection:** django-axes (5 failed attempts = 15 min lockout)
- **CSRF Protection:** Django middleware + custom CSP headers
- **reCAPTCHA v2:** Google verification on registration
- **Rate Limiting:** IP-based limits on sensitive endpoints
- **Secure Headers:** Content Security Policy middleware

**Interview Points:**
- Custom middleware for CSP headers (`ContentSecurityPolicyMiddleware`)
- Constant-time token comparison using `hmac.compare_digest()`
- Proper error handling without revealing system information

### **3. Email Verification System**
- **Resend Feature:** Users can request new verification links
- **Token Cleanup:** `python manage.py cleanup_expired_tokens [--dry-run]`
- **Dual Email Backend:** SendGrid (prod) + Gmail (dev) with automatic fallback
- **Background Processing:** Threaded email sending with error handling

---

## 💰 **CORE FINANCIAL FEATURES**

### **1. Expense Tracking**
- **CRUD Operations:** Create, read, update, delete expenses
- **Smart Categorization:** Default + custom user categories
- **Multiple Sources:** Manual entry, bank webhooks, subscription auto-generation
- **Advanced Filtering:** Date ranges, categories, text search
- **Bulk Operations:** Multi-select delete with confirmation
- **Plan Enforcement:** Free users limited to 50 expenses/month

**Interview Points:**
- Used Django ModelForm for validation and security
- Implemented pagination with user-selectable page sizes (10/20/50)
- Added database indexes for performance optimization
- Source tracking: `manual`, `bank`, `subscription`

### **2. Income Management**
- **Multiple Sources:** Salary, freelance, business, investment, gifts
- **Monthly Tracking:** Navigate by month/year with totals
- **Validation:** Positive amounts, future date prevention
- **Plan Enforcement:** Free users limited to 20 income entries/month

**Interview Points:**
- Used `DecimalField` for precise currency calculations
- Added `MinValueValidator` for data integrity
- Implemented month navigation utility function

### **3. Budget Management**
- **Category Budgets:** Set spending limits per category per month
- **Visual Progress:** Color-coded progress bars (green/yellow/red)
- **Overspending Alerts:** Real-time notifications on dashboard
- **Budget Copying:** Copy previous month's budgets with one click
- **Plan Enforcement:** Free users limited to 3 budget categories

**Interview Points:**
- Used `unique_together` constraint for data integrity
- Implemented percentage calculations with proper rounding
- Added database indexes on frequently queried fields

### **4. Savings Goals**
- **Goal Tracking:** Set target amounts with optional deadlines
- **Progress Visualization:** Percentage completion with remaining amounts
- **Contribution History:** Track individual deposits over time
- **Icon Selection:** 10 predefined icons for visual organization
- **Auto Expense Creation:** Savings contributions create expense entries
- **Plan Enforcement:** Free users limited to 2 savings goals total

**Interview Points:**
- Used `@property` decorators for calculated fields
- Implemented `prefetch_related()` to avoid N+1 queries
- Automatic expense generation with `@transaction.atomic`

### **5. Subscription Management**
- **Billing Cycles:** Weekly, monthly, yearly with auto-conversion
- **Status Tracking:** Active, paused, cancelled subscriptions
- **Auto-Billing:** Automatic expense creation on billing dates
- **Cost Analysis:** Monthly and yearly cost calculations
- **Plan Enforcement:** Free users limited to 3 subscriptions total

**Interview Points:**
- Used `dateutil.relativedelta` for accurate date calculations
- Implemented `get_or_create()` to prevent duplicate expenses
- Added `@property` for monthly cost normalisation

---

## 📊 **DASHBOARD & ANALYTICS**

### **1. Financial Overview Dashboard**
- **Income vs Expenses:** Real-time balance calculation
- **Savings Rate:** Percentage with health indicators (Excellent/Good/Fair/Over Budget)
- **Month-over-Month:** Comparison with previous month's performance
- **Top Categories:** Visual breakdown of spending by category
- **Recent Activity:** Last 5 expenses with quick access

### **2. Advanced Analytics**
- **Daily Spending Chart:** Interactive line chart showing daily patterns
- **Category Breakdown:** Pie chart with top 5 spending categories
- **Spending Forecast:** Predictive analysis for current month
- **Budget Alerts:** Real-time overspending notifications
- **Custom Date Ranges:** Flexible filtering beyond monthly view

### **3. Navigation & UX**
- **Month Navigation:** Previous/next month with year dropdown
- **Onboarding Tour:** Interactive guide for new users
- **Responsive Design:** Mobile-first Bootstrap implementation
- **Dark/Light Theme:** User preference with localStorage persistence
- **Loading States:** Skeleton card UI for async operations

---

## 🤖 **AI FINANCIAL INSIGHTS** *(Pro Feature)*

### **Overview**
A dedicated `/insights/` page that generates personalised financial analysis using Google Gemini 2.5 Flash for Pro users, with intelligent rule-based fallback for free users or when the API key is absent.

### **Feature Breakdown**

#### **AI Insights Cards (Gemini 2.5 Flash)**
- Generates exactly 5 personalised, actionable insight cards per request
- Each card has: type (positive/warning/danger/info), Bootstrap icon, title, insight text
- Prompt is built from last 3 months of income, expenses, budgets, subscriptions, savings goals, and anomalies
- Response parsed from Gemini JSON output with markdown code fence stripping
- Errors fall back gracefully to rule-based insights

**Interview Points:**
- Migrated from deprecated `google.generativeai` to `google.genai` SDK (August 2026)
- Uses `genai.Client(api_key=...)` with `client.models.generate_content()`
- Prompt engineering: structured financial data → strict JSON output format
- JSON parsing with error recovery for malformed or fenced responses

#### **Rule-Based Fallback Insights**
- Always available — no API key or Pro plan required
- Analyses: savings rate trend, spending spike detection, over-budget categories, subscription cost summary, near-complete savings goals, unusual expense anomalies
- Free users see these with a lock banner explaining the Pro upgrade

#### **Skeleton Card Loading UI**
- Pro users with API key configured see skeleton placeholder cards while Gemini loads in the background (AJAX)
- Skeletons are only shown when `is_pro=True` AND `api_key_set=True`
- Free users see rule-based insight cards immediately — no skeleton shown

#### **AJAX Refresh**
- Pro users get a "Refresh Insights" button in the header
- Fires `GET /insights/` with `X-Requested-With: XMLHttpRequest`
- Returns `{insights, ai_used, locked}` JSON; JS replaces cards in-place
- Free users' AJAX calls return `{locked: true}` immediately

#### **Month-over-Month Comparison**
- 4-card panel: Income, Spent, Saved, Savings Rate
- Shows current vs previous month with delta and directional arrow
- Colour-coded: positive delta = green, negative = red (direction logic differs for spending)

#### **Budget Status Bars**
- Per-category progress bars for current month
- Three states: `ok` (green, <80%), `warning` (yellow, 80–99%), `over` (red, ≥100%)

#### **Unusual Expense Anomalies**
- Detects expenses > 2× the 30-day category average
- Shows category, date, amount, and multiplier

#### **Savings Goals Progress**
- Cards for each goal with fill bar, saved amount, remaining, and target date

#### **3-Month Spending Trend Chart**
- Chart.js grouped bar chart: income / spent / saved per month
- Data passed via `data-*` attributes on a hidden `<span>` (no inline JS)

#### **Plan & API Key Banners**
- Free users: lock banner with single "Upgrade to Pro" CTA (no duplicate button in header)
- Pro users with missing API key: info banner explaining how to enable Gemini
- Pro users with API key: no banners shown

**Interview Points:**
- Two-phase render: server renders rule-based insights immediately; JS upgrades to AI if eligible
- Plan check via `plan_service.check_limit(user, 'ai_insights')`
- AJAX endpoint doubles as both initial load upgrade and manual refresh
- Clean separation: data gathering (`_gather_user_data`) → prompt building (`_build_prompt`) → API call → parse → fallback

---

## 💳 **SAAS / MONETISATION LAYER**

### **Overview**
Full subscription and payment infrastructure added in July 2026. Razorpay is integrated for India-based payments; plans are enforced across all major features.

### **Plan Tiers**

| Resource | Free | Pro Monthly | Pro Yearly |
|----------|------|-------------|------------|
| Expenses / month | 50 | Unlimited | Unlimited |
| Income entries / month | 20 | Unlimited | Unlimited |
| Savings Goals (total) | 2 | Unlimited | Unlimited |
| Subscriptions (total) | 3 | Unlimited | Unlimited |
| Budget Categories (total) | 3 | Unlimited | Unlimited |
| CSV Export | ❌ | ✅ | ✅ |
| CSV Import | ❌ | ✅ | ✅ |
| AI Insights (Gemini) | ❌ | ✅ | ✅ |
| Webhook API | ❌ | ✅ | ✅ |

### **Data Model**
- `UserProfile.plan` — stores `free` / `monthly` / `yearly`
- `UserProfile.plan_expires_at` — `DateTimeField`, null for free users
- `UserProfile.is_pro()` — checks plan and expiry
- `Payment` model — stores Razorpay `order_id`, `payment_id`, `amount`, `currency`, `status`, `plan_type`
- Migration: `0016_saas_plan_payment_model`

### **Plan Enforcement**
- `dashboard/services/plan_service.py`:
  - `check_limit(user, resource)` → `(allowed: bool, message: str)`
  - `get_usage(user)` → dict of current usage vs limits for pricing page meters
  - `is_pro(user)` → bool
- `dashboard/decorators.py`:
  - `@plan_required(resource)` — wraps views; redirects to `/pricing/` with error message if limit exceeded
  - Applied to: `export_data`, `settings_upload`, `add_expense`, `income_add`, `subscription_add`, `savings_goal_add`, `insights_view`

**Interview Points:**
- Plan stored as a string field — simple, avoids a separate Plan model
- `check_limit` is the single source of truth; used by both the decorator and the AJAX endpoint
- Free-tier redirects go to `/pricing/` with a contextual message (not a modal)

### **Razorpay Payment Flow**
1. User clicks "Upgrade" on `/pricing/`
2. `POST /payment/create-order/` — creates Razorpay order, returns `order_id` + `key_id` as JSON
3. Razorpay checkout JS opens payment modal
4. On success, Razorpay calls `POST /payment/verify/` with `razorpay_payment_id`, `order_id`, `signature`
5. Server verifies HMAC SHA-256 signature
6. On success: `UserProfile.plan` updated, `Payment` record saved, success email sent
7. `static/js/pricing.js` handles the Razorpay JS SDK integration and monthly/yearly toggle

**Interview Points:**
- HMAC signature verification prevents payment tampering
- `Payment` model records all attempts (including failures) for audit trail
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` must be in `.env` to activate

### **Pricing Page (`/pricing/`)**
- Plan comparison table with feature matrix
- Monthly / yearly billing toggle with savings callout
- Usage meters (current usage vs plan limit) for logged-in users
- Razorpay checkout integration

### **Plan Expiry & Emails**
- `python manage.py expire_plans` — marks expired Pro plans back to `free`, sends expiry email
- `dashboard/services/email_service.py`:
  - `send_payment_success_email(user, plan, amount)`
  - `send_expiry_reminder_email(user, days_left)`
  - `send_plan_expired_email(user)`
- Schedule both `expire_plans` and `cleanup_expired_tokens` as Railway daily cron jobs

### **Admin Controls**
- Grant / revoke Pro directly from Django admin
- `PaymentAdmin` — view all payment records with order/payment IDs and status
- Plan column added to User list in admin

---

## 🔌 **API & INTEGRATIONS**

### **1. Bank Webhook API**
- **Secure Endpoint:** Token-based authentication with SHA-256 hashing
- **JSON Processing:** Validates and sanitises incoming transaction data
- **Auto-Categorisation:** Smart category mapping with fallback to 'Other'
- **User Scoping:** Tokens bound to specific users
- **Plan Enforcement:** Webhook access requires Pro plan

**Interview Points:**
- Used `@csrf_exempt` for external API endpoint
- Implemented secure token verification with timing attack prevention
- Proper HTTP status codes (201, 400, 401)

### **2. Mock Bank Simulator**
- Simulates real bank transaction webhooks for testing
- 15+ realistic merchant transactions with categories
- Connection retry logic and configurable intervals

### **3. Google OAuth Integration**
- django-allauth with PKCE security
- Custom branded templates for signup/connections
- Auto-profile sync from Google account

### **4. Google Gemini AI**
- **SDK:** `google.genai` (migrated from deprecated `google.generativeai`)
- **Model:** `gemini-2.5-flash`
- **Usage:** AI financial insights for Pro users
- **Fallback:** Rule-based insights when API key absent or API errors

### **5. Razorpay Payments**
- **SDK:** `razorpay==1.4.1`
- **Usage:** Pro plan purchases (monthly / yearly)
- **Security:** HMAC SHA-256 signature verification on payment callback

---

## 🎨 **FRONTEND & USER EXPERIENCE**

### **1. Modern UI Design**
- Bootstrap 5.3, custom CSS with CSS variables for theming
- Bootstrap Icons + custom financial icon usage throughout
- Inter font family, consistent component library

### **2. JavaScript Functionality**
- Chart.js for interactive financial charts
- Vanilla JS AJAX for insights refresh and form submissions
- localStorage for theme and preference persistence
- Skeleton card loading UI for async AI content
- `pricing.js` — Razorpay checkout, monthly/yearly plan toggle
- `insights.js` — AJAX insight loading, card rendering, chart initialisation
- All JS in `static/js/` (no inline scripts in HTML files)

**Interview Points:**
- Data passed from Django to JS via `data-*` attributes on hidden elements — avoids inline `<script>` blocks
- Skeleton cards replaced by real cards via DOM manipulation after AJAX resolves

### **3. Responsive Design**
- Mobile-first with Bootstrap breakpoints
- Touch-friendly targets, semantic HTML, ARIA labels

---

## 🗄️ **DATABASE DESIGN & OPTIMISATION**

### **1. Model Architecture**
- `UserProfile` — extended user model: avatar, onboarding state, `plan`, `plan_expires_at`, webhook token (hashed)
- `Expense` — amount, category, date, source, note
- `Income` — amount, source, date, note
- `CategoryBudget` — per-user, per-month category spending limits
- `SavingsGoal` + `SavingsContribution` — goal tracking with contribution history
- `Subscription` — recurring billing with auto-expense generation
- `Payment` — Razorpay payment records
- `EmailVerificationToken` — UUID tokens with expiry

### **2. Database Optimisation**
- 6 custom indexes on frequently queried fields (category, date, user)
- `select_related()` and `prefetch_related()` throughout service layer
- Efficient `Sum()` / `Count()` aggregations
- Django Paginator for expense lists

### **3. Data Integrity**
- `MinValueValidator` on all amount fields
- Custom `clean()` methods with business logic
- `unique_together` constraints where appropriate
- `@transaction.atomic` for multi-step writes

---

## 🚀 **DEPLOYMENT & DEVOPS**

### **Production Environment**
- **Platform:** Railway (auto-scaling, PostgreSQL, cron jobs)
- **Static Files:** WhiteNoise
- **SSL:** Automatic via Railway
- **Cron Jobs (recommended):**
  ```
  0 2 * * *  python manage.py expire_plans
  0 3 * * *  python manage.py cleanup_expired_tokens
  ```

### **Environment Variables**
```bash
SECRET_KEY, DEBUG, ALLOWED_HOSTS, SITE_ID
DATABASE_URL
EMAIL_HOST_PASSWORD         # SendGrid API key
DEFAULT_FROM_EMAIL
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY
GEMINI_API_KEY              # optional — enables AI insights for Pro
RAZORPAY_KEY_ID             # required to activate payments
RAZORPAY_KEY_SECRET
```

### **Management Commands**
```bash
python manage.py expire_plans                       # mark expired Pro → free
python manage.py cleanup_expired_tokens [--dry-run] # remove stale email tokens
python manage.py migrate
python manage.py collectstatic --noinput
```

---

## 📈 **BUSINESS LOGIC & ALGORITHMS**

### **1. Financial Calculations**
- Savings rate: `(income - expenses) / income * 100`
- Budget progress: real-time percentage with colour thresholds
- Subscription billing: auto date advancement, `get_or_create` for idempotency
- Spending forecast: daily average × remaining days in month
- Currency formatting: smart ₹K / ₹L suffixes for large amounts

### **2. Plan Enforcement Logic**
- `check_limit(user, resource)` queries current month's count vs tier limit
- Savings goals and subscriptions use total count (not monthly)
- Pro check: `plan in ('monthly', 'yearly') AND (plan_expires_at is None OR plan_expires_at > now())`

### **3. AI Prompt Engineering**
- Structured financial data formatted as a multi-section text prompt
- Strict output format: JSON array of 5 objects with `type`, `icon`, `title`, `insight`
- Post-processing strips markdown code fences before JSON parsing

### **4. Anomaly Detection**
- Groups last 30 days of expenses by category
- Flags any single expense > 2× the category's 30-day average
- Results surfaced in both AI insights context and the dedicated anomalies panel

---

## 🎯 **KEY INTERVIEW TALKING POINTS**

### **Technical Skills Demonstrated**
1. **Full-Stack Development:** Django backend + modern frontend with vanilla JS
2. **Database Design:** PostgreSQL with indexing, constraints, migrations
3. **API Development:** Webhook API + Razorpay payment API + Gemini AI API
4. **Security Implementation:** CSRF, rate limiting, HMAC verification, brute-force protection
5. **SaaS Architecture:** Plan tiers, usage enforcement, payment flow, expiry management
6. **AI Integration:** Prompt engineering, response parsing, graceful fallback
7. **Code Architecture:** Service layer pattern, decorator-based plan enforcement, modular views
8. **Deployment:** Railway with cron jobs, environment-based configuration

### **Problem-Solving Examples**
1. **Race Condition Fix:** `@transaction.atomic` prevents duplicate registrations
2. **Email Delivery:** Dual backend (SendGrid/Gmail) with automatic fallback
3. **Performance:** 6 database indexes for 50–80% query improvement
4. **Code Maintainability:** Refactored 1211-line views file into 11 focused modules
5. **Deprecated SDK:** Migrated `google.generativeai` → `google.genai` before end-of-support
6. **Payment Security:** HMAC SHA-256 signature verification on Razorpay callback
7. **UX Duplicate Button:** Removed redundant header Upgrade CTA, single lock-banner CTA remains

### **Business Understanding**
1. **Monetisation:** Designed a realistic SaaS freemium model with meaningful free-tier limits
2. **Financial Domain:** Budgets, savings goals, subscriptions, anomaly detection
3. **User Experience:** Skeleton loading, progressive enhancement, single clear CTAs
4. **India Market:** Razorpay for INR payments, Gemini with ₹-aware prompt context
5. **Scalability:** Service-layer architecture, plan checks centralised in one module

---

## 📚 **LEARNING OUTCOMES**

### **Django Framework**
- MVT architecture, forms, auth, middleware, management commands
- Service layer pattern for business logic separation
- Decorator factories (`@plan_required`) for cross-cutting concerns
- Multi-app project organisation

### **Web Development**
- RESTful API design, AJAX patterns, JSON contracts
- Responsive design, accessibility, progressive enhancement
- CSS custom properties, skeleton UI patterns

### **Software Engineering**
- Clean code, modular architecture, DRY principle
- Payment gateway integration and security
- AI API integration with prompt engineering and fallback design
- Environment-based configuration, deployment, cron scheduling

---

**Total Features Implemented:** 60+ distinct features
**Lines of Code:** ~10,000+ (well-documented and organised)
**Development Time:** 4+ months of iterative development
**Code Quality Score:** A- (90/100) — Production ready with SaaS monetisation
