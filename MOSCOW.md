# MoSCoW Analysis — FinTrack

MoSCoW is a prioritization framework used in software development to decide what gets built and when. Each feature is placed into one of four categories based on its importance to the product.

---

## Must Have

Core features. Without these, FinTrack does not work as a product.

| Feature | Reason |
|---|---|
| User registration and login | No auth means no data separation between users |
| Expense add, edit, delete | The entire purpose of the app |
| Dashboard with balance and totals | Users need one view to see where they stand |
| Category-based expense tracking | Numbers without context are meaningless |
| Income entry | Balance requires both income and expenses |
| Session management and logout | Basic security requirement |
| Responsive UI | Must work on desktop and mobile |

---

## Should Have

Important features that add real value but the app still functions without them.

| Feature | Reason |
|---|---|
| Monthly budget limits per category | Moves the app from observation to control |
| Savings goals with progress tracking | Gives users a target to work toward |
| Subscription tracker with auto-billing | Recurring costs are the most overlooked spending |
| CSV import | Users have data elsewhere and need a way to bring it in |
| CSV export | Users should own and be able to extract their data |
| Budget alerts on dashboard | Warns users before they overspend, not after |
| Dark mode | Expected in any modern web app |
| Month-end spending forecast | Helps users act before the month ends |

---

## Could Have

Nice-to-have features that improve polish and experience.

| Feature | Reason |
|---|---|
| Google OAuth login | Reduces signup friction |
| Email verification on registration | Adds security without blocking core usage |
| Onboarding tour for new users | Reduces confusion on first login |
| Indian currency formatting | Better UX for the target audience |
| Contribution history on savings goals | Adds transparency to the savings flow |
| Copy budget from last month | Saves time for repeat users |
| Financial health score | Motivational indicator based on savings rate |
| Pagination with per-page selector | Performance improvement for power users |
| Profile avatar upload | Personalization |
| Account deletion | Data privacy control |

---

## Won't Have

Out of scope for this version. Identified as future upgrades.

| Feature | Reason |
|---|---|
| Real bank API integration | Requires RBI-approved fintech licensing in India |
| Mobile app (Android or iOS) | Needs React Native or Flutter — separate project |
| Celery and Redis for background tasks | Infrastructure overhead not justified at this scale |
| Multi-user household budgeting | Requires shared data model redesign |
| AI-based spending insights | Needs ML pipeline and sufficient historical data |
| PostgreSQL migration | SQLite is sufficient for single-user deployment |
| Payment gateway integration | Out of scope for a tracking app |
| Real-time notifications | Requires WebSockets or push notification service |

---

## How to explain this in an interview

The interviewer is checking whether you understand prioritization and trade-offs.

A good answer sounds like this:

"I used MoSCoW to decide what to build first. The Must Haves were the auth system and expense tracking — without those the app has no purpose. The Should Haves like budget limits and savings goals were built next because they move the app from just showing data to actually helping users make decisions. Features like Google OAuth and email verification were Could Haves — they improve security and UX but the app works without them. Things like a real bank API or mobile app were Won't Haves for this version because they require infrastructure and licensing that are out of scope for an academic project, but I have documented them as the natural next step."
