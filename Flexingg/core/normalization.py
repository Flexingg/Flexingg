import logging
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


def normalize_garmin_activity_to_workout(activity):
    # Handle case where startTimeGMT might be a string or timestamp
    start_time_gmt = activity.get('startTimeGMT')
    start_time = None

    if isinstance(start_time_gmt, str):
        # Try to parse as datetime string first (format: "2023-11-23 09:36:51")
        try:
            # Handle both formats: "2023-11-23 09:36:51" and "2023-11-23T09:36:51"
            if 'T' in start_time_gmt:
                start_time = datetime.fromisoformat(start_time_gmt.replace('Z', '+00:00'))
            else:
                start_time = datetime.strptime(start_time_gmt, '%Y-%m-%d %H:%M:%S')
            start_time = timezone.make_aware(start_time)
        except (ValueError, TypeError):
            # If datetime parsing fails, try as Unix timestamp
            try:
                start_time_gmt = float(start_time_gmt)
                start_time = timezone.make_aware(datetime.fromtimestamp(start_time_gmt / 1000))
            except (ValueError, TypeError):
                logger.error(f"Failed to parse startTimeGMT '{start_time_gmt}' (type: {type(start_time_gmt)}) for activity {activity.get('activityId')}. Raw activity data: {activity}")
                return None
    elif isinstance(start_time_gmt, (int, float)):
        # Handle Unix timestamp
        start_time = timezone.make_aware(datetime.fromtimestamp(start_time_gmt / 1000))
    else:
        logger.error(f"Unknown startTimeGMT type: {type(start_time_gmt)} for activity {activity.get('activityId')}. Value: {start_time_gmt}. Raw activity data: {activity}")
        return None

    # Handle duration as well
    duration = activity.get('duration', 0)
    if isinstance(duration, str):
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration format: {duration} for activity {activity.get('activityId')}")
            duration = 0

    # Calculate end time
    if duration and duration > 0:
        end_time = start_time + timedelta(seconds=duration)
    else:
        # Fallback: assume 1 hour duration if not provided
        end_time = start_time + timedelta(hours=1)

    return {
        'source_id': activity.get('activityId'),
        'start_time': start_time,
        'end_time': end_time,
        'data': activity
    }


def normalize_liftosaur_workout(workout_data):
    start_time_ms = workout_data.get('startTime')
    end_time_ms = workout_data.get('endTime')

    # Check if startTime exists and is not None
    if start_time_ms is None:
        logger.warning(f"Missing startTime for Liftosaur workout: {workout_data.get('id', 'unknown')}")
        # Use current time as fallback
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=1)
    else:
        try:
            start_time = timezone.make_aware(datetime.fromtimestamp(start_time_ms / 1000))
            if end_time_ms:
                end_time = timezone.make_aware(datetime.fromtimestamp(end_time_ms / 1000))
            else:
                # Assume 1-hour workout if no end time
                end_time = start_time + timedelta(hours=1)
        except (ValueError, OSError) as e:
            logger.warning(f"Invalid timestamp {start_time_ms} for Liftosaur workout: {workout_data.get('id', 'unknown')}. Error: {e}")
            # Use current time as fallback
            start_time = timezone.now()
            end_time = start_time + timedelta(hours=1)

    return {
        'source_id': workout_data.get('id'),
        'start_time': start_time,
        'end_time': end_time,
        'data': workout_data
    }


def normalize_hc_sleep(sleep_session):
    try:
        start_str = sleep_session.get('start', '')
        if 'Z' in start_str:
            start_str = start_str.replace('Z', '')
        end_str = sleep_session.get('end', '')
        if 'Z' in end_str:
            end_str = end_str.replace('Z', '')

        # Parse the datetime strings
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)

        # Make them timezone-aware
        start_time = timezone.make_aware(start_dt)
        end_time = timezone.make_aware(end_dt)

        return {
            'source_id': sleep_session.get('_id'),
            'start_time': start_time,
            'end_time': end_time,
            'data': sleep_session
        }
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing Health Connect sleep data: {e}. Data: {sleep_session}")
        # Return None to skip this record
        return None


def normalize_hc_workout(exercise_session):
    try:
        start_str = exercise_session.get('start', '')
        if 'Z' in start_str:
            start_str = start_str.replace('Z', '')
        end_str = exercise_session.get('end', '')
        if 'Z' in end_str:
            end_str = end_str.replace('Z', '')

        # Parse the datetime strings
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)

        # Make them timezone-aware
        start_time = timezone.make_aware(start_dt)
        end_time = timezone.make_aware(end_dt)

        return {
            'source_id': exercise_session.get('_id'),
            'start_time': start_time,
            'end_time': end_time,
            'data': exercise_session
        }
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing Health Connect workout data: {e}. Data: {exercise_session}")
        # Return None to skip this record
        return None


def normalize_garmin_steps(day):
    return {
        'date': datetime.strptime(day.get('calendarDate'), '%Y-%m-%d').date(),
        'steps': day.get('totalSteps'),
        'data': day
    }


def normalize_hc_steps(steps_record):
    try:
        start_str = steps_record.get('start', '')
        if 'Z' in start_str:
            start_str = start_str.replace('Z', '')

        # Parse the datetime and make it timezone-aware
        start_dt = datetime.fromisoformat(start_str)
        record_date = timezone.make_aware(start_dt).date()

        return {
            'date': record_date,
            'steps': steps_record.get('data', {}).get('count'),
            'data': steps_record
        }
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing Health Connect steps data: {e}. Data: {steps_record}")
        # Return None to skip this record
        return None


def normalize_garmin_hydration(day):
    logger.debug(f"Normalizing Garmin hydration data: {day}")

    # Extract the actual hydration value in milliliters
    value_ml = day.get('valueInML')
    goal_ml = day.get('goalInML')

    if value_ml is not None and value_ml > 0:
        hydration_ml = value_ml
        logger.debug(f"Using valueInML: {hydration_ml}")
    elif goal_ml is not None and goal_ml > 0:
        hydration_ml = goal_ml
        logger.debug(f"Using goalInML: {hydration_ml}")
    else:
        logger.debug(f"No valid hydration data found in: {day}")
        return None

    # Convert milliliters to ounces (1 ml = 0.033814 ounces)
    amount_ounces = hydration_ml * 0.033814
    logger.debug(f"Converted {hydration_ml} ml to {amount_ounces} ounces")

    return {
        'date': datetime.strptime(day.get('calendarDate'), '%Y-%m-%d').date(),
        'amount_ounces': amount_ounces,
        'data': day
    }


def normalize_hc_hydration(hydration_record):
    try:
        start_str = hydration_record.get('start', '')
        if 'Z' in start_str:
            start_str = start_str.replace('Z', '')

        # Parse the datetime and make it timezone-aware
        start_dt = datetime.fromisoformat(start_str)
        record_date = timezone.make_aware(start_dt).date()

        data = hydration_record.get('data', {})
        hydration_amount = data.get('volume')

        if hydration_amount is None:
            return None

        # Convert to ounces (assume liters)
        hydration_ounces = Decimal(str(hydration_amount * 33.814))

        return {
            'date': record_date,
            'amount_ounces': hydration_ounces,
            'data': hydration_record
        }
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing Health Connect hydration data: {e}. Data: {hydration_record}")
        return None


__all__ = [
    'normalize_garmin_activity_to_workout',
    'normalize_liftosaur_workout',
    'normalize_hc_sleep',
    'normalize_hc_workout',
    'normalize_garmin_steps',
    'normalize_hc_steps',
    'normalize_garmin_hydration',
    'normalize_hc_hydration',
]