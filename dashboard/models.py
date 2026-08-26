"""
Dashboard Models

Core models for user profiles, income tracking, budgets, subscriptions,
savings goals, and webhook authentication.
"""
from datetime import date
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class UserProfile(models.Model):
    """
    Extended user profile with avatar, onboarding status, and SaaS plan.

    Attributes:
        user: One-to-one link to Django User
        avatar: Profile picture (stored in media/avatars/)
        onboarding_complete: Whether user has completed the dashboard tour
        plan: Current subscription plan (free / monthly / yearly)
        plan_expires_at: When the Pro plan expires (None = never expires)
    """
    PLAN_FREE    = 'free'
    PLAN_MONTHLY = 'monthly'
    PLAN_YEARLY  = 'yearly'
    PLAN_CHOICES = [
        ('free',    'Free'),
        ('monthly', 'Monthly Pro'),
        ('yearly',  'Yearly Pro'),
    ]

    user                = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar              = models.ImageField(upload_to='avatars/', null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    plan                = models.CharField(max_length=10, choices=PLAN_CHOICES, default='free')
    plan_expires_at     = models.DateTimeField(null=True, blank=True)

    def is_pro(self) -> bool:
        """Return True if the user has an active Pro plan."""
        if self.plan in (self.PLAN_MONTHLY, self.PLAN_YEARLY):
            if self.plan_expires_at is None or self.plan_expires_at > timezone.now():
                return True
        return False

    def __str__(self):
        return f"{self.user.username} profile"

    def __repr__(self):
        return f"<UserProfile: {self.user.username} plan={self.plan} onboarded={self.onboarding_complete}>"


class Payment(models.Model):
    """
    Records a Razorpay payment transaction for a Pro plan upgrade.

    Attributes:
        user: User who made the payment
        plan: Which plan was purchased (monthly / yearly)
        amount: Amount in INR (₹49 or ₹499)
        razorpay_order_id: Razorpay order identifier
        razorpay_payment_id: Razorpay payment identifier (set after capture)
        razorpay_signature: HMAC signature for verification
        status: pending → captured / failed / refunded
        created_at / updated_at: Timestamps
    """
    STATUS_PENDING  = 'pending'
    STATUS_CAPTURED = 'captured'
    STATUS_FAILED   = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('captured', 'Captured'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]
    PLAN_CHOICES = [
        ('monthly', 'Monthly — ₹49'),
        ('yearly',  'Yearly — ₹499'),
    ]

    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan                = models.CharField(max_length=10, choices=PLAN_CHOICES)
    amount              = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id   = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=255, blank=True)
    status              = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['razorpay_order_id']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.plan} — {self.status} — ₹{self.amount}"

    def __repr__(self):
        return f"<Payment: {self.user.username} {self.plan} {self.status} ₹{self.amount}>"


class CustomCategory(models.Model):
    """
    User-defined expense categories beyond the default set.
    
    Attributes:
        user: Foreign key to User who created this category
        name: Category name (must be unique per user)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_categories')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"<CustomCategory: {self.name} (user={self.user.username})>"


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
    amount      = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'source']),
        ]

    def clean(self):
        """Validate income data"""
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero'})
        if self.date > date.today():
            raise ValidationError({'date': 'Income date cannot be in the future'})

    def save(self, *args, **kwargs):
        """Always validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source}: ₹{self.amount} on {self.date}"
    
    def __repr__(self):
        return f"<Income: {self.source} ₹{self.amount} ({self.date})>"


class CategoryBudget(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    limit    = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    month    = models.PositiveSmallIntegerField(default=0)   # 0 = every month
    year     = models.PositiveSmallIntegerField(default=0)   # 0 = every month

    class Meta:
        unique_together = ('user', 'category', 'month', 'year')
        indexes = [
            models.Index(fields=['user', 'month', 'year']),
        ]

    def clean(self):
        """Validate budget data"""
        if self.limit <= 0:
            raise ValidationError({'limit': 'Budget limit must be greater than zero'})
        if self.month < 0 or self.month > 12:
            raise ValidationError({'month': 'Month must be between 0 and 12'})

    def save(self, *args, **kwargs):
        """Always validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} – {self.category} ({self.month}/{self.year}): ₹{self.limit}"
    
    def __repr__(self):
        return f"<CategoryBudget: {self.category} ₹{self.limit} ({self.month}/{self.year})>"


class SavingsGoal(models.Model):
    """
    User's savings goal with target amount and optional deadline.
    
    Tracks contributions through SavingsContribution model.
    Automatically calculates progress percentage and remaining amount.
    
    Attributes:
        user: Foreign key to User
        name: Goal name (e.g., "Emergency Fund", "Vacation")
        target: Target amount to save
        target_date: Optional deadline for reaching the goal
        icon: Icon identifier for UI display
        created_at: Timestamp when goal was created
    """
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
    target      = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    target_date = models.DateField(null=True, blank=True)
    icon        = models.CharField(max_length=30, default='piggy-bank')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_date', 'created_at']
        indexes = [
            models.Index(fields=['user', 'target_date']),
        ]

    def clean(self):
        """Validate savings goal data"""
        if self.target <= 0:
            raise ValidationError({'target': 'Target amount must be greater than zero'})
        if self.target_date and self.target_date < date.today():
            raise ValidationError({'target_date': 'Target date cannot be in the past'})

    def save(self, *args, **kwargs):
        """Always validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def __repr__(self):
        return f"<SavingsGoal: {self.name} - {self.progress_pct}% complete>"

    @property
    def saved(self):
        """
        Calculate total amount saved towards this goal.
        
        Uses prefetched contributions if available to avoid N+1 queries.
        
        Returns:
            float: Total saved amount
        """
        # Use prefetched contributions if available (avoids N+1 queries)
        if hasattr(self, '_prefetched_objects_cache') and 'contributions' in self._prefetched_objects_cache:
            return float(sum(c.amount for c in self._prefetched_objects_cache['contributions']))
        
        total = self.contributions.aggregate(Sum('amount'))['amount__sum']
        return float(total or 0)

    @property
    def progress_pct(self):
        """
        Calculate progress percentage towards target.
        
        Returns:
            float: Progress percentage (0-100), capped at 100
        """
        if not self.target or self.target <= 0:
            return 0
        return min(round(self.saved / float(self.target) * 100, 1), 100)

    @property
    def remaining(self):
        """
        Calculate remaining amount needed to reach target.
        
        Returns:
            float: Remaining amount (0 if target reached)
        """
        if not self.target:
            return 0
        return max(float(self.target) - self.saved, 0)


class SavingsContribution(models.Model):
    goal       = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='contributions')
    amount     = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date       = models.DateField()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['goal', '-date']),
        ]

    def clean(self):
        """Validate contribution data"""
        if self.amount <= 0:
            raise ValidationError({'amount': 'Contribution amount must be greater than zero'})
        if self.date > date.today():
            raise ValidationError({'date': 'Contribution date cannot be in the future'})

    def save(self, *args, **kwargs):
        """Always validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"+₹{self.amount} → {self.goal.name} on {self.date}"
    
    def __repr__(self):
        return f"<SavingsContribution: ₹{self.amount} to {self.goal.name}>"


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
    amount       = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cycle        = models.CharField(max_length=10, choices=CYCLE_CHOICES, default='monthly')
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    next_billing = models.DateField()
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['next_billing']
        indexes = [
            models.Index(fields=['user', 'status', 'next_billing']),
        ]

    def clean(self):
        """Validate subscription data"""
        if self.amount <= 0:
            raise ValidationError({'amount': 'Subscription amount must be greater than zero'})
        if self.next_billing < date.today():
            raise ValidationError({'next_billing': 'Next billing date cannot be in the past'})

    def save(self, *args, **kwargs):
        """Always validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.cycle})"
    
    def __repr__(self):
        return f"<Subscription: {self.name} - ₹{self.amount}/{self.cycle} ({self.status})>"

    @property
    def monthly_cost(self):
        """
        Calculate equivalent monthly cost regardless of billing cycle.
        
        Returns:
            float: Monthly cost (weekly * 52/12, yearly / 12, or monthly as-is)
        """
        if self.cycle == 'weekly':
            return float(self.amount) * 52 / 12
        elif self.cycle == 'yearly':
            return float(self.amount) / 12
        return float(self.amount)

    def advance_billing_date(self):
        """
        Advance next_billing past today, creating an Expense for each elapsed cycle.
        
        For overdue subscriptions, this creates expense entries for all missed
        billing dates and updates next_billing to the next future date.
        
        Uses get_or_create to avoid duplicate expenses if called multiple times.
        
        Raises:
            ValueError: If subscription cycle is invalid
        """
        from expenses.models import Expense
        
        today = date.today()
        if self.next_billing > today:
            return
        d = self.next_billing
        while d <= today:
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
    """
    Secure webhook authentication token for bank transaction API.
    
    Tokens are hashed using SHA-256 before storage. The raw token is only
    shown once during creation and cannot be retrieved later.
    
    Attributes:
        user: One-to-one link to User (each user has one webhook token)
        token_hash: SHA-256 hash of the raw token
    """
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='webhook_token')
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hex digest

    def save(self, *args, **kwargs):
        """
        Generate and hash a new token on first save.
        
        The raw token is stored in self._raw_token temporarily for display
        in the admin interface, but is never persisted to the database.
        """
        if not self.token_hash:
            import secrets
            raw = secrets.token_urlsafe(32)
            self._raw_token = raw  # available once, not stored
            self.token_hash = self._hash(raw)
        super().save(*args, **kwargs)

    def regenerate(self):
        """
        Generate a new token and update the hash.
        
        Returns:
            str: New raw token (only time it's accessible)
        """
        import secrets
        raw = secrets.token_urlsafe(32)
        self._raw_token = raw
        self.token_hash = self._hash(raw)
        self.save(update_fields=['token_hash'])
        return raw

    @staticmethod
    def _hash(raw_token):
        """
        Hash a raw token using SHA-256.
        
        Args:
            raw_token: Plain text token string
            
        Returns:
            str: Hex digest of SHA-256 hash
        """
        import hashlib
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def verify(cls, raw_token):
        """
        Look up a WebhookToken by raw token value using constant-time comparison.
        
        Uses hmac.compare_digest to prevent timing attacks that could
        reveal information about valid tokens.
        
        Args:
            raw_token: Plain text token to verify
            
        Returns:
            WebhookToken instance if valid, None otherwise
        """
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
