from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import DataPriority

UserProfile = get_user_model()

class Command(BaseCommand):
    help = 'Populate default DataPriority entries for users who lack them'

    def handle(self, *args, **options):
        users_without_priorities = UserProfile.objects.filter(
            data_priorities__isnull=True
        ).distinct()

        created_count = 0
        for user in users_without_priorities:
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
            # Steps priorities
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
            # Water priorities
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
            created_count += 11

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated defaults for {users_without_priorities.count()} users ({created_count} entries).'
            )
        )