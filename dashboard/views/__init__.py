# Dashboard Views Package
from .landing import landing
from .dashboard import dashboard_view, tour_complete
from .profile import profile, delete_account
from .income import settings_income, income_add, income_edit, income_delete
from .budget import settings_budget, settings_categories, budget_copy_last_month
from .subscriptions import subscriptions, subscription_add, subscription_edit, subscription_delete
from .savings import savings_goals, savings_goal_add, savings_goal_edit, savings_goal_detail, savings_goal_add_funds, savings_goal_delete
from .export import export_data
from .upload import settings_upload
from .settings import settings

__all__ = [
    'landing',
    'dashboard_view',
    'tour_complete',
    'profile',
    'delete_account',
    'settings',
    'settings_income',
    'income_add',
    'income_edit',
    'income_delete',
    'settings_budget',
    'settings_categories',
    'budget_copy_last_month',
    'subscriptions',
    'subscription_add',
    'subscription_edit',
    'subscription_delete',
    'savings_goals',
    'savings_goal_add',
    'savings_goal_edit',
    'savings_goal_detail',
    'savings_goal_add_funds',
    'savings_goal_delete',
    'export_data',
    'settings_upload',
]
