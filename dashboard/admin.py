from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, Income, CategoryBudget, Subscription, SavingsGoal, CustomCategory, WebhookToken
from expenses.models import Expense


# ── Inlines ──────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    fields = ('onboarding_complete', 'avatar')


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
    actions = [deactivate_users, activate_users]
    list_display = ('username', 'email', 'date_joined', 'last_login', 'is_active')
    list_filter  = ('is_active', 'is_staff', 'date_joined')
    ordering     = ('date_joined',)


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
            from django.contrib import messages
            messages.success(request, f'Webhook token for {obj.user.username}: {obj._raw_token} — copy it now, it won\'t be shown again.')
