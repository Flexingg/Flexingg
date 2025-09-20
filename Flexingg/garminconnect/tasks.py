from celery import shared_task
from .utils import configure_garmin_client, refresh_oauth2_only
from .models import Garmin_Auth, GarminDailySteps, GarminActivity
from core.models import UserProfile, Transaction
from django.utils import timezone
from datetime import timedelta, datetime
from datetime import timezone as dt_timezone
import garth
from garth.exc import GarthException, GarthHTTPError
import logging

from decimal import Decimal
logger = logging.getLogger(__name__)

@shared_task
def garmin_sync_steps_task(user_id, start_date, end_date):
    """
    Celery task for syncing daily steps from Garmin.
    """
    try:
        user = UserProfile.objects.get(id=user_id)
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except (UserProfile.DoesNotExist, Garmin_Auth.DoesNotExist):
        logger.error(f"No user or Garmin auth for ID {user_id}")
        return {'success': False, 'error': 'No Garmin auth record found'}

    steps_synced = 0

    try:
        # Configure client with existing tokens
        if not configure_garmin_client(garmin_auth):
            logger.error(f"Failed to configure Garmin client for user {user.id}")
            return {'success': False, 'error': 'Client configuration failed'}

        # Sync steps for each day in range
        local_today = timezone.localtime().date()
        current_date = start_date
        while current_date <= end_date:
            try:
                if current_date > local_today:
                    current_date += timedelta(days=1)
                    continue

                # Fetch daily steps
                url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                daily_steps_data = None
                retry_count = 0
                max_retries = 1
                while retry_count <= max_retries and daily_steps_data is None:
                    try:
                        daily_steps_data = garth.client.connectapi(url)
                        logger.info(f"Successfully fetched steps data for {current_date} using primary endpoint.")
                    except GarthHTTPError as api_err:
                        if api_err.status_code in [401, 403]:
                            if retry_count == 0:
                                logger.warning(f"Auth error on steps API for {current_date}, attempting refresh and retry.")
                                if refresh_oauth2_only(garmin_auth) and configure_garmin_client(garmin_auth):
                                    retry_count += 1
                                    continue
                                else:
                                    logger.error(f"Token refresh failed during steps sync for {current_date}")
                                    break
                            else:
                                logger.error(f"Retry failed after refresh for steps API {current_date}")
                                break
                        else:
                            raise
                    except Exception as api_err:
                        logger.warning(f"Steps API failed for {current_date}: {api_err}")
                        # Try alternative endpoint if primary failed and no auth retry needed
                        if retry_count == 0:
                            alt_url = f"/usersummary-service/usersummary/daily/{current_date.isoformat()}"
                            try:
                                daily_steps_data = garth.client.connectapi(alt_url)
                                logger.info(f"Successfully fetched steps data for {current_date} using alt endpoint.")
                            except GarthHTTPError as alt_err:
                                if alt_err.status_code in [401, 403]:
                                    logger.warning(f"Auth error on alt steps API for {current_date}, but refresh already attempted.")
                                    break
                                else:
                                    raise
                            except Exception as alt_err:
                                logger.warning(f"Alt steps API failed for {current_date}: {alt_err}")
                        break
                    retry_count += 1 if daily_steps_data is None else 0

                if daily_steps_data and len(daily_steps_data) > 0:
                    steps = daily_steps_data[0].get('totalSteps', 0)
                    if steps is not None:
                        obj, created = GarminDailySteps.objects.update_or_create(
                            user=user,
                            date=current_date,
                            defaults={'steps': steps}
                        )
                        if created: steps_synced += 1
            except Exception as step_err:
                logger.error(f"Error syncing steps for {current_date} for user {user.id}: {step_err}")

            current_date += timedelta(days=1)
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'steps_synced': steps_synced}

    except Exception as e:
        logger.error(f"Unexpected error during steps task for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}

@shared_task
def garmin_sync_activities_task(user_id, limit=500, start_date=None, end_date=None):
    """
    Celery task for syncing Garmin activities.
    """
    try:
        user = UserProfile.objects.get(id=user_id)
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except (UserProfile.DoesNotExist, Garmin_Auth.DoesNotExist):
        logger.error(f"No user or Garmin auth for ID {user_id}")
        return {'success': False, 'error': 'No Garmin auth record found'}

    activities_synced = 0

    try:
        # Configure client with existing tokens
        if not configure_garmin_client(garmin_auth):
            logger.error(f"Failed to configure Garmin client for user {user.id}")
            return {'success': False, 'error': 'Client configuration failed'}

        # Build URL with date filter if provided
        url = f"/activitylist-service/activities/search/activities?start=0&limit={limit}"
        if start_date and end_date:
            from_str = f"{start_date.isoformat()}T00:00:00"
            to_str = f"{end_date.isoformat()}T23:59:59"
            url += f"&startDateLocalFrom={from_str}&startDateLocalTo={to_str}"
        # Fetch activities with retry on auth error
        activities = None
        retry_count = 0
        max_retries = 1
        while retry_count <= max_retries and activities is None:
            try:
                activities = garth.client.connectapi(url)
                logger.info(f"Successfully fetched {len(activities) if activities else 0} activities for user {user.id}.")
            except GarthHTTPError as api_err:
                if api_err.status_code in [401, 403]:
                    if retry_count == 0:
                        logger.warning(f"Auth error on activities API, attempting refresh and retry.")
                        if refresh_oauth2_only(garmin_auth) and configure_garmin_client(garmin_auth):
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"Token refresh failed during activities sync")
                            return {'success': False, 'error': 'Token refresh failed after auth error'}
                    else:
                        logger.error(f"Retry failed after refresh for activities API")
                        return {'success': False, 'error': 'API retry failed'}
                else:
                    raise
            except Exception as api_err:
                logger.error(f"Unexpected error on activities API: {api_err}")
                raise
            retry_count += 1 if activities is None else 0

        if not activities:
            logger.info(f"No activities found for user {user.id}")
            return {'success': True, 'activities_synced': 0}

        # Process each activity
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
                                start_time_utc = datetime.strptime(start_ts_gmt, '%Y-%m-%d %H:%M:%S')
                                start_time_utc = start_time_utc.replace(tzinfo=dt_timezone.utc)
                            else:
                                # Unix timestamp string to float
                                start_ts_gmt = float(start_ts_gmt)
                                start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                        elif isinstance(start_ts_gmt, (int, float)):
                            # Unix timestamp in milliseconds
                            start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
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
                if created: activities_synced += 1
                # Process CardioCoin rewards for the activity
                if obj.calories and obj.calories > 0:
                    if not Transaction.objects.filter(
                        user=user,
                        currency_type='cardio_coins',
                        garmin_activity=obj
                    ).exists():
                        join_month_start = user.date_joined.replace(day=1).date()
                        one_week_after = (user.date_joined + timedelta(weeks=1)).date()
                        activity_date = obj.start_time_utc.date()
                        if join_month_start <= activity_date <= one_week_after:
                            user.earn_cardio_coins(Decimal(str(obj.calories)), garmin_activity=obj)


            except Exception as act_err:
                logger.error(f"Error processing activity {activity.get('activityId', 'N/A')} for user {user.id}: {act_err}")

        # Update last sync
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'activities_synced': activities_synced}

    except Exception as e:
        logger.error(f"Unexpected error during activities task for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}
@shared_task
def garmin_sync_weight_task(user_id, start_date=None, end_date=None):
    """
    Celery task for syncing body weight data from Garmin Connect.
    """
    try:
        user = UserProfile.objects.get(id=user_id)
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except (UserProfile.DoesNotExist, Garmin_Auth.DoesNotExist):
        logger.error(f"No user or Garmin auth for ID {user_id}")
        return {'success': False, 'error': 'No Garmin auth record found'}

    weights_synced = 0

    try:
        # Configure client with existing tokens
        if not configure_garmin_client(garmin_auth):
            logger.error(f"Failed to configure Garmin client for user {user.id}")
            return {'success': False, 'error': 'Client configuration failed'}

        # Build URL for weight data
        url = "/weight-service/user/weight"

        # Fetch weight data with retry on auth error
        weight_data = None
        retry_count = 0
        max_retries = 1
        while retry_count <= max_retries and weight_data is None:
            try:
                weight_data = garth.client.connectapi(url)
                logger.info(f"Successfully fetched weight data for user {user.id}.")
            except GarthHTTPError as api_err:
                if api_err.status_code in [401, 403]:
                    if retry_count == 0:
                        logger.warning(f"Auth error on weight API, attempting refresh and retry.")
                        if refresh_oauth2_only(garmin_auth) and configure_garmin_client(garmin_auth):
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"Token refresh failed during weight sync")
                            return {'success': False, 'error': 'Token refresh failed after auth error'}
                    else:
                        logger.error(f"Retry failed after refresh for weight API")
                        return {'success': False, 'error': 'API retry failed'}
                else:
                    raise
            except Exception as api_err:
                logger.error(f"Unexpected error on weight API: {api_err}")
                raise
            retry_count += 1 if weight_data is None else 0

        if not weight_data:
            logger.info(f"No weight data found for user {user.id}")
            return {'success': True, 'weights_synced': 0}

        # Process weight data
        from .models import GarminBodyWeight
        for weight_entry in weight_data:
            try:
                weight_kg = weight_entry.get('weight')
                datetime_str = weight_entry.get('date')

                if not weight_kg or not datetime_str:
                    logger.warning(f"Skipping weight entry with missing data: {weight_entry}")
                    continue

                # Parse datetime
                try:
                    if isinstance(datetime_str, str):
                        # Parse ISO format datetime string
                        weight_datetime = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    else:
                        logger.warning(f"Unexpected datetime format: {datetime_str}")
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid datetime format for weight entry: {datetime_str} - {e}")
                    continue

                # Create or update weight record
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
                logger.error(f"Error processing weight entry for user {user.id}: {weight_err}")

        # Update last sync
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'weights_synced': weights_synced}

    except Exception as e:
        logger.error(f"Unexpected error during weight sync for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def normalize_garmin_weight_data(user_id):
    """
    Normalize Garmin body weight data to unified BodyWeight model.
    """
    from core.models import BodyWeight
    from .models import GarminBodyWeight
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

    try:
        user_weights = GarminBodyWeight.objects.filter(user_id=user_id)

        normalized_count = 0

        with transaction.atomic():
            for garmin_weight in user_weights:
                # Check if already normalized
                if BodyWeight.objects.filter(
                    user_id=user_id,
                    source='garmin',
                    source_id=str(garmin_weight.id)
                ).exists():
                    continue

                # Convert kg to lbs
                weight_lbs = garmin_weight.weight_kg * 2.20462

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='garmin',
                    source_id=str(garmin_weight.id),
                    datetime=garmin_weight.datetime,
                    weight_lbs=weight_lbs,
                    data={
                        'original_weight_kg': garmin_weight.weight_kg,
                        'source_type': garmin_weight.source_type,
                        'garmin_raw_data': garmin_weight.raw_data
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Garmin weight data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}