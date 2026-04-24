from django import forms
from .models import Expense, DEFAULT_CATEGORIES
from dashboard.models import CustomCategory


def get_category_choices(user):
    custom = list(CustomCategory.objects.filter(user=user).values_list('name', flat=True))
    all_cats = DEFAULT_CATEGORIES[:]
    for c in custom:
        if c not in all_cats:
            all_cats.append(c)
    # Subscription is the single fixed category for all subscription expenses
    if 'Subscription' not in all_cats:
        all_cats.append('Subscription')
    return [(c, c) for c in all_cats]


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['date', 'title', 'category', 'amount']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'expense-input',
                'placeholder': 'e.g. Grocery run, Netflix...',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'expense-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'date': forms.DateInput(attrs={
                'class': 'expense-input',
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'] = forms.ChoiceField(
                choices=get_category_choices(user),
                widget=forms.Select(attrs={'class': 'expense-input'}),
            )
