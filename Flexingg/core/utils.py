import logging
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

def liftosaur_download(liftosaur_id, session_token):
    """
    Fetches the latest workout data from the Liftosaur API for a given user ID.
    """
    url = f'https://api3.liftosaur.com/api/storage?tempuserid={liftosaur_id}'
    headers = {'Cookie': f'session={session_token}'}

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

from .models import DataPriority, DailySteps, BodyWeight, Sleep, Workout, DailyWater, NutritionEntry
from django.db.models import Q
from datetime import datetime, date
from typing import Optional, List, Dict, Any


def get_prioritized_data_source(user, data_type: str) -> Optional[str]:
    """
    Get the highest priority data source for a given data type for a user.
    Returns the source name (e.g., 'garmin', 'healthconnect', 'liftosaur') or None if no priority set.
    """
    try:
        priority = DataPriority.objects.filter(
            user=user,
            data_type=data_type
        ).order_by('rank').first()

        return priority.source if priority else None
    except DataPriority.DoesNotExist:
        return None


def get_aggregated_steps(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get total steps from prioritized sources within date range.
    Returns dict with total steps and source breakdown.
    """
    # Get prioritized source
    primary_source = get_prioritized_data_source(user, 'steps')

    if not primary_source:
        return {'total_steps': 0, 'sources': {}, 'primary_source': None}

    # Query unified steps data
    steps_data = DailySteps.objects.filter(
        user=user,
        date__range=[start_date, end_date]
    ).order_by('date')

    # Group by source and calculate totals
    source_totals = {}
    total_steps = 0

    for step_record in steps_data:
        source = step_record.source
        if source not in source_totals:
            source_totals[source] = 0
        source_totals[source] += step_record.steps
        total_steps += step_record.steps

    return {
        'total_steps': total_steps,
        'sources': source_totals,
        'primary_source': primary_source,
        'date_range': {'start': start_date, 'end': end_date}
    }


def get_aggregated_body_weight(user, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Get body weight measurements from all sources within date range.
    Returns dict with weight entries and source breakdown.
    """
    # Build query
    query = Q(user=user)
    if start_date:
        query &= Q(datetime__date__gte=start_date)
    if end_date:
        query &= Q(datetime__date__lte=end_date)

    weight_data = BodyWeight.objects.filter(query).order_by('-datetime')

    # Group by source
    source_weights = {}
    all_weights = []

    for weight_record in weight_data:
        source = weight_record.source
        if source not in source_weights:
            source_weights[source] = []

        weight_entry = {
            'datetime': weight_record.datetime,
            'weight_lbs': weight_record.weight_lbs,
            'source_id': weight_record.source_id,
            'data': weight_record.data
        }
        source_weights[source].append(weight_entry)
        all_weights.append(weight_entry)

    return {
        'weights': all_weights,
        'sources': source_weights,
        'total_entries': len(all_weights),
        'date_range': {'start': start_date, 'end': end_date} if start_date and end_date else None
    }


def get_aggregated_sleep(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get sleep data from prioritized sources within date range.
    Returns dict with sleep entries and source breakdown.
    """
    # Get prioritized source
    primary_source = get_prioritized_data_source(user, 'sleep')

    if not primary_source:
        return {'total_entries': 0, 'sources': {}, 'primary_source': None}

    # Query unified sleep data
    sleep_data = Sleep.objects.filter(
        user=user,
        start_time__date__range=[start_date, end_date]
    ).order_by('-start_time')

    # Group by source
    source_sleep = {}
    all_sleep = []

    for sleep_record in sleep_data:
        source = sleep_record.source
        if source not in source_sleep:
            source_sleep[source] = []

        sleep_entry = {
            'start_time': sleep_record.start_time,
            'end_time': sleep_record.end_time,
            'source_id': sleep_record.source_id,
            'data': sleep_record.data
        }
        source_sleep[source].append(sleep_entry)
        all_sleep.append(sleep_entry)

    return {
        'sleep_entries': all_sleep,
        'sources': source_sleep,
        'total_entries': len(all_sleep),
        'primary_source': primary_source,
        'date_range': {'start': start_date, 'end': end_date}
    }


def get_aggregated_workouts(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get workout data from all sources within date range.
    Returns dict with workout entries and source breakdown.
    """
    # Query unified workout data
    workout_data = Workout.objects.filter(
        user=user,
        start_time__date__range=[start_date, end_date]
    ).order_by('-start_time')

    # Group by source
    source_workouts = {}
    all_workouts = []

    for workout_record in workout_data:
        source = workout_record.source
        if source not in source_workouts:
            source_workouts[source] = []

        workout_entry = {
            'start_time': workout_record.start_time,
            'end_time': workout_record.end_time,
            'duration_seconds': workout_record.duration_seconds,
            'source_id': workout_record.source_id,
            'data': workout_record.data
        }
        source_workouts[source].append(workout_entry)
        all_workouts.append(workout_entry)

    return {
        'workouts': all_workouts,
        'sources': source_workouts,
        'total_workouts': len(all_workouts),
        'date_range': {'start': start_date, 'end': end_date}
    }


def get_aggregated_water(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get water intake data from all sources within date range.
    Returns dict with water entries and source breakdown.
    """
    # Query unified water data
    water_data = DailyWater.objects.filter(
        user=user,
        date__range=[start_date, end_date]
    ).order_by('-date')

    # Group by source and calculate totals
    source_totals = {}
    source_entries = {}
    total_ounces = 0
    all_entries = []

    for water_record in water_data:
        source = water_record.source
        if source not in source_totals:
            source_totals[source] = 0
            source_entries[source] = []

        source_totals[source] += water_record.amount_ounces
        total_ounces += water_record.amount_ounces

        water_entry = {
            'date': water_record.date,
            'amount_ounces': water_record.amount_ounces,
            'source_id': water_record.source_id,
            'data': water_record.data
        }
        source_entries[source].append(water_entry)
        all_entries.append(water_entry)

    return {
        'total_ounces': total_ounces,
        'entries': all_entries,
        'sources': source_entries,
        'source_totals': source_totals,
        'total_entries': len(all_entries),
        'date_range': {'start': start_date, 'end': end_date}
    }


def get_aggregated_nutrition(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get nutrition data from all sources within date range.
    Returns dict with nutrition entries and source breakdown.
    """
    # Query unified nutrition data
    nutrition_data = NutritionEntry.objects.filter(
        user=user,
        datetime__date__range=[start_date, end_date]
    ).order_by('-datetime')

    # Group by source
    source_nutrition = {}
    all_entries = []

    # Calculate totals
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    for nutrition_record in nutrition_data:
        source = nutrition_record.source
        if source not in source_nutrition:
            source_nutrition[source] = []

        nutrition_entry = {
            'datetime': nutrition_record.datetime,
            'food_name': nutrition_record.food_name,
            'calories': nutrition_record.calories,
            'protein_grams': nutrition_record.protein_grams,
            'fat_grams': nutrition_record.fat_grams,
            'carbs_grams': nutrition_record.carbs_grams,
            'quantity_description': nutrition_record.quantity_description,
            'quantity_grams': nutrition_record.quantity_grams,
            'source_id': nutrition_record.source_id,
            'data': nutrition_record.data
        }
        source_nutrition[source].append(nutrition_entry)
        all_entries.append(nutrition_entry)

        # Add to totals if values exist
        if nutrition_record.calories:
            total_calories += nutrition_record.calories
        if nutrition_record.protein_grams:
            total_protein += nutrition_record.protein_grams
        if nutrition_record.fat_grams:
            total_fat += nutrition_record.fat_grams
        if nutrition_record.carbs_grams:
            total_carbs += nutrition_record.carbs_grams

    return {
        'entries': all_entries,
        'sources': source_nutrition,
        'total_entries': len(all_entries),
        'totals': {
            'calories': total_calories,
            'protein_grams': total_protein,
            'fat_grams': total_fat,
            'carbs_grams': total_carbs
        },
        'date_range': {'start': start_date, 'end': end_date}
    }


def get_user_fitness_summary(user, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Get a comprehensive fitness summary for a user within date range.
    Combines data from all sources using priority system where applicable.
    """
    return {
        'steps': get_aggregated_steps(user, start_date, end_date),
        'weight': get_aggregated_body_weight(user, start_date, end_date),
        'sleep': get_aggregated_sleep(user, start_date, end_date),
        'workouts': get_aggregated_workouts(user, start_date, end_date),
        'water': get_aggregated_water(user, start_date, end_date),
        'nutrition': get_aggregated_nutrition(user, start_date, end_date),
        'date_range': {'start': start_date, 'end': end_date}
    }