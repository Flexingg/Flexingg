
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import * #LEAVE AS IS*
from core.models import UserProfile, Workout, UnifiedWorkoutExercise, UnifiedWorkoutSet
import json

logger = logging.getLogger(__name__)


@shared_task
def sync_liftosaur_data(user_id, data, session_token=None):
    """
    Process already-fetched Liftosaur data for the user asynchronously.
    """
    if not data:
        logger.error(f"No data provided for user_id: {user_id}")
        return {'status': 'error', 'message': 'No data to process'}

    return _process_liftosaur_data(user_id, data, session_token)

def _process_liftosaur_data(user_id, data, session_token=None):
    """
    Process Liftosaur JSON data to populate unified Workout models.
    Assumes data is a dict with 'workouts' key containing list of workout dicts.
    Each workout has 'id', 'timestamp', 'name', 'exercises' list.
    Each exercise has 'exercise_name', 'note', 'timestamp', 'sets' list.
    Each set has 'set_order', 'reps', 'weight_value', 'weight_unit', 'completed_reps', 'completed_weight_value', 'completed_weight_unit', 'rpe', 'completed_rpe', 'is_amrap', 'timestamp', 'notes'.
    """
    from core.models import UserProfile, Workout, UnifiedWorkoutExercise, UnifiedWorkoutSet
    from django.utils import timezone
    from django.db import transaction
    import logging
    logger = logging.getLogger(__name__)

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'error', 'message': 'User not found'}

    processed = 0
    with transaction.atomic():
        for workout_data in data.get('workouts', []):
            source_id = workout_data.get('id')
            if not source_id:
                logger.warning("Skipping workout without ID")
                continue

            if Workout.objects.filter(user=user, source='liftosaur', source_id=source_id).exists():
                logger.info(f"Workout {source_id} already exists for user {user_id}")
                continue

            start_time = timezone.datetime.fromisoformat(workout_data.get('timestamp', timezone.now().isoformat()))
            end_time = start_time + timezone.timedelta(seconds=workout_data.get('duration_seconds', 0))
            duration_seconds = workout_data.get('duration_seconds')

            workout = Workout.objects.create(
                user=user,
                source='liftosaur',
                source_id=source_id,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                data=workout_data
            )

            for exercise_data in workout_data.get('exercises', []):
                exercise_name = exercise_data.get('exercise_name', '')
                note = exercise_data.get('note')
                exercise_timestamp = timezone.datetime.fromisoformat(exercise_data.get('timestamp', start_time.isoformat())) if exercise_data.get('timestamp') else None

                exercise = UnifiedWorkoutExercise.objects.create(
                    workout=workout,
                    exercise_name=exercise_name,
                    note=note,
                    timestamp=exercise_timestamp,
                    successes=exercise_data.get('successes', 0),
                    failures=exercise_data.get('failures', 0)
                )

                for set_data in exercise_data.get('sets', []):
                    set_order = set_data.get('set_order', 0)
                    reps = set_data.get('reps')
                    weight_value = set_data.get('weight_value')
                    weight_unit = set_data.get('weight_unit', 'lb')
                    completed_reps = set_data.get('completed_reps', 0)
                    completed_weight_value = set_data.get('completed_weight_value')
                    completed_weight_unit = set_data.get('completed_weight_unit')
                    rpe = set_data.get('rpe')
                    completed_rpe = set_data.get('completed_rpe')
                    is_amrap = set_data.get('is_amrap', False)
                    is_completed = set_data.get('is_completed', False)
                    set_timestamp = timezone.datetime.fromisoformat(set_data.get('timestamp', start_time.isoformat())) if set_data.get('timestamp') else None
                    is_warmup = set_data.get('is_warmup', False)
                    notes = set_data.get('notes', '')

                    UnifiedWorkoutSet.objects.create(
                        workout_exercise=exercise,
                        set_order=set_order,
                        reps=reps,
                        weight_value=weight_value,
                        weight_unit=weight_unit,
                        completed_reps=completed_reps,
                        completed_weight_value=completed_weight_value,
                        completed_weight_unit=completed_weight_unit,
                        rpe=rpe,
                        completed_rpe=completed_rpe,
                        is_amrap=is_amrap,
                        is_completed=is_completed,
                        timestamp=set_timestamp,
                        is_warmup=is_warmup,
                        notes=notes
                    )

                processed += 1

    logger.info(f"Processed {processed} workouts for user {user_id}")
    return {'status': 'success', 'processed': processed}
@shared_task
def normalize_liftosaur_weight_data(user_id):
    """
    Normalize existing Liftosaur BodyMeasurement data to unified BodyWeight model.
    """
    from core.models import BodyWeight
    from .models import BodyMeasurement
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

    try:
        user_measurements = BodyMeasurement.objects.filter(
            user_id=user_id,
            measurement_type='bodyweight'
        )

        normalized_count = 0

        with transaction.atomic():
            for measurement in user_measurements:
                # Check if already normalized
                if BodyWeight.objects.filter(
                    user_id=user_id,
                    source='liftosaur',
                    source_id=str(measurement.id)
                ).exists():
                    continue

                # Convert weight to lbs if needed
                weight_lbs = measurement.value
                if measurement.unit == 'kg':
                    weight_lbs = measurement.value * 2.20462

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='liftosaur',
                    source_id=str(measurement.id),
                    datetime=measurement.timestamp,
                    weight_lbs=weight_lbs,
                    data={
                        'original_unit': measurement.unit,
                        'original_value': measurement.value,
                        'measurement_type': measurement.measurement_type
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing weight data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}