from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta, datetime
from .models import UserProfile, DataPriority, Workout, Sleep, DailySteps, ConnectedService, ArchivedWorkout, WorkoutConflict
from .conflict_detection import ConflictDetector, ConflictResolver

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
    # Handle case where startTimeGMT might be a string
    start_time_gmt = activity.get('startTimeGMT')
    if isinstance(start_time_gmt, str):
        try:
            start_time_gmt = float(start_time_gmt)
        except (ValueError, TypeError):
            logger.warning(f"Invalid startTimeGMT format: {start_time_gmt} for activity {activity.get('activityId')}")
            return None

    # Handle duration as well
    duration = activity.get('duration', 0)
    if isinstance(duration, str):
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration format: {duration} for activity {activity.get('activityId')}")
            duration = 0
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

    # 1. Get user priorities (create defaults if none exist)
    priorities = DataPriority.objects.filter(user=user).order_by('data_type', 'rank')
    priorities_by_type = {}

    # Create default priorities if none exist
    if not priorities.exists():
        logger.info(f"No data priorities found for user {user.username}, creating defaults")

        # Workout priorities: Liftosaur primary, Garmin secondary
        DataPriority.objects.get_or_create(
            user=user,
            data_type='workout',
            source='liftosaur',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=user,
            data_type='workout',
            source='garmin',
            defaults={'rank': 2}
        )
        DataPriority.objects.get_or_create(
            user=user,
            data_type='workout',
            source='healthconnect',
            defaults={'rank': 3}
        )

        # Sleep priorities: Health Connect primary
        DataPriority.objects.get_or_create(
            user=user,
            data_type='sleep',
            source='healthconnect',
            defaults={'rank': 1}
        )

        # Steps priorities: Garmin primary, Health Connect secondary
        DataPriority.objects.get_or_create(
            user=user,
            data_type='steps',
            source='garmin',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=user,
            data_type='steps',
            source='healthconnect',
            defaults={'rank': 2}
        )

        # Refresh priorities after creation
        priorities = DataPriority.objects.filter(user=user).order_by('data_type', 'rank')

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
                # Fetch steps data day by day (Garmin API doesn't support date ranges for steps)
                garmin_steps = []
                current_date = start_date
                while current_date <= end_date:
                    try:
                        if current_date > timezone.localtime().date():
                            current_date += timedelta(days=1)
                            continue

                        # Fetch daily steps for this specific date
                        url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                        daily_steps_data = garth.client.connectapi(url)
                        if daily_steps_data and len(daily_steps_data) > 0:
                            garmin_steps.extend(daily_steps_data)
                        logger.info(f"Successfully fetched steps data for {current_date}")
                    except Exception as step_err:
                        logger.error(f"Error syncing steps for {current_date} for user {user.id}: {step_err}")

                    current_date += timedelta(days=1)
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

    # 4. Process and save data with conflict detection
    for data_type in ['workout', 'sleep', 'steps']:
        if data_type not in priorities_by_type:
            logger.warning(f"No priorities set for {data_type} for user {user.username}; skipping.")
            continue

        # Initialize conflict detection for workouts
        if data_type == 'workout':
            conflict_detector = ConflictDetector(user)
            conflict_resolver = ConflictResolver(user)

        for source in priorities_by_type[data_type]:
            if data_type == 'workout':
                if source == 'garmin':
                    for activity in garmin_activities:
                        norm = normalize_garmin_activity_to_workout(activity)
                        if norm:
                            # Check for conflicts with existing workouts
                            existing_workouts = Workout.objects.filter(
                                user=user,
                                start_time__date=norm['start_time'].date()
                            )
                            conflicts = conflict_detector.detect_conflicts(norm, existing_workouts)

                            if conflicts:
                                # Resolve conflicts by archiving lower priority workouts
                                for conflict in conflicts:
                                    existing_workout = next(w for w in existing_workouts if w.source != source)
                                    conflict_resolver.resolve_conflicts(existing_workout, [existing_workout])

                            # Save the new workout
                            workout, created = Workout.objects.update_or_create(
                                user=user,
                                source='garmin',
                                source_id=norm['source_id'],
                                defaults=norm
                            )
                            logger.info(f"{'Created' if created else 'Updated'} workout from {source} for user {user.username}")

                elif source == 'liftosaur' and liftosaur_data:
                    for workout in liftosaur_data.get('storage', {}).get('history', []):
                        norm = normalize_liftosaur_workout(workout)
                        if norm:
                            # Check for conflicts with existing workouts
                            existing_workouts = Workout.objects.filter(
                                user=user,
                                start_time__date=norm['start_time'].date()
                            )
                            conflicts = conflict_detector.detect_conflicts(norm, existing_workouts)

                            if conflicts:
                                # Resolve conflicts by archiving lower priority workouts
                                for conflict in conflicts:
                                    existing_workout = next(w for w in existing_workouts if w.source != source)
                                    conflict_resolver.resolve_conflicts(existing_workout, [existing_workout])

                            # Save the new workout
                            workout, created = Workout.objects.update_or_create(
                                user=user,
                                source='liftosaur',
                                source_id=norm['source_id'],
                                defaults=norm
                            )
                            logger.info(f"{'Created' if created else 'Updated'} workout from {source} for user {user.username}")

                elif source == 'healthconnect' and 'exerciseSession' in hc_data:
                    for exercise in hc_data['exerciseSession']:
                        norm = normalize_hc_workout(exercise)
                        if norm:
                            # Check for conflicts with existing workouts
                            existing_workouts = Workout.objects.filter(
                                user=user,
                                start_time__date=norm['start_time'].date()
                            )
                            conflicts = conflict_detector.detect_conflicts(norm, existing_workouts)

                            if conflicts:
                                # Resolve conflicts by archiving lower priority workouts
                                for conflict in conflicts:
                                    existing_workout = next(w for w in existing_workouts if w.source != source)
                                    conflict_resolver.resolve_conflicts(existing_workout, [existing_workout])

                            # Save the new workout
                            workout, created = Workout.objects.update_or_create(
                                user=user,
                                source='healthconnect',
                                source_id=norm['source_id'],
                                defaults=norm
                            )
                            logger.info(f"{'Created' if created else 'Updated'} workout from {source} for user {user.username}")

            elif data_type == 'sleep':
                if source == 'healthconnect' and 'sleepSession' in hc_data:
                    for sleep_session in hc_data['sleepSession']:
                        norm = normalize_hc_sleep(sleep_session)
                        if norm:
                            Sleep.objects.update_or_create(
                                user=user,
                                source='healthconnect',
                                source_id=norm['source_id'],
                                defaults=norm
                            )
                            logger.info(f"Processed sleep data from {source} for user {user.username}")

            elif data_type == 'steps':
                if source == 'garmin':
                    for day in garmin_steps:
                        norm = normalize_garmin_steps(day)
                        if norm:
                            DailySteps.objects.update_or_create(
                                user=user,
                                source='garmin',
                                date=norm['date'],
                                defaults={'steps': norm['steps'], 'data': norm['data']}
                            )
                            logger.info(f"Processed steps data from {source} for user {user.username}")
                elif source == 'healthconnect' and 'steps' in hc_data:
                    for steps_record in hc_data['steps']:
                        norm = normalize_hc_steps(steps_record)
                        if norm:
                            DailySteps.objects.update_or_create(
                                user=user,
                                source='healthconnect',
                                date=norm['date'],
                                defaults={'steps': norm['steps'], 'data': norm['data']}
                            )
                            logger.info(f"Processed steps data from {source} for user {user.username}")

    # Log summary of what was processed
    total_workouts = Workout.objects.filter(user=user, start_time__gte=thirty_days_ago).count()
    total_sleep = Sleep.objects.filter(user=user, start_time__gte=thirty_days_ago).count()
    total_steps = DailySteps.objects.filter(user=user, date__gte=thirty_days_ago.date()).count()

    logger.info(f"Sync summary for user {user.username}: {total_workouts} workouts, {total_sleep} sleep records, {total_steps} step records saved")

    return f"Sync completed for user {user_id}"