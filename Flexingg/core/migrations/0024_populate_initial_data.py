from django.core.management import call_command
from django.db import migrations

def populate_levels_data(apps, schema_editor):
    """Populate the Level table with exponential XP requirements."""
    try:
        # Call populate_levels with default parameters
        call_command('populate_levels', max_level=100, base_xp='100', growth_factor='1.1')
        print("Successfully populated levels data.")
    except Exception as e:
        print(f"Error populating levels data: {e}")
        raise

def populate_data_priorities(apps, schema_editor):
    """Populate default DataPriority entries for users who lack them using historical models."""
    DataPriority = apps.get_model('core', 'DataPriority')
    UserProfile = apps.get_model('core', 'UserProfile')
    try:
        for user in UserProfile.objects.all():
            # Workout priorities: Liftosaur primary, Garmin secondary, Health Connect tertiary
            DataPriority.objects.get_or_create(
                user=user,
                data_type='workout',
                source='liftosaur',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='workout',
                source='garmin',
                defaults={'rank': 2}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='workout',
                source='healthconnect',
                defaults={'rank': 3}
            )
            # Sleep priorities: Health Connect primary, Garmin secondary
            DataPriority.objects.get_or_create(
                user=user,
                data_type='sleep',
                source='healthconnect',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='sleep',
                source='garmin',
                defaults={'rank': 2}
            )
            # Steps priorities: Garmin primary, Health Connect secondary
            DataPriority.objects.get_or_create(
                user=user,
                data_type='steps',
                source='garmin',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='steps',
                source='healthconnect',
                defaults={'rank': 2}
            )
            # Water priorities: Health Connect primary, Garmin secondary
            DataPriority.objects.get_or_create(
                user=user,
                data_type='water',
                source='healthconnect',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='water',
                source='garmin',
                defaults={'rank': 2}
            )
            # Bodyweight priorities: Garmin primary, Health Connect secondary
            DataPriority.objects.get_or_create(
                user=user,
                data_type='bodyweight',
                source='garmin',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='bodyweight',
                source='healthconnect',
                defaults={'rank': 2}
            )
        print("Successfully populated data priorities.")
    except Exception as e:
        print(f"Error populating data priorities: {e}")
        raise

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0023_level_transaction_xp_awarded_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_levels_data),
        migrations.RunPython(populate_data_priorities),
    ]