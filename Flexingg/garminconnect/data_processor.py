import logging
from decimal import Decimal
from datetime import timedelta, datetime as _datetime
from django.utils import timezone

from core.models import Transaction, UserProfile
from .models import GarminActivity, GarminBodyWeight
from core.models import DailyWater

logger = logging.getLogger(__name__)


def process_garmin_activities(user: UserProfile, activities: list) -> int:
    """
    Process a list of Garmin activity dicts and persist them to GarminActivity model.
    Returns number of activities created.
    """
    activities_synced = 0
    if not activities:
        return activities_synced

    for activity in activities:
        try:
            activity_id = activity.get('activityId')
            if not activity_id:
                logger.warning(f"Skipping activity with missing ID for user {user.id}: {activity}")
                continue

            start_ts_gmt = activity.get('startTimeGMT')
            start_time_utc = None
            if start_ts_gmt:
                try:
                    if isinstance(start_ts_gmt, str):
                        if ' ' in start_ts_gmt and '-' in start_ts_gmt:
                            # Parse datetime string
                            start_time_utc = _datetime.strptime(start_ts_gmt, '%Y-%m-%d %H:%M:%S')
                            start_time_utc = start_time_utc.replace(tzinfo=_datetime.timezone.utc)
                        else:
                            # Unix timestamp string to float
                            start_ts_gmt = float(start_ts_gmt)
                            start_time_utc = _datetime.fromtimestamp(start_ts_gmt / 1000, tz=_datetime.timezone.utc)
                    elif isinstance(start_ts_gmt, (int, float)):
                        # Unix timestamp in milliseconds
                        start_time_utc = _datetime.fromtimestamp(start_ts_gmt / 1000, tz=_datetime.timezone.utc)
                    else:
                        logger.warning(f"Unexpected start time type for activity {activity_id}: {type(start_ts_gmt)}")
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid start time format for activity {activity_id}: {start_ts_gmt} - {e}")
                    continue
            else:
                logger.warning(f"Missing start time for activity {activity_id} for user {user.id}")
                continue

            defaults = {
                'name': activity.get('activityName', 'Unnamed Activity'),
                'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
                'start_time_utc': start_time_utc,
                'duration_seconds': activity.get('duration'),
                'distance_meters': activity.get('distance'),
                'calories': activity.get('calories'),
                'average_hr': activity.get('averageHR'),
                'max_hr': activity.get('maxHR'),
                'raw_data': activity
            }
            # Filter None values
            defaults = {k: v for k, v in defaults.items() if v is not None}

            obj, created = GarminActivity.objects.update_or_create(
                user=user,
                activity_id=activity_id,
                defaults=defaults
            )
            if created:
                activities_synced += 1

            # Process CardioCoin rewards for the activity (preserve existing logic)
            try:
                if getattr(obj, 'calories', None) and obj.calories > 0:
                    if not Transaction.objects.filter(
                        user=user,
                        currency_type='cardio_coins',
                        garmin_activity=obj
                    ).exists():
                        join_month_start = user.user.date_joined.replace(day=1).date() if hasattr(user, 'user') else user.date_joined.replace(day=1).date()
                        one_week_after = (user.user.date_joined + timedelta(weeks=1)).date() if hasattr(user, 'user') else (user.date_joined + timedelta(weeks=1)).date()
                        activity_date = obj.start_time_utc.date() if getattr(obj, 'start_time_utc', None) else None
                        if activity_date and (join_month_start <= activity_date <= one_week_after):
                            # If UserProfile.user exists with earn_cardio_coins method
                            try:
                                # Prefer the convenience method on UserProfile -> user. Fallback to user if available.
                                owner = user.user if hasattr(user, 'user') else user
                                owner.earn_cardio_coins(Decimal(str(obj.calories)), garmin_activity=obj)
                            except Exception as e:
                                logger.debug(f"Failed awarding CardioCoins for activity {obj.id}: {e}")
            except Exception as e:
                logger.debug(f"CardioCoin award check failed for activity {activity_id}: {e}")

        except Exception as act_err:
            logger.error(f"Error processing activity {activity.get('activityId', 'N/A')} for user {user.id}: {act_err}")

    return activities_synced


def process_garmin_weight_data(user: UserProfile, weight_data: list) -> int:
    """
    Persist Garmin weight entries (raw) into GarminBodyWeight model.
    Returns count created.
    """
    if not weight_data:
        return 0

    weights_synced = 0
    for weight_entry in weight_data:
        try:
            weight_kg = weight_entry.get('weight')
            datetime_str = weight_entry.get('date')

            if weight_kg is None or not datetime_str:
                logger.warning(f"Skipping weight entry with missing data: {weight_entry}")
                continue

            # Parse datetime
            try:
                if isinstance(datetime_str, str):
                    weight_datetime = _datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                else:
                    logger.warning(f"Unexpected datetime format: {datetime_str}")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid datetime format for weight entry: {datetime_str} - {e}")
                continue

            obj, created = GarminBodyWeight.objects.update_or_create(
                user=user,
                datetime=weight_datetime,
                defaults={
                    'weight_kg': weight_kg,
                    'source_type': weight_entry.get('sourceType', 'garmin_scale'),
                    'raw_data': weight_entry
                }
            )
            if created:
                weights_synced += 1
        except Exception as weight_err:
            logger.error(f"Error processing weight entry for user {getattr(user, 'id', 'unknown')}: {weight_err}")
    return weights_synced


def process_garmin_hydration_records(user: UserProfile, hydration_records: list) -> int:
    """
    Persist Garmin hydration daily records into DailyWater (convert units if necessary).
    hydration_records expected as list of daily hydration dicts.
    Returns count created.
    """
    if not hydration_records:
        return 0

    hydration_synced = 0
    for daily in hydration_records:
        try:
            # Use same heuristics as previous implementation: try 'valueInML' or 'goalInML'
            value_ml = daily.get('valueInML')
            goal_ml = daily.get('goalInML')
            hydration_ml = None
            if value_ml is not None and value_ml > 0:
                hydration_ml = value_ml
            elif goal_ml is not None and goal_ml > 0:
                hydration_ml = goal_ml
            else:
                logger.debug(f"No valid hydration data in record: {daily}")
                continue

            # Convert ml to ounces (approx): 1 ml = 0.033814 ounces
            hydration_ounces = hydration_ml * 0.033814

            # Extract date
            calendar_date = daily.get('calendarDate')
            if not calendar_date:
                logger.warning(f"Skipping hydration record without calendarDate: {daily}")
                continue
            try:
                record_date = _datetime.strptime(calendar_date, '%Y-%m-%d').date()
            except Exception:
                logger.warning(f"Invalid calendarDate format for hydration record: {calendar_date}")
                continue

            obj, created = DailyWater.objects.update_or_create(
                user=user,
                source='garmin',
                date=record_date,
                defaults={
                    'amount_ounces': hydration_ounces,
                    'data': daily
                }
            )
            if created:
                hydration_synced += 1

        except Exception as err:
            logger.error(f"Error processing hydration record for user {getattr(user, 'id', 'unknown')}: {err}")

    return hydration_synced