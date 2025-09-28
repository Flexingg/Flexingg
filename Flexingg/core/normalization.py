import logging
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


def normalize_garmin_activity_to_workout(activity):
    # Handle case where startTimeGMT might be a string or timestamp
    start_time_gmt = activity.get('startTimeGMT')
    start_time = None

    def _ts_to_datetime(ts_value):
        """
        Convert a numeric timestamp (seconds or milliseconds) to a timezone-aware datetime.
        Many APIs sometimes return seconds (1.6e9) or milliseconds (1.6e12).
        We detect magnitude: values > 1e11 are treated as milliseconds.
        """
        try:
            val = float(ts_value)
        except (TypeError, ValueError):
            return None
        # If very large, assume milliseconds; otherwise seconds
        if abs(val) > 1e11:
            # milliseconds -> seconds
            sec = val / 1000.0
        else:
            sec = val
        # Use timezone-aware UTC datetime
        try:
            return datetime.fromtimestamp(sec, tz=timezone.utc)
        except Exception:
            try:
                # Fallback: naive datetime then make aware
                return timezone.make_aware(datetime.fromtimestamp(sec))
            except Exception:
                return None

    if isinstance(start_time_gmt, str):
        # Try to parse as datetime string first (format: "2023-11-23 09:36:51" or ISO)
        try:
            # Handle both formats: "2023-11-23 09:36:51" and "2023-11-23T09:36:51"
            if 'T' in start_time_gmt:
                start_time = datetime.fromisoformat(start_time_gmt.replace('Z', '+00:00'))
                if start_time.tzinfo is None:
                    start_time = timezone.make_aware(start_time)
            else:
                # Try common space-separated format
                start_time = datetime.strptime(start_time_gmt, '%Y-%m-%d %H:%M:%S')
                start_time = timezone.make_aware(start_time)
        except (ValueError, TypeError):
            # If datetime parsing fails, try as numeric timestamp (string containing digits)
            dt = _ts_to_datetime(start_time_gmt)
            if dt:
                start_time = dt
            else:
                logger.error(f"Failed to parse startTimeGMT '{start_time_gmt}' (type: {type(start_time_gmt)}) for activity {activity.get('activityId')}. Raw activity data: {activity}")
                return None
    elif isinstance(start_time_gmt, (int, float)):
        # Convert numeric timestamp, detect ms vs s
        dt = _ts_to_datetime(start_time_gmt)
        if dt:
            start_time = dt
        else:
            logger.error(f"Failed to convert numeric startTimeGMT '{start_time_gmt}' for activity {activity.get('activityId')}. Raw activity data: {activity}")
            return None
    else:
        logger.error(f"Unknown startTimeGMT type: {type(start_time_gmt)} for activity {activity.get('activityId')}. Value: {start_time_gmt}. Raw activity data: {activity}")
        return None

    # Ensure start_time is timezone-aware; coerce if necessary
    if start_time and start_time.tzinfo is None:
        start_time = timezone.make_aware(start_time)

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


def normalize_garmin_sleep(sleep_obj):
    """
    Accepts either a garth.SleepData (Pydantic-like) or a raw dict from the Connect API.
    Returns dict {'source_id','start_time','end_time','data'} with timezone-aware datetimes,
    or None on failure.
    """
    try:
        # Try to locate the daily sleep DTO inside the object/dict
        daily = None
        if hasattr(sleep_obj, 'daily_sleep_dto'):
            daily = getattr(sleep_obj, 'daily_sleep_dto')
        elif isinstance(sleep_obj, dict) and 'dailySleepDTO' in sleep_obj:
            daily = sleep_obj['dailySleepDTO']
        elif isinstance(sleep_obj, dict):
            # Common alternative keys
            for k in ('dailySleepDTO', 'daily_sleep_dto', 'sleep', 'sleepData', 'daily_sleep'):
                if k in sleep_obj:
                    daily = sleep_obj[k]
                    break

        # If daily is still None, maybe the dict itself is the DTO
        if not daily:
            if isinstance(sleep_obj, dict) and any(k in sleep_obj for k in ('id', 'sleep_start_timestamp_gmt', 'sleep_end_timestamp_gmt', 'calendarDate')):
                daily = sleep_obj
            else:
                logger.warning("No dailySleepDTO found in Garmin sleep object; skipping record.")
                return None

        # Extract an identifier
        sid = None
        if hasattr(daily, 'id'):
            sid = getattr(daily, 'id')
        elif isinstance(daily, dict):
            sid = daily.get('id') or daily.get('samplePk') or daily.get('dailySleepId')

        # Helper: convert numeric (s or ms), ISO string, or datetime to timezone-aware datetime
        from django.utils import timezone
        from datetime import datetime
        def to_dt(v):
            if v is None:
                return None
            if isinstance(v, datetime):
                return timezone.make_aware(v) if v.tzinfo is None else v
            # Try numeric epoch (ms or s)
            try:
                val = float(v)
                # Heuristic: values > 1e11 are milliseconds
                if abs(val) > 1e11:
                    sec = val / 1000.0
                else:
                    sec = val
                return datetime.fromtimestamp(sec, tz=timezone.utc)
            except Exception:
                # Try ISO parsing
                try:
                    s = str(v).replace('Z', '+00:00')
                    dt = datetime.fromisoformat(s)
                    return timezone.make_aware(dt) if dt.tzinfo is None else dt
                except Exception:
                    return None

        # Common field names observed in garth examples
        start_ts = None
        end_ts = None
        if hasattr(daily, 'sleep_start_timestamp_gmt'):
            start_ts = getattr(daily, 'sleep_start_timestamp_gmt')
        elif isinstance(daily, dict):
            start_ts = daily.get('sleep_start_timestamp_gmt') or daily.get('sleepStartTimestampGmt') or daily.get('sleepStartTimestamp')

        if hasattr(daily, 'sleep_end_timestamp_gmt'):
            end_ts = getattr(daily, 'sleep_end_timestamp_gmt')
        elif isinstance(daily, dict):
            end_ts = daily.get('sleep_end_timestamp_gmt') or daily.get('sleepEndTimestampGmt') or daily.get('sleepEndTimestamp')

        start_time = to_dt(start_ts)
        end_time = to_dt(end_ts)

        # Return normalized dict (store raw payload under 'data')
        return {
            'source_id': str(sid) if sid is not None else (str(int(start_time.timestamp())) if start_time else None),
            'start_time': start_time,
            'end_time': end_time,
            'data': sleep_obj
        }
    except Exception as e:
        logger.exception(f"normalize_garmin_sleep error: {e}")
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
    'normalize_garmin_sleep',
]