"""
Expense Models

Core expense tracking model with support for manual entries,
bank webhooks, and subscription-generated expenses.
"""
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


DEFAULT_CATEGORIES = [
    'Food', 'Travel', 'Shopping', 'Bills',
    'Transport', 'Entertainment', 'Savings',
]


class Expense(models.Model):
    """
    Individual expense entry with amount, category, and source tracking.
    
    Sources:
        - manual: User-created expense
        - bank: Created via webhook from mock bank simulator
        - subscription: Auto-generated from subscription billing
    
    Attributes:
        user: Foreign key to User who owns this expense
        title: Expense description (e.g., "Grocery shopping")
        category: Category name (from DEFAULT_CATEGORIES or custom)
        amount: Expense amount (Decimal for precision)
        date: Date of expense
        source: How the expense was created (manual/bank/subscription)
    """
    SOURCE_MANUAL = 'manual'
    SOURCE_BANK   = 'bank'
    SOURCE_CHOICES = [
        ('manual',       'Manual'),
        ('bank',         'Bank'),
        ('subscription', 'Subscription'),
    ]

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    title    = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    amount   = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date     = models.DateField()
    source   = models.CharField(max_length=12, choices=SOURCE_CHOICES, default='manual')

    def clean(self):
        """Validate expense data — amount must be positive."""
        if self.amount is not None and self.amount <= Decimal('0'):
            raise ValidationError({'amount': 'Amount must be greater than zero'})

    def save(self, *args, **kwargs):
        """Always validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category}: {self.amount} on {self.date}"
    
    def __repr__(self):
        return f"<Expense: {self.title} - ₹{self.amount} ({self.source})>"

