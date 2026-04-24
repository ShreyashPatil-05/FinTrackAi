# Dashboard Views Refactoring Plan

## Problem
`dashboard/views.py` is 1200+ lines - violates Single Responsibility Principle

## Recommended Structure

```
dashboard/
├── views/
│   ├── __init__.py           # Import all views
│   ├── dashboard.py          # Main dashboard view
│   ├── profile.py            # Profile management
│   ├── income.py             # Income CRUD
│   ├── budget.py             # Budget management
│   ├── subscriptions.py      # Subscription tracking
│   ├── savings.py            # Savings goals
│   └── export.py             # Data export
├── services/
│   ├── __init__.py
│   ├── income_service.py     # Income business logic
│   ├── budget_service.py     # Budget calculations
│   └── subscription_service.py
├── models.py
├── urls.py
└── utils.py
```

## Benefits
- ✅ Each file < 200 lines
- ✅ Easy to test
- ✅ Easy to maintain
- ✅ Clear separation of concerns
- ✅ Multiple developers can work simultaneously

## Migration Steps

### Step 1: Create views package
```bash
mkdir dashboard/views
touch dashboard/views/__init__.py
```

### Step 2: Extract dashboard view
```python
# dashboard/views/dashboard.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Income, Expense
from ..utils import get_month_navigation

@login_required
def dashboard_view(request):
    # Move dashboard logic here
    pass
```

### Step 3: Update imports
```python
# dashboard/views/__init__.py
from .dashboard import dashboard_view
from .profile import profile, delete_account
from .income import settings_income, add_income, delete_income
from .budget import settings_budget
from .subscriptions import subscriptions
from .savings import savings_goals, savings_goal_detail
from .export import export_csv

__all__ = [
    'dashboard_view',
    'profile',
    'delete_account',
    'settings_income',
    'add_income',
    'delete_income',
    'settings_budget',
    'subscriptions',
    'savings_goals',
    'savings_goal_detail',
    'export_csv',
]
```

### Step 4: Update URLs
```python
# dashboard/urls.py
from .views import (
    dashboard_view,
    profile,
    # ... rest of imports
)
```

## Service Layer Pattern

### Before (Business logic in views):
```python
# dashboard/views.py
def settings_income(request):
    if request.method == 'POST':
        amount = Decimal(request.POST['amount'])
        # 50 lines of business logic here
        Income.objects.create(...)
```

### After (Business logic in services):
```python
# dashboard/services/income_service.py
class IncomeService:
    @staticmethod
    def create_income(user, date, amount, source):
        """Create income with validation"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return Income.objects.create(
            user=user,
            date=date,
            amount=amount,
            source=source
        )

# dashboard/views/income.py
from ..services.income_service import IncomeService

def settings_income(request):
    if request.method == 'POST':
        try:
            income = IncomeService.create_income(
                user=request.user,
                date=request.POST['date'],
                amount=Decimal(request.POST['amount']),
                source=request.POST['source']
            )
            messages.success(request, 'Income added.')
        except ValueError as e:
            messages.error(request, str(e))
```

## Priority: HIGH
## Effort: 4-6 hours
## Impact: Massive improvement in maintainability
