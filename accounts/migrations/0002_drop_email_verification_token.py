from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_email_verification_token'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmailVerificationToken',
        ),
    ]
