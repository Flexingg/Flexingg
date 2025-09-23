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
    """Populate default DataPriority entries for users who lack them."""
    try:
        # Call populate_data_priorities command
        call_command('populate_data_priorities')
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