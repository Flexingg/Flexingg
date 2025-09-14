import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import * #LEAVE AS IS*
from core.models import UserProfile
import json

logger = logging.getLogger(__name__)

def liftosaur_download(liftosaur_id):
    """
    Fetches the latest workout data from the Liftosaur API for a given user ID.
    """
    import requests
    url = f'https://api3.liftosaur.com/api/storage?tempuserid={liftosaur_id}'
    headers = {'Cookie': 'session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJwenppeGtkcnR1IiwiaWF0IjoxNzAwODczMjkxfQ.0z8ujfBvOL7ZJ6D9qFD9rnd5I31e9FvYNloWMc70iv4'}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Liftosaur API: {e}")
        return None

def convert_timestamp_to_datetime(ts):
    """Converts millisecond timestamp to a datetime object."""
    if ts:
        from datetime import datetime
        dt = datetime.fromtimestamp(ts / 1000.0)
        return timezone.make_aware(dt)
    return timezone.now()

def format_exercise_name(exercise_id):
    """Converts an exercise ID (str like 'squat_barbell' or dict {'id':, 'equipment':}) to formatted name like 'Squat (Barbell)'."""
    if isinstance(exercise_id, str):
        parts = exercise_id.split('_')
        name = parts[0].capitalize()
        if len(parts) > 1:
            equipment = ' '.join(p.capitalize() for p in parts[1:])
            return f"{name} ({equipment})"
        return name
    elif isinstance(exercise_id, dict):
        name = exercise_id.get('id', '').capitalize()
        equipment = exercise_id.get('equipment', '')
        if equipment:
            eq_parts = equipment.split()
            formatted_eq = ' '.join(p.capitalize() for p in eq_parts)
            return f"{name} ({formatted_eq})"
        return name
    else:
        return str(exercise_id).capitalize()
    
def parse_weight(weight_dict):
    """Extracts value and unit from a Liftosaur weight dict, defaulting to 0 lb if invalid."""
    if isinstance(weight_dict, dict) and 'value' in weight_dict and weight_dict['value'] is not None:
        return weight_dict['value'], weight_dict.get('unit', 'lb')
    return 0, 'lb'

def _process_liftosaur_data(user_id, data_input):
    """
    Internal function to process Liftosaur data (dict) into DB.
    """
    try:
        UserProfile = get_user_model()
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'error', 'message': 'User not found'}

    # Handle if json_data_str is already dict (from API) or str
    if isinstance(data_input, dict):
        data = data_input
        logger.info("Input was already a dict (from API)")
    else:
        try:
            data = json.loads(data_input)
            logger.info(f"Parsed JSON string for user {user_id}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for user {user_id}: {e}")
            return {'status': 'error', 'message': 'Invalid JSON string'}
        except Exception as e:
            logger.error(f"Unexpected error parsing string for user {user_id}: {e}")
            return {'status': 'error', 'message': 'Parsing failed'}

    if not isinstance(data, dict):
        logger.error(f"Data is not a dict for user {user_id}: {type(data)}")
        return {'status': 'error', 'message': 'Data is not a dict'}
    
    logger.info(f"Data keys for user {user_id}: {list(data.keys())}")
    storage = data.get('storage', {})
    logger.info(f"Storage keys for user {user_id}: {list(storage.keys()) if isinstance(storage, dict) else 'Not dict'}")
       

    storage = data.get('storage', {})
    stats = {
        '1rms': 0, 'body_measurements': 0, 'workouts': 0, 'workout_exercises': 0, 'workout_sets': 0,
        'programs': 0
    }

    with transaction.atomic():
        # Process 1RM from settings.exerciseData (key like 'squat_barbell')
        exercise_data = storage.get('settings', {}).get('exerciseData', {})
        for ex_key, details in exercise_data.items():
            rm1 = details.get('rm1')
            if rm1 and isinstance(rm1, dict) and 'value' in rm1:
                # ex_key is str like 'squat_barbell'
                ex_key_str = str(ex_key)
                if isinstance(ex_key, str):
                    parts = ex_key_str.split('_')
                    ex_id = parts[0]
                    eq = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    name = format_exercise_name({'id': ex_id, 'equipment': eq})
                else:
                    name = format_exercise_name(ex_key_str)
                exercise, created = Exercise.objects.get_or_create(
                    id=ex_key,
                    defaults={'name': name}
                )
                UserExerciseStat.objects.update_or_create(
                    user=user,
                    exercise=exercise,
                    defaults={'rm1_value': rm1['value'], 'rm1_unit': rm1['unit']}
                )
                stats['1rms'] += 1 if created else 0

        # Process bodyweight
        current_bw = storage.get('settings', {}).get('currentBodyweight')
        if current_bw and isinstance(current_bw, dict):
            BodyMeasurement.objects.update_or_create(
                user=user,
                measurement_type='bodyweight',
                defaults={
                    'value': current_bw.get('value'),
                    'unit': current_bw.get('unit'),
                    'timestamp': timezone.now()
                }
            )
            stats['body_measurements'] += 1

        # Process history
        history = storage.get('history', [])
        if isinstance(history, list):
            for hist in history:
                workout_id = hist.get('id')
                if not workout_id:
                    continue
                timestamp = convert_timestamp_to_datetime(hist.get('startTime') or hist.get('endTime'))
                program_id = hist.get('programId', hist.get('programName', 'Unknown'))
                workout, created = Workout.objects.update_or_create(
                    id=workout_id,
                    user=user,
                    defaults={
                        'timestamp': timestamp,
                        'name': hist.get('dayName', 'Workout'),
                        'program_id': program_id
                    }
                )
                stats['workouts'] += 1 if created else 0

                # Clear existing exercises for this workout to avoid duplicates
                workout.exercises.all().delete()

                # Process entries (exercises)
                entries = hist.get('entries', [])
                for entry in entries:
                    exercise_dict = entry.get('exercise', {})
                    exercise_name = format_exercise_name(exercise_dict)
                    exercise, _ = Exercise.objects.get_or_create(
                        id=f"{exercise_dict.get('id', '')}_{exercise_dict.get('equipment', '')}".strip('_'),
                        defaults={'name': exercise_name}
                    )
                    state = entry.get('state', {})
                    workout_exercise = WorkoutExercise.objects.create(
                        workout=workout,
                        exercise=exercise,
                        exercise_name=exercise_name,
                        note=entry.get('notes', ''),
                        timestamp=convert_timestamp_to_datetime(entry.get('timestamp')),
                        successes=state.get('successes', 0),
                        failures=state.get('failures', 0)
                    )
                    stats['workout_exercises'] += 1

                    # Process working sets
                    sets = entry.get('sets', [])
                    for idx, set_data in enumerate(sets, 1):
                        weight_val, weight_unit = parse_weight(set_data.get('weight', {}))
                        completed_weight_val, completed_weight_unit = parse_weight(set_data.get('completedWeight', {}))
                        WorkoutSet.objects.create(
                            workout_exercise=workout_exercise,
                            set_order=idx,
                            reps=set_data.get('reps'),
                            weight_value=weight_val,
                            weight_unit=weight_unit or 'lb',
                            completed_reps=set_data.get('completedReps', 0),
                            completed_weight_value=completed_weight_val or weight_val,
                            completed_weight_unit=completed_weight_unit or weight_unit,
                            rpe=set_data.get('rpe'),
                            completed_rpe=set_data.get('completedRpe'),
                            is_amrap=set_data.get('isAmrap', False),
                            is_completed=set_data.get('isCompleted', False),
                            timestamp=convert_timestamp_to_datetime(set_data.get('timestamp')),
                            is_warmup=False,
                            notes=set_data.get('label', '')
                        )
                        stats['workout_sets'] += 1

                    # Process warmup sets (negative order)
                    warmup_sets = entry.get('warmupSets', [])
                    for idx, warmup_data in enumerate(warmup_sets, 1):
                        weight_val, weight_unit = parse_weight(warmup_data.get('weight', {}))
                        WorkoutSet.objects.create(
                            workout_exercise=workout_exercise,
                            set_order=-idx,
                            reps=warmup_data.get('reps'),
                            weight_value=weight_val,
                            weight_unit=weight_unit or 'lb',
                            completed_reps=warmup_data.get('completedReps', warmup_data.get('reps', 0)),
                            completed_weight_value=weight_val,
                            completed_weight_unit=weight_unit,
                            is_completed=True,
                            is_warmup=True
                        )
                        stats['workout_sets'] += 1

        # Process programs
        programs = storage.get('programs', [])
        if isinstance(programs, list):
            for prog in programs:
                external_id = prog.get('id', prog.get('name', 'Unknown'))
                Program.objects.update_or_create(
                    user=user,
                    external_id=external_id,
                    defaults={'name': prog.get('name', 'Unknown'), 'data': prog}
                )
                stats['programs'] += 1

    logger.info(f"Import completed for user {user.username} with stats: {stats}")
    return {'status': 'success', 'stats': stats}


@shared_task
def sync_liftosaur_data(user_id, data):
    """
    Process already-fetched Liftosaur data for the user asynchronously.
    """
    if not data:
        logger.error(f"No data provided for user_id: {user_id}")
        return {'status': 'error', 'message': 'No data to process'}

    return _process_liftosaur_data(user_id, data)