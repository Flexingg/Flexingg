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

# Import normalization task (moved separately to normalization_tasks.py)
from .normalization_tasks import normalize_garmin_weight_data


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
                        # Require the activity to be on or after the user's actual join date,
                        # and within one week after joining. This prevents awarding for activities
                        # that occurred earlier in the same month before the user joined.
                        user_join_dt = getattr(user, 'date_joined', None)
                        if not user_join_dt:
                            continue
                        join_date = user_join_dt.date()
                        one_week_after = (user_join_dt + timedelta(weeks=1)).date()
                        activity_date = obj.start_time_utc.date() if getattr(obj, 'start_time_utc', None) else None
                        if activity_date and (join_date <= activity_date <= one_week_after):
                            try:
                                user.earn_cardio_coins(Decimal(str(obj.calories)), garmin_activity=obj)
                            except Exception as e:
                                logger.debug(f"Failed awarding CardioCoins for activity {obj.id}: {e}")


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

        # Try to fetch weight data. Prefer garth helper; fall back to raw endpoint.
        weight_data = None
        try:
            # Use date range when available for WeightData.list
            if start_date and end_date:
                days = (end_date - start_date).days + 1
            else:
                days = 365
            try:
                weight_data = garth.WeightData.list(start_date.isoformat() if start_date else None, days)
            except Exception:
                # Fallback to raw REST endpoint
                weight_url = "/weight-service/user/weight"
                weight_data = garth.client.connectapi(weight_url)
            logger.info(f"Successfully fetched {len(weight_data) if weight_data else 0} weight entries for user {user.id}.")
        except GarthHTTPError as api_err:
            status = getattr(api_err, 'status_code', None)
            # If endpoint not present for this account, skip gracefully
            if status == 404:
                logger.info(f"Weight endpoint not available for user {user.id} (404). Skipping weight sync.")
                weight_data = []
            elif status in [401, 403]:
                # Try one refresh attempt then retry using the same logic
                logger.warning(f"Auth error on weight API for user {user.id}, attempting refresh and retry.")
                if refresh_oauth2_only(garmin_auth) and configure_garmin_client(garmin_auth):
                    try:
                        if start_date and end_date:
                            days = (end_date - start_date).days + 1
                        else:
                            days = 365
                        try:
                            weight_data = garth.WeightData.list(start_date.isoformat() if start_date else None, days)
                        except Exception:
                            weight_url = "/weight-service/user/weight"
                            weight_data = garth.client.connectapi(weight_url)
                        logger.info(f"Successfully fetched {len(weight_data) if weight_data else 0} weight entries after refresh for user {user.id}.")
                    except GarthHTTPError as retry_err:
                        logger.error(f"Retry after refresh failed for weight API for user {user.id}: {retry_err}")
                        return {'success': False, 'error': 'Token refresh failed or weight endpoint unavailable after retry'}
                else:
                    logger.error(f"Token refresh failed during weight sync for user {user.id}")
                    return {'success': False, 'error': 'Token refresh failed after auth error'}
            else:
                logger.error(f"Unexpected HTTP error on weight API for user {user.id}: {api_err}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching weight data for user {user.id}: {e}")
            raise     

        if not weight_data:
            logger.info(f"No weight data found for user {user.id}")
            return {'success': True, 'weights_synced': 0}

        # Process weight data - support both garth.WeightData objects and raw dicts
        from .models import GarminBodyWeight
        for weight_entry in weight_data:
            try:
                # Detect garth.WeightData-like object
                if hasattr(weight_entry, 'weight') and hasattr(weight_entry, 'datetime_utc'):
                    raw_weight = getattr(weight_entry, 'weight', None)
                    weight_dt = getattr(weight_entry, 'datetime_utc', None)
                    source_type = getattr(weight_entry, 'source_type', None) or getattr(weight_entry, 'sourceType', 'garmin_scale')
                    raw_json = weight_entry.__dict__ if hasattr(weight_entry, '__dict__') else None
                else:
                    # Expect a dict from the raw REST endpoint
                    raw_weight = weight_entry.get('weight')
                    source_type = weight_entry.get('sourceType') or weight_entry.get('source_type') or 'garmin_scale'
                    raw_json = weight_entry

                    # Many Garmin weight REST responses include 'timestamp_gmt' in ms or 'date' ISO string
                    weight_dt = None
                    if weight_entry.get('timestamp_gmt'):
                        try:
                            ts = float(weight_entry.get('timestamp_gmt'))
                            weight_dt = datetime.fromtimestamp(ts / 1000.0, tz=dt_timezone.utc)
                        except Exception:
                            weight_dt = None
                    elif weight_entry.get('date'):
                        try:
                            weight_dt = datetime.fromisoformat(str(weight_entry.get('date')).replace('Z', '+00:00'))
                        except Exception:
                            weight_dt = None

                # Validate presence
                if raw_weight is None or weight_dt is None:
                    logger.warning(f"Skipping weight entry with missing data for user {getattr(user,'id','unknown')}: {weight_entry}")
                    continue

                # Garmin returns weight in grams (per garth README). Convert to kg.
                try:
                    raw_weight_val = float(raw_weight)
                except Exception:
                    logger.warning(f"Invalid weight value, skipping: {raw_weight}")
                    continue

                # Heuristic: if value looks like grams (>1000), divide by 1000 to get kg
                if raw_weight_val > 1000:
                    weight_kg = raw_weight_val / 1000.0
                else:
                    # already in kg (rare), accept as-is
                    weight_kg = raw_weight_val

                # Ensure timezone-aware datetime
                if weight_dt.tzinfo is None:
                    weight_dt = weight_dt.replace(tzinfo=dt_timezone.utc)

                # Persist record
                obj, created = GarminBodyWeight.objects.update_or_create(
                    user=user,
                    datetime=weight_dt,
                    defaults={
                        'weight_kg': weight_kg,
                        'source_type': source_type,
                        'raw_data': raw_json
                    }
                )
                if created:
                    weights_synced += 1

            except Exception as weight_err:
                logger.error(f"Error processing weight entry for user {getattr(user,'id','unknown')}: {weight_err}", exc_info=True)

        # Update last sync
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        # Trigger normalization task which lives in normalization_tasks.py
        normalize_garmin_weight_data.delay(user_id)

        return {'success': True, 'weights_synced': weights_synced}

    except Exception as e:
        logger.error(f"Unexpected error during weight sync for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def garmin_sync_hydration_task(user_id, start_date, end_date):
    """
    Celery task for syncing daily hydration from Garmin.
    """
    try:
        user = UserProfile.objects.get(id=user_id)
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except (UserProfile.DoesNotExist, Garmin_Auth.DoesNotExist):
        logger.error(f"No user or Garmin auth for ID {user_id}")
        return {'success': False, 'error': 'No Garmin auth record found'}

    hydration_synced = 0

    try:
        # Configure client with existing tokens
        if not configure_garmin_client(garmin_auth):
            logger.error(f"Failed to configure Garmin client for user {user.id}")
            return {'success': False, 'error': 'Client configuration failed'}

        # Sync hydration for each day in range
        local_today = timezone.localtime().date()
        current_date = start_date
        while current_date <= end_date:
            try:
                if current_date > local_today:
                    current_date += timedelta(days=1)
                    continue

                # Fetch daily hydration
                url = f"/usersummary-service/stats/hydration/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                daily_hydration_data = None
                retry_count = 0
                max_retries = 1
                while retry_count <= max_retries and daily_hydration_data is None:
                    try:
                        daily_hydration_data = garth.client.connectapi(url)
                        logger.info(f"Successfully fetched hydration data for {current_date}.")
                    except GarthHTTPError as api_err:
                        if api_err.status_code in [401, 403]:
                            if retry_count == 0:
                                logger.warning(f"Auth error on hydration API for {current_date}, attempting refresh and retry.")
                                if refresh_oauth2_only(garmin_auth) and configure_garmin_client(garmin_auth):
                                    retry_count += 1
                                    continue
                                else:
                                    logger.error(f"Token refresh failed during hydration sync for {current_date}")
                                    break
                            else:
                                logger.error(f"Retry failed after refresh for hydration API {current_date}")
                                break
                        elif api_err.status_code == 404:
                            # Hydration API might not exist, skip silently
                            logger.debug(f"Hydration API not available for {current_date}")
                            break
                        else:
                            raise
                    except Exception as api_err:
                        logger.warning(f"Hydration API failed for {current_date}: {api_err}")
                        break
                    retry_count += 1 if daily_hydration_data is None else 0

                if daily_hydration_data and len(daily_hydration_data) > 0:
                    # Assume hydration data structure similar to steps
                    hydration_amount = daily_hydration_data[0].get('totalHydration', 0)
                    if hydration_amount is not None and hydration_amount > 0:
                        # Convert to ounces if needed (Garmin likely returns in ml)
                        hydration_ounces = hydration_amount / 29.5735  # ml to ounces
                        from core.models import DailyWater
                        obj, created = DailyWater.objects.update_or_create(
                            user=user,
                            source='garmin',
                            date=current_date,
                            defaults={
                                'amount_ounces': hydration_ounces,
                                'data': daily_hydration_data[0]
                            }
                        )
                        if created: hydration_synced += 1
            except Exception as hydration_err:
                logger.error(f"Error syncing hydration for {current_date} for user {user.id}: {hydration_err}")

            current_date += timedelta(days=1)
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'hydration_synced': hydration_synced}

    except Exception as e:
        logger.error(f"Unexpected error during hydration task for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}