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
    start_time = timezone.make_aware(datetime.fromtimestamp(workout_data.get('timestamp') / 1000))
    # Assume 1-hour workout if no end time
    end_time = start_time + timedelta(hours=1)
    return {
        'source_id': workout_data.get('id'),
        'start_time': start_time,
        'end_time': end_time,
        'data': workout_data
    }

def normalize_hc_sleep(sleep_session):
    start_str = sleep_session.get('start', '')
    if 'Z' in start_str:
        start_str = start_str.replace('Z', '')
    end_str = sleep_session.get('end', '')
    if 'Z' in end_str:
        end_str = end_str.replace('Z', '')

    start_time = timezone.make_aware(datetime.fromisoformat(start_str))
    end_time = timezone.make_aware(datetime.fromisoformat(end_str))
    return {
        'source_id': sleep_session.get('_id'),
        'start_time': start_time,
        'end_time': end_time,
        'data': sleep_session
    }

def normalize_hc_workout(exercise_session):
    start_str = exercise_session.get('start', '')
    if 'Z' in start_str:
        start_str = start_str.replace('Z', '')
    end_str = exercise_session.get('end', '')
    if 'Z' in end_str:
        end_str = end_str.replace('Z', '')

    start_time = timezone.make_aware(datetime.fromisoformat(start_str))
    end_time = timezone.make_aware(datetime.fromisoformat(end_str))
    return {
        'source_id': exercise_session.get('_id'),
        'start_time': start_time,
        'end_time': end_time,
        'data': exercise_session
    }

def normalize_garmin_steps(day):
    return {
        'date': datetime.strptime(day.get('calendarDate'), '%Y-%m-%d').date(),
        'steps': day.get('totalSteps'),
        'data': day
    }

def normalize_hc_steps(steps_record):
    start_str = steps_record.get('start', '')
    if 'Z' in start_str:
        start_str = start_str.replace('Z', '')
    return {
        'date': timezone.make_aware(datetime.fromisoformat(start_str)).date(),
        'steps': steps_record.get('data', {}).get('count'),
        'data': steps_record
    }


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
        configure_garmin_client(garmin_auth_service.auth_data)
        activities_url = f"/activitylist-service/activities/search/activities?limit=999&start=0"
        garmin_activities = garth.client.connectapi(activities_url)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        steps_url = f"/usersummary-service/stats/steps/daily/{start_date.isoformat()}/{end_date.isoformat()}"
        garmin_steps = garth.client.connectapi(steps_url)
        logger.info("Successfully fetched Garmin data")
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
                        if norm['start_time'].date() not in filled_dates:
                            Workout.objects.update_or_create(user=user, source='healthconnect', source_id=norm['source_id'], defaults=norm)
                            filled_dates.add(norm['start_time'].date())
            elif data_type == 'sleep':
                if source == 'healthconnect' and 'sleepSession' in hc_data:
                    for sleep_session in hc_data['sleepSession']:
                        norm = normalize_hc_sleep(sleep_session)
                        if norm['start_time'].date() not in filled_dates:
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
                        if norm['date'] not in filled_dates:
                            DailySteps.objects.update_or_create(user=user, source='healthconnect', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                            filled_dates.add(norm['date'])
            logger.info(f"Processed {data_type} data from {source} for user {user.username}")

    if 'sleep' in priorities_by_type:
        filled_dates = set()
        for source in priorities_by_type['sleep']:
            if source == 'healthconnect' and 'sleepSession' in hc_data:
                for sleep_session in hc_data['sleepSession']:
                    norm = normalize_hc_sleep(sleep_session)
                    if norm['start_time'].date() not in filled_dates:
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
                    if norm['date'] not in filled_dates:
                        DailySteps.objects.update_or_create(user=user, source='healthconnect', date=norm['date'], defaults={'steps': norm['steps'], 'data': norm['data']})
                        filled_dates.add(norm['date'])

    return f"Sync completed for user {user_id}"
