from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('add/', views.add_expense, name='add_expense'),
    path('<int:pk>/edit/', views.edit_expense, name='edit_expense'),
    path('<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    path('bulk-delete/', views.bulk_delete_expenses, name='bulk_delete_expenses'),
]
