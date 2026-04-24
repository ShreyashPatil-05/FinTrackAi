# Generated migration for model validation improvements

from django.db import migrations, models
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_create_site'),
    ]

    operations = [
        # Add validators to Income.amount
        migrations.AlterField(
            model_name='income',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]
            ),
        ),
        # Add validators to CategoryBudget.limit
        migrations.AlterField(
            model_name='categorybudget',
            name='limit',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]
            ),
        ),
        # Add validators to SavingsGoal.target
        migrations.AlterField(
            model_name='savingsgoal',
            name='target',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]
            ),
        ),
        # Add validators to SavingsContribution.amount
        migrations.AlterField(
            model_name='savingscontribution',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]
            ),
        ),
        # Add validators to Subscription.amount
        migrations.AlterField(
            model_name='subscription',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]
            ),
        ),
        # Add database indexes for performance
        migrations.AddIndex(
            model_name='income',
            index=models.Index(fields=['user', '-date'], name='dashboard_i_user_id_date_idx'),
        ),
        migrations.AddIndex(
            model_name='income',
            index=models.Index(fields=['user', 'source'], name='dashboard_i_user_id_source_idx'),
        ),
        migrations.AddIndex(
            model_name='categorybudget',
            index=models.Index(fields=['user', 'month', 'year'], name='dashboard_c_user_id_month_year_idx'),
        ),
        migrations.AddIndex(
            model_name='savingsgoal',
            index=models.Index(fields=['user', 'target_date'], name='dashboard_s_user_id_target_idx'),
        ),
        migrations.AddIndex(
            model_name='savingscontribution',
            index=models.Index(fields=['goal', '-date'], name='dashboard_s_goal_id_date_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['user', 'status', 'next_billing'], name='dashboard_s_user_status_next_idx'),
        ),
    ]
