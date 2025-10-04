from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta, datetime
from .models import UserProfile, DataPriority, Workout, Sleep, DailySteps, DailyWater, ConnectedService, ArchivedWorkout, WorkoutConflict, NutritionEntry
from .conflict_detection import ConflictDetector, ConflictResolver

# Garmin imports
from garminconnect.utils import configure_garmin_client, refresh_oauth2_only
import garth
from garth.exc import GarthException, GarthHTTPError

# Health Connect imports
from healthconnect.utils import HCGatewayClient
from healthconnect.data_processor import save_healthconnect_records
from healthconnect.normalization_tasks import normalize_healthconnect_weight_data
from healthconnect.sync_tasks import healthconnect_sync_and_stage_task

# Liftosaur imports
from .liftosaur_client import liftosaur_download

# Normalization helpers
from .normalization import (
    normalize_garmin_activity_to_workout,
    normalize_liftosaur_workout,
    normalize_hc_sleep,
    normalize_hc_workout,
    normalize_garmin_steps,
    normalize_hc_steps,
    normalize_garmin_hydration,
    normalize_hc_hydration,
)

# Data processor import (refactor)
from .data_processor import process_and_save_user_data

logger = logging.getLogger(__name__)

@shared_task
def sync_user_data(user_id, bypass_debounce=False):
    logger.info(f"Sync started for user {user_id}")
    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        logger.error(f"User with id {user_id} not found.")
        return

    # Check if sync is needed based on debounce setting (skip if bypass_debounce is True)
    if not bypass_debounce:
        debounce_minutes = getattr(user, 'sync_debounce_minutes', 60)
        if user.last_sync and debounce_minutes > 0:
            time_since_last_sync = timezone.now() - user.last_sync
            if time_since_last_sync.total_seconds() < (debounce_minutes * 60):
                logger.info(f"Sync skipped for user {user_id} - last sync was {time_since_last_sync.total_seconds() / 60:.1f} minutes ago (debounce: {debounce_minutes} minutes)")
                return f"Sync skipped for user {user_id} - too soon since last sync"

    # Update last_sync timestamp
    user.last_sync = timezone.now()
    user.save(update_fields=['last_sync'])

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
        DataPriority.objects.get_or_create(
            user=user,
            data_type='sleep',
            source='garmin',
            defaults={'rank': 2}
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

        # Water priorities: Health Connect primary, Garmin secondary
        DataPriority.objects.get_or_create(
            user=user,
            data_type='water',
            source='healthconnect',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=user,
            data_type='water',
            source='garmin',
            defaults={'rank': 2}
        )

        # Bodyweight priorities: Garmin primary, Health Connect secondary
        DataPriority.objects.get_or_create(
            user=user,
            data_type='bodyweight',
            source='garmin',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=user,
            data_type='bodyweight',
            source='healthconnect',
            defaults={'rank': 2}
        )

        # Refresh priorities after creation
        priorities = DataPriority.objects.filter(user=user).order_by('data_type', 'rank')

    for p in priorities:
        if p.data_type not in priorities_by_type:
            priorities_by_type[p.data_type] = []
        priorities_by_type[p.data_type].append(p.source)

    # 2. No deletion - update existing data instead

    # 3. Fetch fresh data
    garmin_activities, garmin_steps, garmin_hydration, hc_data, liftosaur_data = [], [], [], {}, {}
    garmin_sleep = []

    try:
        garmin_auth_service = ConnectedService.objects.get(user=user, service_name='garmin')
        auth_data = garmin_auth_service.auth_data

        # Check if auth_data has the expected structure
        if not auth_data or not isinstance(auth_data, dict):
            logger.error("Invalid or missing Garmin auth data")
            garmin_activities = []
            garmin_steps = []
            garmin_sleep = []
        else:
            # Try to refresh tokens if needed
            refreshed_auth = refresh_oauth2_only(auth_data)
            if refreshed_auth:
                logger.info("Garmin tokens refreshed; updating stored auth_data")
                try:
                    garmin_auth_service.auth_data = refreshed_auth
                    garmin_auth_service.save()
                    auth_data = refreshed_auth
                except Exception as persist_err:
                    logger.exception(f"Failed to persist refreshed Garmin auth_data: {persist_err}")
            else:
                logger.debug("Garmin token refresh not performed or returned no update; using existing auth_data")

            logger.info(f"Configuring Garmin client for user {user.username}")
            configured = False
            try:
                configured = configure_garmin_client(auth_data)
            except Exception as cfg_err:
                logger.exception(f"Error configuring Garmin client: {cfg_err}")

            if configured:
                # Activities
                activities_url = f"/activitylist-service/activities/search/activities?limit=999&start=0"
                try:
                    garmin_activities = garth.client.connectapi(activities_url)
                    logger.info(f"Successfully fetched {len(garmin_activities) if garmin_activities else 0} Garmin activities")
                except Exception as act_err:
                    logger.exception(f"Failed to fetch Garmin activities: {act_err}")

                # Prepare date range
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)

                # Steps and weight containers
                garmin_steps = []
                garmin_weights = []

                # Weight fetching (try helper then REST fallback)
                try:
                    if start_date and end_date:
                        days = (end_date - start_date).days + 1
                        end_str = end_date.isoformat()
                        start_str = start_date.isoformat()
                    else:
                        days = 365
                        end_dt = timezone.now().date()
                        end_str = end_dt.isoformat()
                        start_str = (end_dt - timedelta(days=days - 1)).isoformat()

                    try:
                        garmin_weights = garth.WeightData.list(end=end_str, days=days)
                    except Exception as w_helper_err:
                        logger.exception(f"Garmin WeightData.list() helper failed: {w_helper_err}")
                        try:
                            weight_url = f"/weight-service/weight/range/{start_str}/{end_str}?includeAll=true"
                            garmin_weights = garth.client.connectapi(weight_url)
                        except Exception as fallback_w_err:
                            logger.exception(f"Failed to fetch Garmin weight data via fallback endpoint: {fallback_w_err}")
                    logger.info(f"Successfully fetched {len(garmin_weights) if garmin_weights else 0} weight records")
                except Exception as weight_err:
                    logger.exception(f"Failed to fetch weight data: {weight_err}")
                    garmin_weights = []

                # Hydration day-by-day
                garmin_hydration = []
                current_date = start_date
                max_iterations = 50
                iteration_count = 0
                while current_date <= end_date and iteration_count < max_iterations:
                    if current_date > timezone.localtime().date():
                        logger.debug(f"Skipping future hydration date {current_date}")
                        current_date += timedelta(days=1)
                        iteration_count += 1
                        continue

                    url = f"/usersummary-service/stats/hydration/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                    daily_hydration_data = None
                    retry_count = 0
                    max_retries = 1
                    while retry_count <= max_retries and daily_hydration_data is None:
                        try:
                            daily_hydration_data = garth.client.connectapi(url)
                            logger.info(f"Successfully fetched hydration data for {current_date}")
                        except GarthHTTPError as api_err:
                            if api_err.status_code in [401, 403]:
                                if retry_count == 0:
                                    logger.warning(f"Auth error on hydration API for {current_date}, attempting refresh and retry.")
                                    try:
                                        refreshed = refresh_oauth2_only(auth_data)
                                        if refreshed:
                                            # persist refreshed tokens if returned
                                            try:
                                                garmin_auth_service.auth_data = refreshed
                                                garmin_auth_service.save()
                                                auth_data = refreshed
                                                logger.info("Persisted refreshed Garmin tokens during hydration retry")
                                            except Exception as persist_err:
                                                logger.exception(f"Failed to persist refreshed Garmin auth_data during hydration retry: {persist_err}")
                                            if configure_garmin_client(auth_data):
                                                retry_count += 1
                                                continue
                                        else:
                                            if configure_garmin_client(auth_data):
                                                retry_count += 1
                                                continue
                                    except Exception as refresh_err:
                                        logger.exception(f"Failed to refresh Garmin tokens during hydration retry: {refresh_err}")
                                        break
                                    logger.error(f"Token refresh failed during hydration sync for {current_date}")
                                    break
                                else:
                                    logger.error(f"Retry failed after refresh for hydration API {current_date}")
                                    break
                            elif api_err.status_code == 404:
                                logger.debug(f"Hydration API not available for {current_date}")
                                break
                            else:
                                logger.exception(f"Unexpected API error fetching hydration for {current_date}: {api_err}")
                                break
                        except Exception as api_err:
                            logger.exception(f"Hydration API failed for {current_date}: {api_err}")
                            break
                        retry_count += 1 if daily_hydration_data is None else 0

                    if daily_hydration_data and len(daily_hydration_data) > 0:
                        garmin_hydration.extend(daily_hydration_data)

                    current_date += timedelta(days=1)
                    iteration_count += 1

                if iteration_count >= max_iterations:
                    logger.error(f"Hydration sync loop exceeded maximum iterations ({max_iterations}). Last processed date: {current_date}")

                # Steps day-by-day
                current_date = start_date
                max_iterations = 50
                iteration_count = 0
                while current_date <= end_date and iteration_count < max_iterations:
                    if current_date > timezone.localtime().date():
                        current_date += timedelta(days=1)
                        iteration_count += 1
                        continue

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
                                    try:
                                        refreshed = refresh_oauth2_only(auth_data)
                                        if refreshed:
                                            # persist refreshed tokens if returned
                                            try:
                                                garmin_auth_service.auth_data = refreshed
                                                garmin_auth_service.save()
                                                auth_data = refreshed
                                                logger.info("Persisted refreshed Garmin tokens during steps retry")
                                            except Exception as persist_err:
                                                logger.exception(f"Failed to persist refreshed Garmin auth_data during steps retry: {persist_err}")
                                            if configure_garmin_client(auth_data):
                                                retry_count += 1
                                                continue
                                        else:
                                            if configure_garmin_client(auth_data):
                                                retry_count += 1
                                                continue
                                    except Exception as refresh_err:
                                        logger.exception(f"Failed to refresh Garmin tokens during steps retry: {refresh_err}")
                                        break
                                    logger.error(f"Token refresh failed during steps sync for {current_date}")
                                    break
                                else:
                                    logger.error(f"Retry failed after refresh for steps API {current_date}")
                                    break
                            elif api_err.status_code == 404:
                                logger.debug(f"Steps API not available for {current_date}")
                                break
                            else:
                                logger.exception(f"Unexpected API error fetching steps for {current_date}: {api_err}")
                                break
                        except Exception as api_err:
                            logger.warning(f"Steps API failed for {current_date}: {api_err}")
                            break
                        retry_count += 1 if daily_steps_data is None else 0

                    if daily_steps_data and len(daily_steps_data) > 0:
                        garmin_steps.extend(daily_steps_data)
                    current_date += timedelta(days=1)
                    iteration_count += 1

                if iteration_count >= max_iterations:
                    logger.error(f"Steps sync loop exceeded maximum iterations ({max_iterations}). Last processed date: {current_date}")

                logger.info(f"Successfully fetched {len(garmin_steps) if garmin_steps else 0} Garmin steps records")

                # Sleep data (preferred helper, fallback to daily)
                try:
                    try:
                        days = (end_date - start_date).days + 1
                        end_str = end_date.isoformat()
                        start_str = start_date.isoformat()
                    except Exception:
                        days = 30
                        end_str = timezone.now().date().isoformat()
                        start_str = (timezone.now().date() - timedelta(days=days - 1)).isoformat()

                    try:
                        garmin_sleep = garth.SleepData.list(end_str, days)
                        logger.info(f"Fetched {len(garmin_sleep) if garmin_sleep else 0} Garmin sleep records via garth helper")
                    except Exception as sleep_helper_err:
                        logger.exception(f"Garmin SleepData.list() helper failed: {sleep_helper_err}")
                        g_sleep = []
                        current_date = start_date
                        iteration_count = 0
                        max_iterations = max(50, days + 5)
                        while current_date <= end_date and iteration_count < max_iterations:
                            try:
                                if current_date > timezone.localtime().date():
                                    current_date += timedelta(days=1)
                                    iteration_count += 1
                                    continue
                                url = f"/wellness-service/wellness/dailySleepData/{garth.client.username}?date={current_date.isoformat()}&nonSleepBufferMinutes=60"
                                resp = None
                                try:
                                    resp = garth.client.connectapi(url)
                                except Exception as e:
                                    logger.debug(f"Garmin sleep daily endpoint failed for {current_date}: {e}")
                                    resp = None
                                if resp:
                                    g_sleep.append(resp)
                            except Exception as inner_e:
                                logger.warning(f"Error fetching Garmin sleep for {current_date}: {inner_e}")
                            current_date += timedelta(days=1)
                            iteration_count += 1
                        garmin_sleep = g_sleep
                        logger.info(f"Fetched {len(garmin_sleep) if garmin_sleep else 0} Garmin sleep records via daily endpoint fallback")
                except Exception as sleep_err:
                    logger.exception(f"Failed to fetch Garmin sleep data: {sleep_err}")

                logger.info(f"Successfully fetched Garmin data. Activities: {len(garmin_activities) if garmin_activities else 0}, Steps records: {len(garmin_steps) if garmin_steps else 0}, Hydration records: {len(garmin_hydration) if garmin_hydration else 0}, Sleep records: {len(garmin_sleep) if garmin_sleep else 0}")
            else:
                logger.error("Failed to configure Garmin client")
                garmin_activities = []
                garmin_steps = []
                garmin_sleep = []
    except ConnectedService.DoesNotExist:
        logger.warning("No Garmin service connected for user")
        garmin_activities = []
        garmin_steps = []
        garmin_sleep = []
    except Exception as e:
        logger.exception(f"Error fetching Garmin data: {e}")
        garmin_activities = []
        garmin_steps = []
        garmin_sleep = []

    try:
        liftosaur_auth = ConnectedService.objects.get(user=user, service_name='liftosaur')
        liftosaur_user_id = liftosaur_auth.auth_data.get('user_id')
        session_token = liftosaur_auth.auth_data.get('session_token')
        logger.info(f"Liftosaur auth_data present keys: {list(liftosaur_auth.auth_data.keys()) if isinstance(liftosaur_auth.auth_data, dict) else 'unknown'}")
        if not liftosaur_user_id or not session_token:
            logger.warning(f"Liftosaur auth data incomplete or missing user_id/session_token for user {user.id}")
            liftosaur_data = {}
        else:
            try:
                liftosaur_data = liftosaur_download(liftosaur_user_id, session_token)
                logger.info(f"Successfully fetched Liftosaur data: type={type(liftosaur_data)}, items={len(liftosaur_data) if hasattr(liftosaur_data, '__len__') else 'n/a'}")
            except Exception as ld_err:
                logger.exception(f"Error downloading Liftosaur data: {ld_err}")
                liftosaur_data = {}
    except ConnectedService.DoesNotExist:
        logger.warning("No Liftosaur service connected for user")
        liftosaur_data = {}
    except Exception as e:
        logger.exception(f"Error fetching Liftosaur data: {e}")
        liftosaur_data = {}

    # If the user has Health Connect linked, kick off the fast staging sync (write-only ingestion)
    try:
        hc_auth = ConnectedService.objects.get(user=user, service_name='healthconnect')
        try:
            healthconnect_sync_and_stage_task.delay(user.id)
            logger.info(f"Triggered Health Connect staged sync for user {user.id}")
        except Exception as e:
            logger.warning(f"Failed to trigger Health Connect staged sync for user {user.id}: {e}")
    except ConnectedService.DoesNotExist:
        # No HC connection for this user — that's fine.
        logger.debug(f"No Health Connect ConnectedService for user {user.id}; skipping staged sync trigger")

    # 4. Process and save data in priority order
    # Delegate heavy processing to core.data_processor.process_and_save_user_data
    try:
        # Log priorities and fetched data sizes to aid debugging when workouts are not created
        try:
            logger.info(f"Priorities by type for user {user.username}: {priorities_by_type}")
            logger.info(f"Garmin: activities={len(garmin_activities) if garmin_activities is not None else 0}, steps={len(garmin_steps) if garmin_steps is not None else 0}, hydration={len(garmin_hydration) if garmin_hydration is not None else 0}, sleep={len(garmin_sleep) if garmin_sleep is not None else 0}")
            logger.info(f"HealthConnect keys: {list(hc_data.keys()) if isinstance(hc_data, dict) else type(hc_data)}; Liftosaur type: {type(liftosaur_data)}")
        except Exception:
            logger.exception("Failed to log pre-processing debug info for sync inputs")
        summary = process_and_save_user_data(user, priorities_by_type, garmin_activities, garmin_steps, garmin_hydration, hc_data, liftosaur_data, garmin_sleep)
        # If process_and_save_user_data returns a summary dict, log totals similarly to previous behavior
        if isinstance(summary, dict):
            logger.info(f"Processed summary for user {user.username}: {summary}")
        else:
            logger.info(f"Processed user data for {user.username}")
    except Exception as e:
        logger.exception(f"Error processing/saving data for user {user.id}: {e}")
        return

    # 5. Process nutrition data (no priority system yet, just process from Health Connect)
    if 'nutrition' in hc_data and hc_data['nutrition']:
        nutrition_data = hc_data['nutrition']

        # Check if nutrition data is properly fetched
        if isinstance(nutrition_data, dict):
            logger.error("Invalid nutrition format received: expected list of NutritionEntry objects for data['nutrition']")
            return

        # ... existing code ...

    logger.info(f"Sync completed successfully for user {user_id}")
