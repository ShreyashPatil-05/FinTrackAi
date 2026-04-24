"""
Dashboard Forms

Django forms for income, budget, subscription, and savings goal management.
"""
from django import forms
from decimal import Decimal
from .models import Income, CategoryBudget, Subscription, SavingsGoal, SavingsContribution


class IncomeForm(forms.ModelForm):
    """Form for creating/editing income entries"""
    
    class Meta:
        model = Income
        fields = ['date', 'source', 'amount', 'description']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Salary, Freelance'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes'
            }),
        }
    
    def clean_amount(self):
        """Validate amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero")
        return amount


class CategoryBudgetForm(forms.ModelForm):
    """Form for setting category budgets"""
    
    class Meta:
        model = CategoryBudget
        fields = ['category', 'limit']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
        }
    
    def clean_limit(self):
        """Validate budget limit is positive"""
        limit = self.cleaned_data.get('limit')
        if limit and limit <= 0:
            raise forms.ValidationError("Budget limit must be greater than zero")
        return limit


class SubscriptionForm(forms.ModelForm):
    """Form for creating/editing subscriptions"""
    
    CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    class Meta:
        model = Subscription
        fields = ['name', 'amount', 'billing_cycle', 'next_billing']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Netflix, Spotify'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'billing_cycle': forms.Select(attrs={'class': 'form-control'}),
            'next_billing': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def clean_amount(self):
        """Validate subscription amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Subscription amount must be greater than zero")
        return amount


class SavingsGoalForm(forms.ModelForm):
    """Form for creating/editing savings goals"""
    
    class Meta:
        model = SavingsGoal
        fields = ['name', 'target_amount', 'target_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Emergency Fund, Vacation'
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'target_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def clean_target_amount(self):
        """Validate target amount is positive"""
        amount = self.cleaned_data.get('target_amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Target amount must be greater than zero")
        return amount
    
    def clean_target_date(self):
        """Validate target date is in the future"""
        from datetime import date
        target_date = self.cleaned_data.get('target_date')
        if target_date and target_date < date.today():
            raise forms.ValidationError("Target date must be in the future")
        return target_date


class SavingsContributionForm(forms.ModelForm):
    """Form for adding contributions to savings goals"""
    
    class Meta:
        model = SavingsContribution
        fields = ['amount', 'date']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def clean_amount(self):
        """Validate contribution amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Contribution amount must be greater than zero")
        return amount
