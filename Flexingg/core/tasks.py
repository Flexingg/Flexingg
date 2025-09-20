from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta, datetime
from .models import UserProfile, DataPriority, Workout, Sleep, DailySteps, ConnectedService

# Garmin imports
from garminconnect.utils import configure_garmin_client, refresh_oauth2_only
import garth
from garth.exc import GarthException, GarthHTTPError

# Health Connect imports
from healthconnect.utils import HCGatewayClient

# Liftosaur imports
from .utils import liftosaur_download

logger = logging.getLogger(__name__)

def normalize_garmin_activity_to_workout(activity):
    return {
        'source_id': activity.get('activityId'),
        'start_time': timezone.make_aware(datetime.fromtimestamp(activity.get('startTimeGMT') / 1000)),
        'end_time': timezone.make_aware(datetime.fromtimestamp((activity.get('startTimeGMT') + activity.get('duration') * 1000) / 1000)),
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


@shared_task
def sync_user_data(user_id):
    logger.info(f"Sync started for user {user_id}")
    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        logger.error(f"User with id {user_id} not found.")
        return

    # 1. Get user priorities
    priorities = DataPriority.objects.filter(user=user).order_by('data_type', 'rank')
    priorities_by_type = {}
    for p in priorities:
        if p.data_type not in priorities_by_type:
            priorities_by_type[p.data_type] = []
        priorities_by_type[p.data_type].append(p.source)

    # 2. Delete old data for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    Workout.objects.filter(user=user, start_time__gte=thirty_days_ago).delete()
    Sleep.objects.filter(user=user, start_time__gte=thirty_days_ago).delete()
    DailySteps.objects.filter(user=user, date__gte=thirty_days_ago.date()).delete()
    logger.info(f"Deleted last 30 days of data for user {user.username}")

    # 3. Fetch fresh data
    garmin_activities, garmin_steps, hc_data, liftosaur_data = [], [], {}, {}

    try:
        garmin_auth_service = ConnectedService.objects.get(user=user, service_name='garmin')
        auth_data = garmin_auth_service.auth_data

        # Check if auth_data has the expected structure
        if not auth_data or not isinstance(auth_data, dict):
            logger.error("Invalid or missing Garmin auth data")
            garmin_activities = []
            garmin_steps = []
        else:
            # Try to refresh tokens if needed
            refreshed_auth = refresh_oauth2_only(auth_data)
            if refreshed_auth:
                # Update the stored auth data if refresh was successful
                garmin_auth_service.auth_data = refreshed_auth
                garmin_auth_service.save()
                auth_data = refreshed_auth

            if configure_garmin_client(auth_data):
                activities_url = f"/activitylist-service/activities/search/activities?limit=999&start=0"
                garmin_activities = garth.client.connectapi(activities_url)
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)
                steps_url = f"/usersummary-service/stats/steps/daily/{start_date.isoformat()}/{end_date.isoformat()}"
                garmin_steps = garth.client.connectapi(steps_url)
                logger.info("Successfully fetched Garmin data")
            else:
                logger.error("Failed to configure Garmin client")
                garmin_activities = []
                garmin_steps = []
    except ConnectedService.DoesNotExist:
        logger.warning("No Garmin service connected for user")
        garmin_activities = []
        garmin_steps = []
    except Exception as e:
        logger.error(f"Error fetching Garmin data: {e}")
        garmin_activities = []
        garmin_steps = []

    try:
        hc_auth = ConnectedService.objects.get(user=user, service_name='healthconnect')
        client = HCGatewayClient()
        client.token = hc_auth.auth_data.get('token')
        client.refresh_token = hc_auth.auth_data.get('refresh_token')
        expiry_str = hc_auth.auth_data.get('expiry')
        if isinstance(expiry_str, str):
            client.expiry = timezone.datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        else:
            # Ensure expiry is timezone-aware
            if expiry_str and hasattr(expiry_str, 'tzinfo') and expiry_str.tzinfo is None:
                client.expiry = timezone.make_aware(expiry_str)
            else:
                client.expiry = expiry_str
        if client.is_authenticated():
            hc_data = client.fetch_historical(days=30)
            logger.info("Successfully fetched Health Connect data")
        else:
            logger.warning("Health Connect client not authenticated")
            hc_data = {}
    except Exception as e:
        logger.error(f"Error fetching Health Connect data: {e}")
        hc_data = {}

    try:
        liftosaur_auth = ConnectedService.objects.get(user=user, service_name='liftosaur')
        liftosaur_user_id = liftosaur_auth.auth_data.get('user_id')
        session_token = liftosaur_auth.auth_data.get('session_token')
        if liftosaur_user_id and session_token:
            liftosaur_data = liftosaur_download(liftosaur_user_id, session_token)
            logger.info("Successfully fetched Liftosaur data")
        else:
            logger.warning("Liftosaur auth data incomplete")
            liftosaur_data = {}
    except Exception as e:
        logger.error(f"Error fetching Liftosaur data: {e}")
        liftosaur_data = {}

    # 4. Process and save data in priority order
    for data_type in ['workout', 'sleep', 'steps']:
        if data_type not in priorities_by_type:
            logger.warning(f"No priorities set for {data_type} for user {user.username}; skipping.")
            continue
        filled_dates = set()
        for source in priorities_by_type[data_type]:
            if data_type == 'workout':
                if source == 'garmin':
                    for activity in garmin_activities:
                        norm = normalize_garmin_activity_to_workout(activity)
                        if norm['start_time'].date() not in filled_dates:
                            Workout.objects.update_or_create(user=user, source='garmin', source_id=norm['source_id'], defaults=norm)
                            filled_dates.add(norm['start_time'].date())
                elif source == 'liftosaur' and liftosaur_data:
                     for workout in liftosaur_data.get('storage', {}).get('history', []):
                        norm = normalize_liftosaur_workout(workout)
                        if norm['start_time'].date() not in filled_dates:
                            Workout.objects.update_or_create(user=user, source='liftosaur', source_id=norm['source_id'], defaults=norm)
                            filled_dates.add(norm['start_time'].date())
                elif source == 'healthconnect' and 'exerciseSession' in hc_data:
                    for exercise in hc_data['exerciseSession']:
                        norm = normalize_hc_workout(exercise)
                        if norm and norm['start_time'].date() not in filled_dates:
                            Workout.objects.update_or_create(user=user, source='healthconnect', source_id=norm['source_id'], defaults=norm)
                            filled_dates.add(norm['start_time'].date())
            elif data_type == 'sleep':
                if source == 'healthconnect' and 'sleepSession' in hc_data:
                    for sleep_session in hc_data['sleepSession']:
                        norm = normalize_hc_sleep(sleep_session)
                        if norm and norm['start_time'].date() not in filled_dates:
                            Sleep.objects.update_or_create(user=user, source='healthconnect', source_id=norm['source_id'], defaults=norm)
                            filled_dates.add(norm['start_time'].date())
            elif data_type == 'steps':
                if source == 'garmin':
                    for day in garmin_steps:
                        norm = normalize_garmin_steps(day)
                        if norm['date'] not in filled_dates:
                            DailySteps.objects.update_or_create(user=user, source='garmin', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                            filled_dates.add(norm['date'])
                elif source == 'healthconnect' and 'steps' in hc_data:
                    for steps_record in hc_data['steps']:
                        norm = normalize_hc_steps(steps_record)
                        if norm and norm['date'] not in filled_dates:
                            DailySteps.objects.update_or_create(user=user, source='healthconnect', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                            filled_dates.add(norm['date'])
            logger.info(f"Processed {data_type} data from {source} for user {user.username}")

    if 'sleep' in priorities_by_type:
        filled_dates = set()
        for source in priorities_by_type['sleep']:
            if source == 'healthconnect' and 'sleepSession' in hc_data:
                for sleep_session in hc_data['sleepSession']:
                    norm = normalize_hc_sleep(sleep_session)
                    if norm and norm['start_time'].date() not in filled_dates:
                        Sleep.objects.update_or_create(user=user, source='healthconnect', source_id=norm['source_id'], defaults=norm)
                        filled_dates.add(norm['start_time'].date())

    if 'steps' in priorities_by_type:
        filled_dates = set()
        for source in priorities_by_type['steps']:
            if source == 'garmin':
                for day in garmin_steps:
                    norm = normalize_garmin_steps(day)
                    if norm['date'] not in filled_dates:
                        DailySteps.objects.update_or_create(user=user, source='garmin', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                        filled_dates.add(norm['date'])
            elif source == 'healthconnect' and 'steps' in hc_data:
                for steps_record in hc_data['steps']:
                    norm = normalize_hc_steps(steps_record)
                    if norm and norm['date'] not in filled_dates:
                        DailySteps.objects.update_or_create(user=user, source='healthconnect', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                        filled_dates.add(norm['date'])

    return f"Sync completed for user {user_id}"
