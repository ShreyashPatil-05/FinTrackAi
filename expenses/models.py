from django.db import models
from django.contrib.auth.models import User


DEFAULT_CATEGORIES = [
    'Food', 'Travel', 'Shopping', 'Bills',
    'Transport', 'Entertainment', 'Savings',
]


class Expense(models.Model):
    SOURCE_MANUAL = 'manual'
    SOURCE_BANK   = 'bank'
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('bank',   'Bank'),
    ]

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    title    = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    amount   = models.DecimalField(max_digits=10, decimal_places=2)
    date     = models.DateField()
    source   = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')

    def __str__(self):
        return f"{self.category}: {self.amount} on {self.date}"

