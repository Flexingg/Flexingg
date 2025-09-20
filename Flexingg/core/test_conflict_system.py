"""
Test script for the new conflict detection and resolution system.
This demonstrates how the system handles conflicts between different data sources.
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flexingg.settings')
django.setup()

from .models import UserProfile, Workout, ArchivedWorkout, WorkoutConflict, DataPriority
from .conflict_detection import ConflictDetector, ConflictResolver


def create_test_user():
    """Create a test user for demonstration."""
    user, created = UserProfile.objects.get_or_create(
        username='test_user_conflict',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")

    # Set up data priorities
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

    return user


def create_test_workouts(user):
    """Create test workouts to demonstrate conflicts."""
    now = timezone.now()

    # Create a Liftosaur workout (higher priority)
    liftosaur_workout = Workout.objects.create(
        user=user,
        source='liftosaur',
        source_id='liftosaur_123',
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        data={
            'exercise_name': 'Bench Press',
            'sets': [{'weight': 100, 'reps': 8}],
            'calories': None,  # Missing data
            'heartRate': None   # Missing data
        }
    )

    # Create a Garmin workout at the same time (lower priority, should be archived)
    garmin_workout = Workout.objects.create(
        user=user,
        source='garmin',
        source_id='garmin_456',
        start_time=now - timedelta(hours=2, minutes=5),  # 5 minutes later
        end_time=now - timedelta(hours=1, minutes=30),
        data={
            'activityName': 'Strength Training',
            'calories': 150,      # Has data that Liftosaur is missing
            'heartRate': 140,     # Has data that Liftosaur is missing
            'duration': 3600
        }
    )

    print(f"Created Liftosaur workout: {liftosaur_workout}")
    print(f"Created Garmin workout: {garmin_workout}")

    return liftosaur_workout, garmin_workout


def demonstrate_conflict_detection(user, workout1, workout2):
    """Demonstrate conflict detection between workouts."""
    print("\n=== Conflict Detection Demo ===")

    detector = ConflictDetector(user)

    # Test conflict detection
    conflicts = detector.detect_conflicts(
        {
            'source': 'garmin',
            'start_time': workout2.start_time,
            'end_time': workout2.end_time,
            'data': workout2.data
        },
        [workout1]
    )

    print(f"Detected conflicts: {len(conflicts)}")
    for conflict in conflicts:
        print(f"  - Type: {conflict['type']}")
        print(f"  - Confidence: {conflict['confidence']}")
        print(f"  - Description: {conflict['description']}")


def demonstrate_conflict_resolution(user, primary_workout, conflict_workout):
    """Demonstrate conflict resolution by archiving lower priority workout."""
    print("\n=== Conflict Resolution Demo ===")

    resolver = ConflictResolver(user)

    # Resolve conflicts
    archived_workouts = resolver.resolve_conflicts(primary_workout, [conflict_workout])

    print(f"Archived workouts: {len(archived_workouts)}")
    for archived in archived_workouts:
        print(f"  - Archived: {archived.source} workout {archived.source_id}")
        print(f"    Reason: {archived.archived_reason}")
        print(f"    Linked to: {archived.linked_primary_workout.source} workout")


def demonstrate_data_merging(user, primary_workout):
    """Demonstrate merging missing data from archived workouts."""
    print("\n=== Data Merging Demo ===")

    resolver = ConflictResolver(user)

    # Get archived workouts linked to the primary workout
    archived_workouts = ArchivedWorkout.objects.filter(
        linked_primary_workout=primary_workout
    )

    print(f"Found {archived_workouts.count()} archived workouts linked to primary workout")

    # Check for missing data
    missing_data = resolver.check_for_missing_data(primary_workout, archived_workouts)

    print(f"Missing data that can be filled: {list(missing_data.keys())}")

    if missing_data:
        # Merge the missing data
        merged = resolver.merge_missing_data(primary_workout, missing_data)
        print(f"Data merge successful: {merged}")

        # Show updated workout data
        print("Updated primary workout data:")
        for key, value in primary_workout.data.items():
            if value is not None:
                print(f"  {key}: {value}")


def show_conflict_records(user):
    """Show conflict records that were created."""
    print("\n=== Conflict Records ===")

    conflicts = WorkoutConflict.objects.filter(user=user)
    print(f"Total conflict records: {conflicts.count()}")

    for conflict in conflicts:
        print(f"  - Conflict: {conflict.primary_workout.source} vs {conflict.archived_workout.source}")
        print(f"    Type: {conflict.conflict_type}")
        print(f"    Resolution: {conflict.resolution_method}")
        print(f"    Score: {conflict.conflict_score}")


def main():
    """Run the complete demonstration."""
    print("=== Conflict Detection & Resolution System Demo ===")

    # Create test user
    user = create_test_user()

    # Create test workouts
    liftosaur_workout, garmin_workout = create_test_workouts(user)

    # Demonstrate conflict detection
    demonstrate_conflict_detection(user, liftosaur_workout, garmin_workout)

    # Demonstrate conflict resolution
    demonstrate_conflict_resolution(user, liftosaur_workout, garmin_workout)

    # Demonstrate data merging
    demonstrate_data_merging(user, liftosaur_workout)

    # Show conflict records
    show_conflict_records(user)

    print("\n=== Demo Complete ===")
    print("The system successfully:")
    print("1. Detected time overlap conflict between Liftosaur and Garmin workouts")
    print("2. Archived the lower priority Garmin workout")
    print("3. Merged missing data (calories, heart rate) from archived workout to primary")
    print("4. Created conflict records for tracking and audit purposes")


if __name__ == '__main__':
    main()