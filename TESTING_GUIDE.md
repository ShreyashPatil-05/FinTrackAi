# Testing Guide for FinTrack

## Current State
❌ No unit tests  
❌ No integration tests  
❌ No test coverage reporting

## Recommended Testing Strategy

### 1. Unit Tests (70% of tests)

```python
# dashboard/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from ..models import Income, SavingsGoal

class IncomeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
    
    def test_income_creation(self):
        """Test income can be created with valid data"""
        income = Income.objects.create(
            user=self.user,
            date=date.today(),
            source='Salary',
            amount=Decimal('5000.00')
        )
        self.assertEqual(income.amount, Decimal('5000.00'))
        self.assertEqual(str(income), f"Income: ₹5000.00 on {date.today()}")
    
    def test_income_requires_positive_amount(self):
        """Test income amount must be positive"""
        with self.assertRaises(ValueError):
            Income.objects.create(
                user=self.user,
                date=date.today(),
                source='Salary',
                amount=Decimal('-100.00')
            )

class SavingsGoalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
    
    def test_savings_progress_calculation(self):
        """Test savings goal progress percentage"""
        goal = SavingsGoal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('10000.00'),
            target_date=date(2026, 12, 31)
        )
        # Add contribution
        goal.contributions.create(amount=Decimal('2500.00'), date=date.today())
        
        self.assertEqual(goal.saved_amount(), Decimal('2500.00'))
        self.assertEqual(goal.progress_percentage(), 25.0)
```

### 2. View Tests (20% of tests)

```python
# dashboard/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        self.client.login(username='testuser', password='pass123')
    
    def test_dashboard_requires_login(self):
        """Test dashboard redirects to login if not authenticated"""
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Test dashboard loads successfully for logged-in user"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')
    
    def test_add_income_with_valid_data(self):
        """Test adding income with valid POST data"""
        response = self.client.post(reverse('add_income'), {
            'date': '2026-04-24',
            'source': 'Salary',
            'amount': '5000.00',
            'description': 'Monthly salary'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(Income.objects.count(), 1)
    
    def test_add_income_with_invalid_amount(self):
        """Test adding income with negative amount fails"""
        response = self.client.post(reverse('add_income'), {
            'date': '2026-04-24',
            'source': 'Salary',
            'amount': '-100.00'
        })
        self.assertEqual(Income.objects.count(), 0)
        self.assertContains(response, 'error', status_code=200)
```

### 3. Integration Tests (10% of tests)

```python
# dashboard/tests/test_integration.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

class SubscriptionBillingIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        self.client.login(username='testuser', password='pass123')
    
    def test_subscription_creates_expense_on_billing(self):
        """Test subscription automatically creates expense when billed"""
        # Create subscription
        subscription = Subscription.objects.create(
            user=self.user,
            name='Netflix',
            amount=Decimal('199.00'),
            billing_cycle='monthly',
            next_billing=date.today()
        )
        
        # Trigger billing
        subscription.process_billing()
        
        # Check expense was created
        expense = Expense.objects.filter(
            user=self.user,
            title='Netflix',
            source='subscription'
        ).first()
        
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal('199.00'))
```

### 4. Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test dashboard

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### 5. Test Coverage Goals

- **Minimum:** 70% coverage
- **Target:** 85% coverage
- **Critical paths:** 100% coverage (auth, payments, data integrity)

### 6. CI/CD Integration

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage
      - name: Run tests
        run: |
          coverage run --source='.' manage.py test
          coverage report --fail-under=70
```

## Priority: CRITICAL
## Effort: 8-12 hours for initial test suite
## Impact: Prevents bugs, enables confident refactoring
