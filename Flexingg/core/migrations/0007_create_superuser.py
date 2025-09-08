from django.db import migrations
from django.contrib.auth import get_user_model
import os

def generate_superuser(apps, schema_editor):
    User = get_user_model()
    
    su_name = os.getenv('DJANGO_SU_NAME', 'admin')
    su_email = os.getenv('DJANGO_SU_EMAIL', '')
    su_password = os.getenv('DJANGO_SU_PASSWORD', 'password')
    
    if not User.objects.filter(username=su_name).exists():
        superuser = User.objects.create_superuser(
            username=su_name,
            email=su_email,
            password=su_password
        )
        print(f"Superuser {su_name} created.")

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_userprofile_height_ft_userprofile_height_in_and_more'),
    ]

    operations = [
        migrations.RunPython(generate_superuser),
    ]