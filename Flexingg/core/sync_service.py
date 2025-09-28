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
                garmin_weights = []

                # Add weight data fetching
                try:
                    # Compute days in the range (inclusive)
                    if start_date and end_date:
                        days = (end_date - start_date).days + 1
                        end_str = end_date.isoformat()
                        start_str = start_date.isoformat()
                    else:
                        # Fallback to a sensible default (last 365 days)
                        days = 365
                        end_dt = timezone.now().date()
                        end_str = end_dt.isoformat()
                        start_str = (end_dt - timedelta(days=days - 1)).isoformat()

                    # Preferred: use garth.WeightData.list(end, days)
                    try:
                        garmin_weights = garth.WeightData.list(end=end_str, days=days)
                    except Exception:
                        # Fallback to the REST range endpoint used by garth internally
                        weight_url = f"/weight-service/weight/range/{start_str}/{end_str}?includeAll=true"
                        garmin_weights = garth.client.connectapi(weight_url)

                    logger.info(f"Successfully fetched {len(garmin_weights) if garmin_weights else 0} weight records")
                except Exception as weight_err:
                    logger.warning(f"Failed to fetch weight data: {weight_err}")
                    garmin_weights = []
                
                # Fetch hydration data day by day
                garmin_hydration = []
                current_date = start_date
                max_iterations = 50  # Prevent infinite loops
                iteration_count = 0
                while current_date <= end_date and iteration_count < max_iterations:
                    try:
                        if current_date > timezone.localtime().date():
                       
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
                                        if refresh_oauth2_only(auth_data) and configure_garmin_client(auth_data):
                                            retry_count += 1
                                            continue
                                        else:
                                            logger.error(f"Token refresh failed during hydration sync for {current_date}")
                                            break
                                    else:
                                        logger.error(f"Retry failed after refresh for hydration API {current_date}")
                                        break
                                elif api_err.status_code == 404:
                                    logger.debug(f"Hydration API not available for {current_date}")
                                    break
                                else:
                                    raise
                            except Exception as api_err:
                                logger.warning(f"Hydration API failed for {current_date}: {api_err}")
                                break
                            retry_count += 1 if daily_hydration_data is None else 0

                        if daily_hydration_data and len(daily_hydration_data) > 0:
                            garmin_hydration.extend(daily_hydration_data)
                    except Exception as hydration_err:
                        logger.error(f"Error syncing hydration for {current_date} for user {user.id}: {hydration_err}")


                
                # Always increment the date, regardless of errors

                    current_date += timedelta(days=1)
                    iteration_count += 1

                if iteration_count >= max_iterations:
                    logger.error(f"Hydration sync loop exceeded maximum iterations ({max_iterations}). This indicates a potential infinite loop. Last processed date: {current_date}")

                
                # Fetch steps data day by day (Garmin API doesn't support date ranges for steps)
                current_date = start_date
                max_iterations = 50  # Prevent infinite loops
                iteration_count = 0

                while current_date <= end_date and iteration_count < max_iterations:
                    try:
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
                                        if refresh_oauth2_only(auth_data) and configure_garmin_client(auth_data):
                                            retry_count += 1
                                            continue
                                        else:
                                            logger.error(f"Token refresh failed during steps sync for {current_date}")
                                            break
                                    else:
                                        logger.error(f"Retry failed after refresh for steps API {current_date}")
                                        break
                                elif api_err.status_code == 404:
                                    logger.debug(f"Steps API not available for {current_date}")
                                    break
                                else:
                                    raise
                            except Exception as api_err:
                                logger.warning(f"Steps API failed for {current_date}: {api_err}")
                                break

                            retry_count += 1 if daily_steps_data is None else 0

                        if daily_steps_data and len(daily_steps_data) > 0:
                            garmin_steps.extend(daily_steps_data)
                    except Exception as steps_err:
                        logger.error(f"Error syncing steps for {current_date} for user {user.id}: {steps_err}")

                    # Always increment the date, regardless of errors
                    current_date += timedelta(days=1)
                    iteration_count += 1

                if iteration_count >= max_iterations:
                    logger.error(f"Steps sync loop exceeded maximum iterations ({max_iterations}). This indicates a potential infinite loop. Last processed date: {current_date}")

                # Fetch sleep data using garth helper (preferred) and fallback to daily endpoint
                try:
                    # Compute days in range (inclusive)
                    try:
                        days = (end_date - start_date).days + 1
                        end_str = end_date.isoformat()
                        start_str = start_date.isoformat()
                    except Exception:
                        # fallback to 30 days if dates missing
                        days = 30
                        end_str = timezone.now().date().isoformat()
                        start_str = (timezone.now().date() - timedelta(days=days - 1)).isoformat()

                    try:
                        # Preferred: use garth convenience method which returns structured objects
                        garmin_sleep = garth.SleepData.list(end_str, days)
                        logger.info(f"Fetched {len(garmin_sleep) if garmin_sleep else 0} Garmin sleep records via garth helper")
                    except Exception:
                        # Fallback: query dailySleepData endpoint day-by-day
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
                                    # The REST endpoint may return a dict for that day
                                    g_sleep.append(resp)
                            except Exception as inner_e:
                                logger.warning(f"Error fetching Garmin sleep for {current_date}: {inner_e}")
                            current_date += timedelta(days=1)
                            iteration_count += 1
                        garmin_sleep = g_sleep
                        logger.info(f"Fetched {len(garmin_sleep) if garmin_sleep else 0} Garmin sleep records via daily endpoint fallback")
                except Exception as sleep_err:
                    logger.warning(f"Failed to fetch Garmin sleep data: {sleep_err}")
                logger.info(f"Successfully fetched Garmin data. Activities: {len(garmin_activities)}, Steps records: {len(garmin_steps)}, Hydration records: {len(garmin_hydration)}")
                logger.info("Successfully fetched Garmin data")
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
        logger.error(f"Error fetching Garmin data: {e}")
        garmin_activities = []
        garmin_steps = []
        garmin_sleep = []

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
            # Persist raw Health Connect records into HealthConnectData model
            try:
                saved = save_healthconnect_records(user, hc_data)
                logger.info(f"Saved {saved} Health Connect records for user {user.username}")
            except Exception as e:
                logger.exception(f"Failed to save Health Connect raw records for user {user.id}: {e}")
            # Enqueue normalization task for weights (Health Connect) if weight data present
            if isinstance(hc_data, dict) and 'weight' in hc_data and hc_data.get('weight'):
                try:
                    normalize_healthconnect_weight_data.delay(user.id)
                except Exception:
                    logger.exception(f"Failed to enqueue weight normalization for user {user.id}")
            # Calculate date range for steps and hydration using steps data if available
            start_date = end_date = timezone.now().date()
            if 'steps' in hc_data and len(hc_data['steps']) > 0:
                start_date = timezone.make_aware(datetime.fromisoformat(hc_data['steps'][0][0]))
                end_date = timezone.make_aware(datetime.fromisoformat(hc_data['steps'][-1][0]))
            if 'hydration' in hc_data and len(hc_data['hydration']) > 0:
                start_date = min(start_date, timezone.make_aware(datetime.fromisoformat(hc_data['hydration'][0][0])))
                end_date = max(end_date, timezone.make_aware(datetime.fromisoformat(hc_data['hydration'][-1][0])))
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
    # Delegate heavy processing to core.data_processor.process_and_save_user_data
    try:
        # Log priorities and fetched data sizes to aid debugging when workouts are not created
        try:
            logger.info(f"Priorities by type for user {user.username}: {priorities_by_type}")
            logger.info(f"Garmin: activities={len(garmin_activities) if garmin_activities is not None else 0}, steps={len(garmin_steps) if garmin_steps is not None else 0}, hydration={len(garmin_hydration) if garmin_hydration is not None else 0}")
            logger.info(f"HealthConnect keys: {list(hc_data.keys()) if isinstance(hc_data, dict) else type(hc_data)}; Liftosaur type: {type(liftosaur_data)}")
        except Exception:
            logger.debug("Failed to log pre-processing debug info for sync inputs")
        summary = process_and_save_user_data(user, priorities_by_type, garmin_activities, garmin_steps, garmin_hydration, hc_data, liftosaur_data, garmin_sleep)
        # If process_and_save_user_data returns a summary dict, log totals similarly to previous behavior
        if isinstance(summary, dict):
            logger.info(f"Processed summary for user {user.username}: {summary}")
        else:
            logger.info(f"Processed user data for {user.username}")
    except Exception as e:
        logger.error(f"Error processing/saving data for user {user.id}: {e}")


    # 5. Process nutrition data (no priority system yet, just process from Health Connect)
    if 'nutrition' in hc_data and hc_data['nutrition']:
        logger.info(f"Processing nutrition data from Health Connect for user {user.username}")
        nutrition_count = 0
        for nutrition_record in hc_data['nutrition']:
            try:
                # Extract basic nutrition info
                # Extract basic nutrition info
                # The nutrition data is nested in nutrition_record['data']
                nutrition_data = nutrition_record.get('data', {})
                food_name = nutrition_data.get('name')
                if not food_name:
                    # Fallback to app_source or a descriptive name
                    app_source = nutrition_record.get('app', 'unknown')
                    if app_source == 'com.sbs.diet':
                        food_name = 'Diet App Meal'
                    else:
                        food_name = f'Food from {app_source}'

                calories = nutrition_data.get('energy', {}).get('inCalories') if isinstance(nutrition_data.get('energy'), dict) else None
                protein_grams = nutrition_data.get('protein', {}).get('inGrams') if isinstance(nutrition_data.get('protein'), dict) else None
                fat_grams = nutrition_data.get('totalFat', {}).get('inGrams') if isinstance(nutrition_data.get('totalFat'), dict) else None
                carbs_grams = nutrition_data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(nutrition_data.get('totalCarbohydrate'), dict) else None
                # Convert to float for database storage
                try:
                    calories = float(calories) if calories is not None else None
                    protein_grams = float(protein_grams) if protein_grams is not None else None
                    fat_grams = float(fat_grams) if fat_grams is not None else None
                    carbs_grams = float(carbs_grams) if carbs_grams is not None else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid numeric data in nutrition record {nutrition_record.get('_id', 'unknown')}")
                    continue

                # Convert calories from cal to kcal (divide by 1000)
                calories = calories / 1000 if calories is not None else None

                # Extract quantity information
                quantity_description = None
                quantity_grams = None

                # Try to get quantity from serving size or other fields
                if 'servingSize' in nutrition_record and isinstance(nutrition_record['servingSize'], dict):
                    serving_size = nutrition_record['servingSize']
                    if 'inGrams' in serving_size:
                        quantity_grams = serving_size['inGrams']
                    elif 'inMilliliters' in serving_size:
                        # Convert mL to grams (approximate for liquids)
                        quantity_grams = serving_size['inMilliliters']

                # Parse datetime
                start_str = nutrition_record.get('start', '')
                if 'Z' in start_str:
                    start_str = start_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(start_str)

                # Check if datetime is already timezone-aware
                if start_dt.tzinfo is not None:
                    nutrition_datetime = start_dt
                else:
                    nutrition_datetime = timezone.make_aware(start_dt)

                # Create or update nutrition entry
                existing = NutritionEntry.objects.filter(
                    user=user,
                    source='healthconnect',
                    source_id=nutrition_record.get('_id')
                ).first()
                data_dict = {
                    'healthconnect_data': nutrition_record,
                    'app_source': nutrition_record.get('app', 'unknown')
                }
                if existing:
                    needs_update = (
                        existing.datetime != nutrition_datetime or
                        existing.food_name != food_name or
                        existing.quantity_description != quantity_description or
                        existing.quantity_grams != quantity_grams or
                        existing.calories != calories or
                        existing.protein_grams != protein_grams or
                        existing.fat_grams != fat_grams or
                        existing.carbs_grams != carbs_grams or
                        existing.data != data_dict
                    )
                    if needs_update:
                        existing.datetime = nutrition_datetime
                        existing.food_name = food_name
                        existing.quantity_description = quantity_description
                        existing.quantity_grams = quantity_grams
                        existing.calories = calories
                        existing.protein_grams = protein_grams
                        existing.fat_grams = fat_grams
                        existing.carbs_grams = carbs_grams
                        existing.data = data_dict
                        existing.save()
                else:
                    NutritionEntry.objects.create(
                        user=user,
                        source='healthconnect',
                        source_id=nutrition_record.get('_id'),
                        datetime=nutrition_datetime,
                        food_name=food_name,
                        quantity_description=quantity_description,
                        quantity_grams=quantity_grams,
                        calories=calories,
                        protein_grams=protein_grams,
                        fat_grams=fat_grams,
                        carbs_grams=carbs_grams,
                        data=data_dict
                    )
                nutrition_count += 1
            except Exception as e:
                logger.error(f"Error processing nutrition record {nutrition_record.get('_id', 'unknown')}: {e}")
                continue

        logger.info(f"Processed {nutrition_count} nutrition entries from Health Connect for user {user.username}")


    # Log summary of what was processed
    thirty_days_ago = timezone.now() - timedelta(days=30)
    total_workouts = Workout.objects.filter(user=user, start_time__gte=thirty_days_ago).count()
    total_sleep = Sleep.objects.filter(user=user, start_time__gte=thirty_days_ago).count()
    total_steps = DailySteps.objects.filter(user=user, date__gte=thirty_days_ago.date()).count()
    total_nutrition = NutritionEntry.objects.filter(user=user, datetime__gte=thirty_days_ago).count()
    workouts_from_liftosaur = Workout.objects.filter(user=user, source='liftosaur', start_time__gte=thirty_days_ago).count()
    workouts_from_garmin = Workout.objects.filter(user=user, source='garmin', start_time__gte=thirty_days_ago).count()
    workouts_from_hc = Workout.objects.filter(user=user, source='healthconnect', start_time__gte=thirty_days_ago).count()
    total_water = DailyWater.objects.filter(user=user, date__gte=thirty_days_ago.date()).count()
    logger.info(f"User {user.username} sync summary: {total_workouts} workouts ({workouts_from_liftosaur} from Liftosaur, {workouts_from_garmin} from Garmin, {workouts_from_hc} from Health Connect), {total_sleep} sleep records, {total_steps} step records, {total_water} water records, {total_nutrition} nutrition entries in the last 30 days")
    return f"Sync completed for user {user_id}"