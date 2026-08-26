from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import UserProfile, Income, CategoryBudget, Subscription, SavingsGoal, CustomCategory, WebhookToken, Payment
from expenses.models import Expense


# ── Inlines ──────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    fields = ('onboarding_complete', 'avatar', 'plan', 'plan_expires_at')


class IncomeInline(admin.TabularInline):
    model = Income
    extra = 0
    fields = ('date', 'source', 'amount', 'description')
    readonly_fields = ('date', 'source', 'amount', 'description')
    ordering = ('-date',)
    max_num = 20
    can_delete = False


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0
    fields = ('date', 'title', 'category', 'amount')
    readonly_fields = ('date', 'title', 'category', 'amount')
    ordering = ('-date',)
    max_num = 20
    can_delete = False


class CategoryBudgetInline(admin.TabularInline):
    model = CategoryBudget
    extra = 0
    fields = ('category', 'limit', 'month', 'year')
    readonly_fields = ('category', 'month', 'year')


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    fields = ('name', 'amount', 'cycle', 'status', 'next_billing')
    readonly_fields = ('name', 'amount', 'cycle', 'next_billing')
    ordering = ('next_billing',)


class SavingsGoalInline(admin.TabularInline):
    model = SavingsGoal
    extra = 0
    fields = ('name', 'target', 'saved', 'target_date')
    readonly_fields = ('name', 'target', 'saved', 'target_date')


class CustomCategoryInline(admin.TabularInline):
    model = CustomCategory
    extra = 0
    fields = ('name',)


# ── Actions ──────────────────────────────────────────

def deactivate_users(modeladmin, request, queryset):
    queryset.exclude(is_superuser=True).update(is_active=False)
deactivate_users.short_description = 'Deactivate selected users'


def activate_users(modeladmin, request, queryset):
    queryset.update(is_active=True)
activate_users.short_description = 'Activate selected users'


def grant_monthly_pro(modeladmin, request, queryset):
    """Grant Monthly Pro to selected users for 31 days."""
    for user in queryset:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.plan = 'monthly'
        profile.plan_expires_at = timezone.now() + timedelta(days=31)
        profile.save()
grant_monthly_pro.short_description = 'Grant Monthly Pro (31 days)'


def grant_yearly_pro(modeladmin, request, queryset):
    """Grant Yearly Pro to selected users for 365 days."""
    for user in queryset:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.plan = 'yearly'
        profile.plan_expires_at = timezone.now() + timedelta(days=365)
        profile.save()
grant_yearly_pro.short_description = 'Grant Yearly Pro (365 days)'


def revoke_pro(modeladmin, request, queryset):
    """Revert selected users to Free plan."""
    for user in queryset:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.plan = 'free'
        profile.plan_expires_at = None
        profile.save()
revoke_pro.short_description = 'Revoke Pro — set to Free'


# ── Extended UserAdmin ────────────────────────────────

class FinTrackUserAdmin(BaseUserAdmin):
    inlines = (
        UserProfileInline,
        IncomeInline,
        ExpenseInline,
        CategoryBudgetInline,
        SubscriptionInline,
        SavingsGoalInline,
        CustomCategoryInline,
    )
    actions = [deactivate_users, activate_users, grant_monthly_pro, grant_yearly_pro, revoke_pro]
    list_display = ('username', 'email', 'date_joined', 'last_login', 'is_active', 'get_plan')
    list_filter  = ('is_active', 'is_staff', 'date_joined', 'profile__plan')
    ordering     = ('date_joined',)

    @admin.display(description='Plan')
    def get_plan(self, obj):
        try:
            return obj.profile.get_plan_display()
        except UserProfile.DoesNotExist:
            return '—'


admin.site.unregister(User)
admin.site.register(User, FinTrackUserAdmin)


# ── Webhook Token ─────────────────────────────────────

@admin.register(WebhookToken)
class WebhookTokenAdmin(admin.ModelAdmin):
    list_display  = ('user', 'token_hash')
    readonly_fields = ('token_hash',)
    fields        = ('user', 'token_hash')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Show the raw token once after creation
        if hasattr(obj, '_raw_token'):
            
            messages.success(request, f'Webhook token for {obj.user.username}: {obj._raw_token} — copy it now, it won\'t be shown again.')


# ── Payment ───────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display    = ('user', 'plan', 'amount', 'status', 'created_at')
    list_filter     = ('status', 'plan')
    search_fields   = ('user__username', 'user__email', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at', 'updated_at')
    ordering        = ('-created_at',)
