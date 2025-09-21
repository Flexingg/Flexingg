import logging
from django.utils import timezone
from datetime import datetime
from typing import Tuple, Any

logger = logging.getLogger(__name__)


def convert_timestamp_to_datetime(ts: Any) -> datetime:
    """Converts millisecond timestamp to a timezone-aware datetime object."""
    if ts:
        dt = datetime.fromtimestamp(ts / 1000.0)
        return timezone.make_aware(dt)
    return timezone.now()


def format_exercise_name(exercise_id: Any) -> str:
    """
    Converts an exercise ID (str like 'squat_barbell' or dict {'id':..., 'equipment':...})
    to formatted name like 'Squat (Barbell)'.
    """
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


def parse_weight(weight_dict: Any) -> Tuple[float, str]:
    """Extracts value and unit from a Liftosaur weight dict, defaulting to 0 lb if invalid."""
    if isinstance(weight_dict, dict) and 'value' in weight_dict and weight_dict['value'] is not None:
        return weight_dict['value'], weight_dict.get('unit', 'lb')
    return 0, 'lb'


__all__ = [
    'convert_timestamp_to_datetime',
    'format_exercise_name',
    'parse_weight',
]