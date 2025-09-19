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
            # Workout priorities
            DataPriority.objects.get_or_create(
                user=user,
                data_type='workout',
                source='garmin',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=user,
                data_type='workout',
                source='liftosaur',
                defaults={'rank': 2}
            )
            # Sleep priorities
            DataPriority.objects.get_or_create(
                user=user,
                data_type='sleep',
                source='healthconnect',
                defaults={'rank': 1}
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
            created_count += 5

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated defaults for {users_without_priorities.count()} users ({created_count} entries).'
            )
        )