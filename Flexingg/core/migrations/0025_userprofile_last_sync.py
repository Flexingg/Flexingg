# Generated migration for adding last_sync field to UserProfile

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_populate_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='last_sync',
            field=models.DateTimeField(blank=True, help_text='Timestamp of the last general sync', null=True),
        ),
    ]