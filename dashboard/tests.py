from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    UserProfile, Income, CategoryBudget,
    SavingsGoal, SavingsContribution, Subscription, CustomCategory
)
from expenses.models import Expense


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_user(username='testuser', password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def login(client, user):
    """Use force_login to bypass axes authentication backend in tests."""
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')


# ─────────────────────────────────────────────
# SavingsGoal Model Tests
# ─────────────────────────────────────────────

class SavingsGoalModelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.goal = SavingsGoal.objects.create(
            user=self.user, name='Car', target=50000
        )

    def test_saved_is_zero_with_no_contributions(self):
        self.assertEqual(self.goal.saved, 0)

    def test_saved_sums_contributions(self):
        SavingsContribution.objects.create(goal=self.goal, amount=10000, date='2026-03-01')
        SavingsContribution.objects.create(goal=self.goal, amount=5000,  date='2026-03-10')
        self.assertEqual(self.goal.saved, 15000)

    def test_progress_pct_correct(self):
        SavingsContribution.objects.create(goal=self.goal, amount=25000, date='2026-03-01')
        self.assertEqual(self.goal.progress_pct, 50.0)

    def test_progress_pct_capped_at_100(self):
        SavingsContribution.objects.create(goal=self.goal, amount=60000, date='2026-03-01')
        self.assertEqual(self.goal.progress_pct, 100.0)

    def test_remaining_correct(self):
        SavingsContribution.objects.create(goal=self.goal, amount=20000, date='2026-03-01')
        self.assertEqual(self.goal.remaining, 30000)

    def test_remaining_zero_when_goal_met(self):
        SavingsContribution.objects.create(goal=self.goal, amount=50000, date='2026-03-01')
        self.assertEqual(self.goal.remaining, 0)

    def test_progress_pct_zero_target(self):
        goal = SavingsGoal.objects.create(user=self.user, name='Empty', target=0)
        self.assertEqual(goal.progress_pct, 0)

    def test_saved_reflects_deleted_contribution(self):
        c = SavingsContribution.objects.create(goal=self.goal, amount=10000, date='2026-03-01')
        self.assertEqual(self.goal.saved, 10000)
        c.delete()
        self.assertEqual(self.goal.saved, 0)


# ─────────────────────────────────────────────
# Subscription Model Tests
# ─────────────────────────────────────────────

class SubscriptionModelTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_monthly_cost_monthly(self):
        sub = Subscription(amount=Decimal('649'), cycle='monthly')
        self.assertEqual(sub.monthly_cost, 649.0)

    def test_monthly_cost_yearly(self):
        sub = Subscription(amount=Decimal('1200'), cycle='yearly')
        self.assertEqual(sub.monthly_cost, 100.0)

    def test_monthly_cost_weekly(self):
        sub = Subscription(amount=Decimal('100'), cycle='weekly')
        self.assertAlmostEqual(sub.monthly_cost, 433.33, places=1)

    def test_advance_billing_creates_expense(self):
        yesterday = date.today() - timedelta(days=1)
        sub = Subscription.objects.create(
            user=self.user, name='Netflix', amount=649,
            cycle='monthly', next_billing=yesterday, status='active'
        )
        sub.advance_billing_date()
        self.assertTrue(
            Expense.objects.filter(user=self.user, title='Netflix (Subscription)').exists()
        )

    def test_advance_billing_updates_next_billing(self):
        yesterday = date.today() - timedelta(days=1)
        sub = Subscription.objects.create(
            user=self.user, name='Spotify', amount=119,
            cycle='monthly', next_billing=yesterday, status='active'
        )
        sub.advance_billing_date()
        sub.refresh_from_db()
        self.assertGreater(sub.next_billing, date.today())

    def test_advance_billing_skips_future_date(self):
        tomorrow = date.today() + timedelta(days=1)
        sub = Subscription.objects.create(
            user=self.user, name='Prime', amount=299,
            cycle='monthly', next_billing=tomorrow, status='active'
        )
        sub.advance_billing_date()
        self.assertFalse(
            Expense.objects.filter(user=self.user, title='Prime (Subscription)').exists()
        )


# ─────────────────────────────────────────────
# Auth View Tests
# ─────────────────────────────────────────────

class AuthViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser', 'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser', 'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid')

    def test_register_creates_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout_redirects(self):
        login(self.client, self.user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_change_password_wrong_current(self):
        response = self.client.post(reverse('change_password'), {
            'username': 'testuser',
            'current_password': 'wrongpass',
            'new_password1': 'NewPass@123',
            'new_password2': 'NewPass@123',
        })
        self.assertContains(response, 'incorrect')

    def test_change_password_success(self):
        response = self.client.post(reverse('change_password'), {
            'username': 'testuser',
            'current_password': 'testpass123',
            'new_password1': 'NewPass@123',
            'new_password2': 'NewPass@123',
        })
        self.assertRedirects(response, reverse('login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass@123'))

    def test_change_password_mismatch(self):
        response = self.client.post(reverse('change_password'), {
            'username': 'testuser',
            'current_password': 'testpass123',
            'new_password1': 'NewPass@123',
            'new_password2': 'DifferentPass@123',
        })
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# Dashboard View Tests
# ─────────────────────────────────────────────

class DashboardViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_dashboard_loads_for_logged_in_user(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_correct_month(self):
        response = self.client.get(reverse('dashboard') + '?month=3&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['view_month'], 3)
        self.assertEqual(response.context['view_year'], 2026)

    def test_dashboard_invalid_month_falls_back(self):
        response = self.client.get(reverse('dashboard') + '?month=99&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.context['view_month'], range(1, 13))


# ─────────────────────────────────────────────
# Expense View Tests
# ─────────────────────────────────────────────

class ExpenseViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_expense_list_loads(self):
        response = self.client.get(reverse('expense_list'))
        self.assertEqual(response.status_code, 200)

    def test_add_expense(self):
        response = self.client.post(reverse('add_expense'), {
            'title': 'Groceries', 'category': 'Food',
            'amount': '450', 'date': '2026-03-01'
        })
        self.assertRedirects(response, reverse('expense_list'))
        self.assertTrue(Expense.objects.filter(user=self.user, title='Groceries').exists())

    def test_edit_expense(self):
        expense = Expense.objects.create(
            user=self.user, title='Uber', category='Transport',
            amount=150, date='2026-03-01'
        )
        response = self.client.post(reverse('edit_expense', args=[expense.pk]), {
            'title': 'Uber Ride', 'category': 'Transport',
            'amount': '200', 'date': '2026-03-01'
        })
        self.assertRedirects(response, reverse('expense_list'))
        expense.refresh_from_db()
        self.assertEqual(expense.title, 'Uber Ride')
        self.assertEqual(float(expense.amount), 200.0)

    def test_delete_expense(self):
        expense = Expense.objects.create(
            user=self.user, title='Coffee', category='Food',
            amount=50, date='2026-03-01'
        )
        self.client.post(reverse('delete_expense', args=[expense.pk]))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_cannot_edit_other_users_expense(self):
        other = make_user('other')
        expense = Expense.objects.create(
            user=other, title='Secret', category='Food',
            amount=100, date='2026-03-01'
        )
        response = self.client.post(reverse('edit_expense', args=[expense.pk]), {
            'title': 'Hacked', 'category': 'Food',
            'amount': '100', 'date': '2026-03-01'
        })
        self.assertEqual(response.status_code, 404)

    def test_expense_list_pagination(self):
        today = date.today()
        for i in range(15):
            Expense.objects.create(
                user=self.user, title=f'Expense {i}',
                category='Food', amount=100, date=today
            )
        response = self.client.get(reverse('expense_list') + '?per_page=10')
        self.assertEqual(len(response.context['expenses']), 10)


# ─────────────────────────────────────────────
# Savings Goal View Tests
# ─────────────────────────────────────────────

class SavingsGoalViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)
        self.goal = SavingsGoal.objects.create(
            user=self.user, name='Laptop', target=80000
        )

    def test_savings_goals_page_loads(self):
        response = self.client.get(reverse('savings_goals'))
        self.assertEqual(response.status_code, 200)

    def test_add_funds_creates_contribution_and_expense(self):
        self.client.post(reverse('savings_goal_add_funds', args=[self.goal.pk]), {
            'amount': '10000', 'date': '2026-03-01'
        })
        self.assertEqual(SavingsContribution.objects.filter(goal=self.goal).count(), 1)
        self.assertTrue(Expense.objects.filter(user=self.user, category='Savings').exists())

    def test_add_funds_updates_saved(self):
        self.client.post(reverse('savings_goal_add_funds', args=[self.goal.pk]), {
            'amount': '20000', 'date': '2026-03-01'
        })
        self.assertEqual(self.goal.saved, 20000)

    def test_add_funds_exceeds_target_rejected(self):
        response = self.client.post(reverse('savings_goal_add_funds', args=[self.goal.pk]), {
            'amount': '90000', 'date': '2026-03-01'
        })
        self.assertEqual(SavingsContribution.objects.filter(goal=self.goal).count(), 0)

    def test_add_funds_zero_amount_rejected(self):
        self.client.post(reverse('savings_goal_add_funds', args=[self.goal.pk]), {
            'amount': '0', 'date': '2026-03-01'
        })
        self.assertEqual(SavingsContribution.objects.filter(goal=self.goal).count(), 0)

    def test_delete_goal(self):
        self.client.post(reverse('savings_goal_delete', args=[self.goal.pk]))
        self.assertFalse(SavingsGoal.objects.filter(pk=self.goal.pk).exists())

    def test_delete_goal_cascades_contributions(self):
        SavingsContribution.objects.create(goal=self.goal, amount=5000, date='2026-03-01')
        self.client.post(reverse('savings_goal_delete', args=[self.goal.pk]))
        self.assertFalse(SavingsContribution.objects.filter(goal=self.goal).exists())


# ─────────────────────────────────────────────
# Income View Tests
# ─────────────────────────────────────────────

class IncomeViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_income_page_loads(self):
        response = self.client.get(reverse('settings_income'))
        self.assertEqual(response.status_code, 200)

    def test_add_income(self):
        self.client.post(reverse('income_add'), {
            'date': '2026-03-01', 'source': 'Salary',
            'amount': '85000', 'description': 'March salary'
        })
        self.assertTrue(Income.objects.filter(user=self.user, source='Salary').exists())

    def test_delete_income(self):
        income = Income.objects.create(
            user=self.user, date='2026-03-01',
            source='Salary', amount=85000
        )
        self.client.post(reverse('income_delete', args=[income.pk]))
        self.assertFalse(Income.objects.filter(pk=income.pk).exists())

    def test_cannot_delete_other_users_income(self):
        other = make_user('other2')
        income = Income.objects.create(
            user=other, date='2026-03-01', source='Salary', amount=50000
        )
        self.client.post(reverse('income_delete', args=[income.pk]))
        self.assertTrue(Income.objects.filter(pk=income.pk).exists())


# ─────────────────────────────────────────────
# Budget Tests
# ─────────────────────────────────────────────

class BudgetTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_budget_page_loads(self):
        response = self.client.get(reverse('settings_budget'))
        self.assertEqual(response.status_code, 200)

    def test_save_budget_limit(self):
        self.client.post(
            reverse('settings_budget') + '?month=3&year=2026',
            {'limit_Food': '5000'}
        )
        self.assertTrue(
            CategoryBudget.objects.filter(
                user=self.user, category='Food', month=3, year=2026
            ).exists()
        )

    def test_budget_alert_in_dashboard_context(self):
        today = date.today()
        CategoryBudget.objects.create(
            user=self.user, category='Food',
            limit=1000, month=today.month, year=today.year
        )
        Expense.objects.create(
            user=self.user, title='Food', category='Food',
            amount=900, date=today
        )
        response = self.client.get(reverse('dashboard'))
        alerts = response.context['budget_alerts']
        self.assertTrue(any(a['category'] == 'Food' for a in alerts))


# ─────────────────────────────────────────────
# Profile & Account Tests
# ─────────────────────────────────────────────

class ProfileTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_profile_page_loads(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_update_profile(self):
        self.client.post(reverse('profile'), {
            'action': 'profile',
            'first_name': 'Shreyash',
            'last_name': 'Patil',
            'username': 'testuser',
            'email': 'shreyash@example.com',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Shreyash')

    def test_delete_account(self):
        self.client.post(reverse('delete_account'))
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_delete_account_cascades_expenses(self):
        Expense.objects.create(
            user=self.user, title='Test', category='Food',
            amount=100, date='2026-03-01'
        )
        self.client.post(reverse('delete_account'))
        self.assertFalse(Expense.objects.filter(title='Test').exists())


# ─────────────────────────────────────────────
# Subscription View Tests
# ─────────────────────────────────────────────

class SubscriptionViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        login(self.client, self.user)

    def test_subscriptions_page_loads(self):
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, 200)

    def test_add_subscription(self):
        self.client.post(reverse('subscription_add'), {
            'name': 'Netflix', 'amount': '649',
            'cycle': 'monthly', 'category': 'Streaming',
            'next_billing': str(date.today() + timedelta(days=30)),
            'status': 'active',
        })
        self.assertTrue(
            Subscription.objects.filter(user=self.user, name='Netflix').exists()
        )

    def test_delete_subscription(self):
        sub = Subscription.objects.create(
            user=self.user, name='Spotify', amount=119,
            cycle='monthly', next_billing=date.today() + timedelta(days=15),
            status='active'
        )
        self.client.post(reverse('subscription_delete', args=[sub.pk]))
        self.assertFalse(Subscription.objects.filter(pk=sub.pk).exists())


# ─────────────────────────────────────────────
# 404 Handler Test
# ─────────────────────────────────────────────

class ErrorPageTests(TestCase):

    def test_unknown_url_returns_404(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
