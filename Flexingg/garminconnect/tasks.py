from celery import shared_task
from .views import ensure_valid_tokens
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
        # Ensure tokens are valid
        if not ensure_valid_tokens(garmin_auth):
            logger.error(f"Token refresh failed for user {user.id}")
            return {'success': False, 'error': 'Token refresh failed'}

        # Configure client with tokens
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

        # Sync steps for each day in range
        current_date = start_date
        while current_date <= end_date:
            try:
                if current_date > timezone.now().date():
                    current_date += timedelta(days=1)
                    continue

                # Fetch daily steps
                url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                try:
                    daily_steps_data = garth.client.connectapi(url)
                except Exception as api_err:
                    logger.warning(f"Steps API failed for {current_date}: {api_err}")
                    # Try alternative endpoint
                    alt_url = f"/usersummary-service/usersummary/daily/{current_date.isoformat()}"
                    daily_steps_data = garth.client.connectapi(alt_url)

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
        # Ensure tokens are valid
        if not ensure_valid_tokens(garmin_auth):
            logger.error(f"Token refresh failed for user {user.id}")
            return {'success': False, 'error': 'Token refresh failed'}

        # Configure client with tokens (same as steps)
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

        # Build URL with date filter if provided
        url = f"/activitylist-service/activities/search/activities?start=0&limit={limit}"
        if start_date and end_date:
            from_str = f"{start_date.isoformat()}T00:00:00"
            to_str = f"{end_date.isoformat()}T23:59:59"
            url += f"&startDateLocalFrom={from_str}&startDateLocalTo={to_str}"
        # Fetch activities
        activities = garth.client.connectapi(url)

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

                # Integrate CardioCoin rewards
                if obj.calories and obj.calories > 0:
                    from core.models import Transaction
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