from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} profile"


class CustomCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_categories')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Income(models.Model):
    SOURCE_CHOICES = [
        ('Salary',     'Salary'),
        ('Freelance',  'Freelance'),
        ('Business',   'Business'),
        ('Investment', 'Investment'),
        ('Gift',       'Gift'),
        ('Other',      'Other'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    date        = models.DateField()
    source      = models.CharField(max_length=100, choices=SOURCE_CHOICES, default='Salary')
    description = models.CharField(max_length=255, blank=True)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.source}: {self.amount} on {self.date}"


class CategoryBudget(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    limit    = models.DecimalField(max_digits=12, decimal_places=2)
    month    = models.PositiveSmallIntegerField(default=0)   # 0 = every month
    year     = models.PositiveSmallIntegerField(default=0)   # 0 = every month

    class Meta:
        unique_together = ('user', 'category', 'month', 'year')

    def __str__(self):
        return f"{self.user.username} – {self.category} ({self.month}/{self.year}): {self.limit}"


class SavingsGoal(models.Model):
    ICON_CHOICES = [
        ('piggy-bank',      '🐷 Piggy Bank'),
        ('house',           '🏠 House'),
        ('car-front',       '🚗 Car'),
        ('airplane',        '✈️ Travel'),
        ('laptop',          '💻 Laptop'),
        ('heart-pulse',     '❤️ Health'),
        ('mortarboard',     '🎓 Education'),
        ('gem',             '💎 Luxury'),
        ('shield-check',    '🛡️ Emergency'),
        ('trophy',          '🏆 Goal'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name        = models.CharField(max_length=100)
    target      = models.DecimalField(max_digits=12, decimal_places=2)
    target_date = models.DateField(null=True, blank=True)
    icon        = models.CharField(max_length=30, default='piggy-bank')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_date', 'created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def saved(self):
        # Use prefetched contributions if available (avoids N+1 queries)
        if hasattr(self, '_prefetched_objects_cache') and 'contributions' in self._prefetched_objects_cache:
            return float(sum(c.amount for c in self._prefetched_objects_cache['contributions']))
        from django.db.models import Sum
        total = self.contributions.aggregate(Sum('amount'))['amount__sum']
        return float(total or 0)

    @property
    def progress_pct(self):
        if not self.target or self.target <= 0:
            return 0
        return min(round(self.saved / float(self.target) * 100, 1), 100)

    @property
    def remaining(self):
        if not self.target:
            return 0
        return max(float(self.target) - self.saved, 0)


class SavingsContribution(models.Model):
    goal       = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='contributions')
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    date       = models.DateField()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"+{self.amount} → {self.goal.name} on {self.date}"


class Subscription(models.Model):
    CYCLE_CHOICES = [
        ('weekly',  'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly',  'Yearly'),
    ]
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('paused',    'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    CATEGORY_CHOICES = [
        ('Streaming', 'Streaming'),
        ('Music',     'Music'),
        ('Software',  'Software'),
        ('Gaming',    'Gaming'),
        ('News',      'News'),
        ('Fitness',   'Fitness'),
        ('Cloud',     'Cloud'),
        ('Other',     'Other'),
    ]
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    name         = models.CharField(max_length=100)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    cycle        = models.CharField(max_length=10, choices=CYCLE_CHOICES, default='monthly')
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    next_billing = models.DateField()
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['next_billing']

    def __str__(self):
        return f"{self.name} ({self.cycle})"

    @property
    def monthly_cost(self):
        if self.cycle == 'weekly':
            return float(self.amount) * 52 / 12
        elif self.cycle == 'yearly':
            return float(self.amount) / 12
        return float(self.amount)

    def advance_billing_date(self):
        """Advance next_billing past today, creating an Expense for each elapsed cycle."""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        from expenses.models import Expense
        today = date.today()
        if self.next_billing >= today:
            return
        d = self.next_billing
        while d < today:
            # Record an expense on the billing date — use source='bank' equivalent
            # Use update_or_create keyed on title+date+source to avoid collision with manual entries
            Expense.objects.get_or_create(
                user=self.user,
                title=f"{self.name} (Subscription)",
                date=d,
                source='subscription',
                defaults={'category': 'Subscription', 'amount': self.amount},
            )
            if self.cycle == 'weekly':
                d += relativedelta(weeks=1)
            elif self.cycle == 'yearly':
                d += relativedelta(years=1)
            else:
                d += relativedelta(months=1)
        self.next_billing = d
        self.save(update_fields=['next_billing'])


class WebhookToken(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='webhook_token')
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hex digest

    def save(self, *args, **kwargs):
        if not self.token_hash:
            import secrets
            raw = secrets.token_urlsafe(32)
            self._raw_token = raw  # available once, not stored
            self.token_hash = self._hash(raw)
        super().save(*args, **kwargs)

    def regenerate(self):
        import secrets
        raw = secrets.token_urlsafe(32)
        self._raw_token = raw
        self.token_hash = self._hash(raw)
        self.save(update_fields=['token_hash'])
        return raw

    @staticmethod
    def _hash(raw_token):
        import hashlib
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def verify(cls, raw_token):
        """Look up a WebhookToken by raw token value. Returns the instance or None."""
        import hashlib, hmac
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            # Use constant-time comparison via filter then hmac to prevent timing attacks
            obj = cls.objects.select_related('user').get(token_hash=token_hash)
            if hmac.compare_digest(obj.token_hash, token_hash):
                return obj
        except cls.DoesNotExist:
            pass
        return None

    def __str__(self):
        return f"Webhook token for {self.user.username}"
