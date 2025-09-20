"""
Conflict detection utilities for workout data from different sources.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from .models import Workout, ArchivedWorkout, WorkoutConflict, DataPriority

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detects conflicts between workout data from different sources."""

    def __init__(self, user):
        self.user = user
        self.priorities = self._get_priorities()

    def _get_priorities(self):
        """Get user's data priorities."""
        priorities = {}
        for priority in DataPriority.objects.filter(user=self.user, data_type='workout'):
            priorities[priority.source] = priority.rank
        return priorities

    def detect_conflicts(self, new_workout_data, existing_workouts):
        """
        Detect conflicts between new workout data and existing workouts.

        Args:
            new_workout_data: Dict with workout data from a source
            existing_workouts: List of existing Workout objects

        Returns:
            List of conflict dictionaries
        """
        conflicts = []

        for existing_workout in existing_workouts:
            conflict = self._check_conflict(new_workout_data, existing_workout)
            if conflict:
                conflicts.append(conflict)

        return conflicts

    def _check_conflict(self, new_workout, existing_workout):
        """Check for conflict between two workouts."""
        # Time overlap conflict (within 30 minutes)
        time_overlap = abs((new_workout['start_time'] - existing_workout.start_time).total_seconds()) < 1800

        if time_overlap:
            return {
                'type': 'time_overlap',
                'confidence': 0.9,
                'description': f"Workouts overlap in time: {new_workout['source']} vs {existing_workout.source}"
            }

        # Same day, different data (for steps, sleep, etc.)
        same_day = (new_workout['start_time'].date() == existing_workout.start_time.date() and
                   new_workout.get('data_type') == existing_workout.data.get('data_type'))

        if same_day:
            return {
                'type': 'data_mismatch',
                'confidence': 0.7,
                'description': f"Same day different data: {new_workout['source']} vs {existing_workout.source}"
            }

        return None

    def calculate_conflict_score(self, conflict_type, workout1_data, workout2_data):
        """Calculate confidence score for a conflict."""
        base_scores = {
            'time_overlap': 0.9,
            'data_mismatch': 0.7,
            'duplicate_activity': 0.8
        }

        score = base_scores.get(conflict_type, 0.5)

        # Adjust based on data completeness
        if workout1_data.get('data') and workout2_data.get('data'):
            completeness1 = self._calculate_data_completeness(workout1_data['data'])
            completeness2 = self._calculate_data_completeness(workout2_data['data'])

            # Higher completeness increases confidence
            avg_completeness = (completeness1 + completeness2) / 2
            score = min(1.0, score + (avg_completeness * 0.1))

        return score

    def _calculate_data_completeness(self, data):
        """Calculate how complete the workout data is (0-1)."""
        completeness = 0
        checks = 0

        # Check for basic fields
        if data.get('calories'):
            completeness += 0.2
        checks += 1

        if data.get('heartRate'):
            completeness += 0.2
        checks += 1

        if data.get('duration'):
            completeness += 0.2
        checks += 1

        if data.get('distance'):
            completeness += 0.2
        checks += 1

        if data.get('steps'):
            completeness += 0.2
        checks += 1

        return completeness if checks > 0 else 0


class ConflictResolver:
    """Resolves conflicts between workout data sources."""

    def __init__(self, user):
        self.user = user
        self.detector = ConflictDetector(user)

    def resolve_conflicts(self, primary_workout, conflicting_workouts):
        """
        Resolve conflicts by archiving lower priority workouts.

        Args:
            primary_workout: The higher priority workout to keep
            conflicting_workouts: List of lower priority workouts to archive
        """
        archived_workouts = []

        for conflict_workout in conflicting_workouts:
            # Archive the lower priority workout
            archived = self._archive_workout(conflict_workout, primary_workout)
            archived_workouts.append(archived)

            # Create conflict record
            self._create_conflict_record(primary_workout, archived)

        return archived_workouts

    def _archive_workout(self, workout, primary_workout):
        """Archive a workout that conflicts with a higher priority one."""
        archived = ArchivedWorkout.objects.create(
            user=workout.user,
            source=workout.source,
            source_id=workout.source_id,
            start_time=workout.start_time,
            end_time=workout.end_time,
            duration_seconds=workout.duration_seconds,
            data=workout.data,
            archived_reason='lower_priority',
            linked_primary_workout=primary_workout
        )

        # Delete the original workout
        workout.delete()

        logger.info(f"Archived workout {workout.id} due to conflict with {primary_workout.id}")
        return archived

    def _create_conflict_record(self, primary_workout, archived_workout):
        """Create a record of the conflict resolution."""
        WorkoutConflict.objects.create(
            user=self.user,
            primary_workout=primary_workout,
            archived_workout=archived_workout,
            conflict_type='time_overlap',  # Default, could be more specific
            conflict_score=0.9,
            resolution_method='auto_priority'
        )

    def check_for_missing_data(self, primary_workout, archived_workouts):
        """
        Check if primary workout is missing data that archived workouts have.

        Returns:
            Dict of missing data that can be filled from archived workouts
        """
        missing_data = {}
        primary_data = primary_workout.data or {}

        # Check for missing heart rate data
        if not primary_data.get('heartRate') and not primary_data.get('averageHR'):
            for archived in archived_workouts:
                archived_data = archived.data or {}
                if archived_data.get('heartRate') or archived_data.get('averageHR'):
                    missing_data['heart_rate'] = {
                        'source': archived.source,
                        'data': archived_data.get('heartRate') or archived_data.get('averageHR')
                    }
                    break

        # Check for missing GPS/location data
        if not primary_data.get('location') and not primary_data.get('coordinates'):
            for archived in archived_workouts:
                archived_data = archived.data or {}
                if archived_data.get('location') or archived_data.get('coordinates'):
                    missing_data['location'] = {
                        'source': archived.source,
                        'data': archived_data.get('location') or archived_data.get('coordinates')
                    }
                    break

        # Check for missing calories
        if not primary_data.get('calories'):
            for archived in archived_workouts:
                archived_data = archived.data or {}
                if archived_data.get('calories'):
                    missing_data['calories'] = {
                        'source': archived.source,
                        'data': archived_data.get('calories')
                    }
                    break

        return missing_data

    def merge_missing_data(self, primary_workout, missing_data):
        """Merge missing data from archived workouts into primary workout."""
        if not missing_data:
            return False

        updated = False
        primary_data = primary_workout.data or {}

        for data_type, data_info in missing_data.items():
            if data_type == 'heart_rate':
                primary_data['heartRate'] = data_info['data']
                primary_data['heartRateSource'] = data_info['source']
                updated = True
            elif data_type == 'location':
                primary_data['location'] = data_info['data']
                primary_data['locationSource'] = data_info['source']
                updated = True
            elif data_type == 'calories':
                primary_data['calories'] = data_info['data']
                primary_data['caloriesSource'] = data_info['source']
                updated = True

        if updated:
            primary_workout.data = primary_data
            primary_workout.save()
            logger.info(f"Merged missing data into workout {primary_workout.id}")

        return updated