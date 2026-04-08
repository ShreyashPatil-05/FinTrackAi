"""
Dashboard app — URL Configuration
"""
from django.urls import path
from . import views


urlpatterns = [

    # Public
    path('', views.landing, name='landing'),

    # Core dashboard
    path('dashboard/',    views.dashboard_view, name='dashboard'),
    path('tour-complete/', views.tour_complete,  name='tour_complete'),
    path('profile/',      views.profile,         name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('export-data/',  views.export_data,     name='export_data'),

    # Settings — dispatcher
    path('settings/', views.settings, name='settings'),

    # Settings — Income
    path('settings/income/',                   views.settings_income, name='settings_income'),
    path('settings/income/add/',               views.income_add,      name='income_add'),
    path('settings/income/<int:pk>/edit/',     views.income_edit,     name='income_edit'),
    path('settings/income/<int:pk>/delete/',   views.income_delete,   name='income_delete'),

    # Settings — Categories
    path('settings/categories/', views.settings_categories, name='settings_categories'),

    # Settings — Budget
    path('settings/budget/',                  views.settings_budget,          name='settings_budget'),
    path('settings/budget/copy-last-month/', views.budget_copy_last_month,   name='budget_copy_last_month'),

    # Settings — Upload
    path('settings/upload/', views.settings_upload, name='settings_upload'),

    # Subscriptions
    path('subscriptions/',                    views.subscriptions,       name='subscriptions'),
    path('subscriptions/add/',                views.subscription_add,    name='subscription_add'),
    path('subscriptions/<int:pk>/edit/',      views.subscription_edit,   name='subscription_edit'),
    path('subscriptions/<int:pk>/delete/',    views.subscription_delete, name='subscription_delete'),

    # Savings Goals
    path('savings-goals/',                        views.savings_goals,        name='savings_goals'),
    path('savings-goals/add/',                    views.savings_goal_add,     name='savings_goal_add'),
    path('savings-goals/<int:pk>/',               views.savings_goal_detail,  name='savings_goal_detail'),
    path('savings-goals/<int:pk>/edit/',          views.savings_goal_edit,    name='savings_goal_edit'),
    path('savings-goals/<int:pk>/add-funds/',     views.savings_goal_add_funds, name='savings_goal_add_funds'),
    path('savings-goals/<int:pk>/delete/',        views.savings_goal_delete,  name='savings_goal_delete'),

]
