from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0012_add_webhook_token'),
    ]

    operations = [
        migrations.RenameField(
            model_name='webhooktoken',
            old_name='token',
            new_name='token_hash',
        ),
        migrations.AlterField(
            model_name='webhooktoken',
            name='token_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
