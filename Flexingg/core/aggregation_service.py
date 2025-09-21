import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime
from django.db.models import Q

from .models import DataPriority, DailySteps, BodyWeight, Sleep, Workout, DailyWater, NutritionEntry

logger = logging.getLogger(__name__)


def get_prioritized_data_source(user, data_type: str) -> Optional[str]:
    """
    Get the highest priority data source for a given data type for a user.
    Returns the source name (e.g., 'garmin', 'healthconnect', 'liftosaur') or None if no priority set.
    """
    try:
        # Check if user is authenticated before querying database
        if not user or not getattr(user, 'is_authenticated', False):
            return None

        priority = DataPriority.objects.filter(
            user=user,
            data_type=data_type
        ).order_by('rank').first()

        return priority.source if priority else None
    except Exception:
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
    source_totals: Dict[str, int] = {}
    total_steps = 0

    for step_record in steps_data:
        source = step_record.source
        if source not in source_totals:
            source_totals[source] = 0
        source_totals[source] += step_record.steps or 0
        total_steps += step_record.steps or 0

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
    source_weights: Dict[str, List[Dict[str, Any]]] = {}
    all_weights: List[Dict[str, Any]] = []

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
    source_sleep: Dict[str, List[Dict[str, Any]]] = {}
    all_sleep: List[Dict[str, Any]] = []

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
    source_workouts: Dict[str, List[Dict[str, Any]]] = {}
    all_workouts: List[Dict[str, Any]] = []

    for workout_record in workout_data:
        source = workout_record.source
        if source not in source_workouts:
            source_workouts[source] = []

        workout_entry = {
            'start_time': workout_record.start_time,
            'end_time': workout_record.end_time,
            'duration_seconds': getattr(workout_record, 'duration_seconds', None),
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
    source_totals: Dict[str, float] = {}
    source_entries: Dict[str, List[Dict[str, Any]]] = {}
    total_ounces = 0.0
    all_entries: List[Dict[str, Any]] = []

    for water_record in water_data:
        source = water_record.source
        if source not in source_totals:
            source_totals[source] = 0.0
            source_entries[source] = []

        source_totals[source] += float(water_record.amount_ounces)
        total_ounces += float(water_record.amount_ounces)

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
    source_nutrition: Dict[str, List[Dict[str, Any]]] = {}
    all_entries: List[Dict[str, Any]] = []

    # Calculate totals
    total_calories = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0

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
            total_calories += float(nutrition_record.calories)
        if nutrition_record.protein_grams:
            total_protein += float(nutrition_record.protein_grams)
        if nutrition_record.fat_grams:
            total_fat += float(nutrition_record.fat_grams)
        if nutrition_record.carbs_grams:
            total_carbs += float(nutrition_record.carbs_grams)

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
    # Check if user is authenticated before querying database
    if not user or not getattr(user, 'is_authenticated', False):
        return {
            'steps': {'total_steps': 0, 'sources': {}, 'primary_source': None, 'date_range': {'start': start_date, 'end': end_date}},
            'weight': {'weights': [], 'sources': {}, 'total_entries': 0, 'date_range': {'start': start_date, 'end': end_date}},
            'sleep': {'total_entries': 0, 'sources': {}, 'primary_source': None, 'date_range': {'start': start_date, 'end': end_date}},
            'workouts': {'workouts': [], 'sources': {}, 'total_workouts': 0, 'date_range': {'start': start_date, 'end': end_date}},
            'water': {'total_ounces': 0, 'entries': [], 'sources': {}, 'source_totals': {}, 'total_entries': 0, 'date_range': {'start': start_date, 'end': end_date}},
            'nutrition': {'entries': [], 'sources': {}, 'total_entries': 0, 'totals': {'calories': 0, 'protein_grams': 0, 'fat_grams': 0, 'carbs_grams': 0}, 'date_range': {'start': start_date, 'end': end_date}},
            'date_range': {'start': start_date, 'end': end_date}
        }

    return {
        'steps': get_aggregated_steps(user, start_date, end_date),
        'weight': get_aggregated_body_weight(user, start_date, end_date),
        'sleep': get_aggregated_sleep(user, start_date, end_date),
        'workouts': get_aggregated_workouts(user, start_date, end_date),
        'water': get_aggregated_water(user, start_date, end_date),
        'nutrition': get_aggregated_nutrition(user, start_date, end_date),
        'date_range': {'start': start_date, 'end': end_date}
    }