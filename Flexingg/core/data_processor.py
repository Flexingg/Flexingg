import logging
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Workout, Sleep, DailySteps, DailyWater, NutritionEntry
from .currency_service import calculate_cardio_coins, calculate_gym_gems, calculate_xp_from_currencies

logger = logging.getLogger(__name__)


def process_and_save_user_data(user, priorities_by_type, garmin_activities, garmin_steps, garmin_hydration, hc_data, liftosaur_data):
    """
    Process fetched data and save to unified models following priorities.
    Returns a summary dict.
    """
    created_workouts = []
    updated_workouts = []

    # (moved) top-level info log will be emitted after inputs are normalized below

    # Normalize incoming payload shapes and log counts for visibility
    def _ensure_list(x):
        if x is None:
            return []
        if isinstance(x, list):
            return x
        if isinstance(x, dict):
            # Try common container keys used by APIs/libraries
            for key in ('activities', 'data', 'results', 'workouts', 'records', 'items'):
                if key in x and isinstance(x[key], list):
                    return x[key]
            # If dict is actually a single record, wrap it
            return [x]
        # Fallback: wrap whatever truthy value into a list
        return [x]

    garmin_activities = _ensure_list(garmin_activities)
    garmin_steps = _ensure_list(garmin_steps)
    garmin_hydration = _ensure_list(garmin_hydration)
    liftosaur_workouts = []
    if isinstance(liftosaur_data, list):
        liftosaur_workouts = liftosaur_data
    elif isinstance(liftosaur_data, dict):
        # Liftosaur API returns various shapes; try common keys and nested storage
        # 1) top-level 'workouts' or 'history'
        if 'workouts' in liftosaur_data and isinstance(liftosaur_data['workouts'], list):
            liftosaur_workouts = liftosaur_data['workouts']
        elif 'history' in liftosaur_data and isinstance(liftosaur_data['history'], list):
            liftosaur_workouts = liftosaur_data['history']
        else:
            # 2) nested under 'storage' (common: {'storage': {'history': [...]}})
            storage = liftosaur_data.get('storage') if isinstance(liftosaur_data.get('storage'), dict) else None
            if storage:
                if 'history' in storage and isinstance(storage['history'], list):
                    liftosaur_workouts = storage['history']
                elif 'workouts' in storage and isinstance(storage['workouts'], list):
                    liftosaur_workouts = storage['workouts']
                elif 'data' in storage and isinstance(storage['data'], list):
                    liftosaur_workouts = storage['data']
            # 3) If still empty, treat single workout-like dict as one workout (heuristic)
            if not liftosaur_workouts:
                if any(k in liftosaur_data for k in ('id', 'startTime', 'start_time', 'timestamp')):
                    liftosaur_workouts = [liftosaur_data]
                else:
                    # Attempt to find any list-valued key that looks like workouts and log it for debugging
                    for k, v in liftosaur_data.items():
                        if isinstance(v, list):
                            logger.debug(f"Liftosaur data contains list under key '{k}' (len={len(v)}); sample keys: {list(v[0].keys()) if v else '[]'}")
    else:
        liftosaur_workouts = []

    logger.debug(f"Data processor input shapes - garmin_activities: {len(garmin_activities)}, garmin_steps: {len(garmin_steps)}, garmin_hydration: {len(garmin_hydration)}, liftosaur_workouts: {len(liftosaur_workouts)}, hc_data_keys: {list(hc_data.keys()) if isinstance(hc_data, dict) else type(hc_data)}")
    if not liftosaur_workouts and liftosaur_data:
        try:
            logger.info(f"Liftosaur payload keys for user {user.username}: {list(liftosaur_data.keys()) if isinstance(liftosaur_data, dict) else type(liftosaur_data)}")
            # if storage present, show nested keys
            if isinstance(liftosaur_data, dict) and 'storage' in liftosaur_data and isinstance(liftosaur_data['storage'], dict):
                logger.info(f"Liftosaur.storage keys: {list(liftosaur_data['storage'].keys())}")
        except Exception:
            logger.debug("Failed to log Liftosaur payload sample for debugging")

    # Add top-level info so we can see priorities and input sizes in logs (safe position)
    try:
        logger.info(f"Processing inputs for user {user.username}: priorities={priorities_by_type}; garmin_activities={len(garmin_activities)}, garmin_steps={len(garmin_steps)}, garmin_hydration={len(garmin_hydration)}, liftosaur_workouts={len(liftosaur_workouts)}; hc_keys={(list(hc_data.keys()) if isinstance(hc_data, dict) else type(hc_data))}")
    except Exception:
        logger.info(f"Processing inputs for user {getattr(user, 'id', 'unknown')}: failed to stringify counts")

    logger.debug(f"Data processor input shapes - garmin_activities: {len(garmin_activities)}, garmin_steps: {len(garmin_steps)}, garmin_hydration: {len(garmin_hydration)}, liftosaur_workouts: {len(liftosaur_workouts)}, hc_data_keys: {list(hc_data.keys()) if isinstance(hc_data, dict) else type(hc_data)}")

    # Build an effective priorities mapping that falls back to any available sources
    # This prevents the sync from skipping all workouts when the user only has a high-priority
    # source configured but that source has no data for the period.
    effective_priorities_by_type = {}
    for dt in ['workout', 'sleep', 'steps', 'water']:
        # start with explicit user priorities if present
        user_sources = list(priorities_by_type.get(dt, [])) if isinstance(priorities_by_type, dict) else []
        # Add sources that have data but are not present in user priorities (as fallback)
        if dt == 'workout':
            if 'liftosaur' not in user_sources and len(liftosaur_workouts) > 0:
                user_sources.append('liftosaur')
            if 'garmin' not in user_sources and len(garmin_activities) > 0:
                user_sources.append('garmin')
            if 'healthconnect' not in user_sources and isinstance(hc_data, dict) and 'exerciseSession' in hc_data and hc_data.get('exerciseSession'):
                user_sources.append('healthconnect')
        elif dt == 'sleep':
            if 'healthconnect' not in user_sources and isinstance(hc_data, dict) and 'sleepSession' in hc_data and hc_data.get('sleepSession'):
                user_sources.append('healthconnect')
        elif dt == 'steps':
            if 'garmin' not in user_sources and len(garmin_steps) > 0:
                user_sources.append('garmin')
            if 'healthconnect' not in user_sources and isinstance(hc_data, dict) and 'steps' in hc_data and hc_data.get('steps'):
                user_sources.append('healthconnect')
        elif dt == 'water':
            if 'healthconnect' not in user_sources and isinstance(hc_data, dict) and 'hydration' in hc_data and hc_data.get('hydration'):
                user_sources.append('healthconnect')
            if 'garmin' not in user_sources and len(garmin_hydration) > 0:
                user_sources.append('garmin')
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in user_sources:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        effective_priorities_by_type[dt] = deduped

    logger.info(f"Effective priorities for user {user.username}: {effective_priorities_by_type}")

    for data_type in ['workout', 'sleep', 'steps', 'water']:
        # use effective priorities (falls back to available sources)
        if data_type not in effective_priorities_by_type or not effective_priorities_by_type.get(data_type):
            logger.warning(f"No priorities (or available sources) set for {data_type} for user {user.username}; skipping.")
            continue
        filled_dates = set()
        for source in effective_priorities_by_type[data_type]:
            if data_type == 'workout':
                if source == 'garmin':
                    from .normalization import normalize_garmin_activity_to_workout
                    # surface some info so we can debug why no workouts are created
                    before_created = len(created_workouts)
                    before_updated = len(updated_workouts)
                    logger.info(f"Starting Garmin activity processing for user {user.username}: {len(garmin_activities)} activities found")
                    if garmin_activities:
                        try:
                            sample = garmin_activities[0]
                            logger.info(f"Sample Garmin activity id: {sample.get('activityId', '[no id]')}, keys: {list(sample.keys())}")
                        except Exception:
                            logger.debug("Failed to log sample Garmin activity")
                    else:
                        logger.info("No Garmin activities to process")

                    for activity in garmin_activities:
                        norm = None
                        try:
                            norm = normalize_garmin_activity_to_workout(activity)
                        except Exception as e:
                            logger.exception(f"Exception during normalization of Garmin activity for user {user.username}: {e}")
                            norm = None
                        if not norm:
                            logger.debug(f"normalize_garmin_activity_to_workout returned None for activity (maybe unsupported format): {activity.get('activityId', '[no id]')}")
                            continue
                        sid = norm.get('source_id')
                        if not sid:
                            logger.debug(f"Normalized Garmin activity missing source_id; skipping. Norm keys: {list(norm.keys()) if isinstance(norm, dict) else norm}")
                            continue
                        existing = Workout.objects.filter(user=user, source='garmin', source_id=sid).first()
                        if existing:
                            needs_update = (
                                existing.start_time != norm.get('start_time') or
                                existing.end_time != norm.get('end_time') or
                                existing.data != norm.get('data')
                            )
                            if needs_update:
                                existing.start_time = norm.get('start_time')
                                existing.end_time = norm.get('end_time')
                                existing.data = norm.get('data')
                                existing.save()
                                updated_workouts.append(existing)
                                logger.info(f"Updated existing Garmin workout {existing.source_id} for user {user.username}")
                        else:
                            try:
                                w = Workout.objects.create(user=user, source='garmin', **norm)
                                created_workouts.append(w)
                                logger.info(f"Created Garmin workout {sid} for user {user.username}")
                            except Exception as e:
                                logger.exception(f"Failed to create Garmin workout for normalized record {sid}: {e}")
                                continue

                    created_delta = len(created_workouts) - before_created
                    updated_delta = len(updated_workouts) - before_updated
                    logger.info(f"Finished Garmin activity processing for user {user.username}: created={created_delta}, updated={updated_delta}")
                elif source == 'liftosaur' and liftosaur_data:
                    from .normalization import normalize_liftosaur_workout
                    # Use normalized liftosaur_workouts list prepared above
                    if not liftosaur_workouts:
                        logger.debug(f"No Liftosaur workouts to process for user {user.username}")
                    for workout in liftosaur_workouts:
                        try:
                            norm = normalize_liftosaur_workout(workout)
                        except Exception as e:
                            logger.exception(f"Exception normalizing Liftosaur workout for user {user.username}: {e}")
                            continue
                        if not norm:
                            logger.debug(f"normalize_liftosaur_workout returned None for workout: {workout.get('id', '[no id]')}")
                            continue
                        st_date = norm.get('start_time').date() if norm.get('start_time') else None
                        if st_date and st_date in filled_dates:
                            logger.debug(f"Skipping Liftosaur workout {norm.get('source_id')} due to filled date {st_date}")
                            continue
                        existing = Workout.objects.filter(user=user, source='liftosaur', source_id=norm.get('source_id')).first()
                        if existing:
                            needs_update = (
                                existing.start_time != norm.get('start_time') or
                                existing.end_time != norm.get('end_time') or
                                existing.data != norm.get('data')
                            )
                            if needs_update:
                                existing.start_time = norm.get('start_time')
                                existing.end_time = norm.get('end_time')
                                existing.data = norm.get('data')
                                existing.save()
                                updated_workouts.append(existing)
                                logger.debug(f"Updated existing Liftosaur workout {existing.source_id} for user {user.username}")
                        else:
                            w = Workout.objects.create(user=user, source='liftosaur', **norm)
                            created_workouts.append(w)
                            logger.debug(f"Created Liftosaur workout {norm.get('source_id')} for user {user.username}")
                        if st_date:
                            filled_dates.add(st_date)
                elif source == 'healthconnect' and 'exerciseSession' in hc_data:
                    from .normalization import normalize_hc_workout
                    for exercise in hc_data['exerciseSession']:
                        norm = normalize_hc_workout(exercise)
                        if norm and norm['start_time'].date() not in filled_dates:
                            existing = Workout.objects.filter(user=user, source='healthconnect', source_id=norm['source_id']).first()
                            if existing:
                                needs_update = (
                                    existing.start_time != norm['start_time'] or
                                    existing.end_time != norm['end_time'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.start_time = norm['start_time']
                                    existing.end_time = norm['end_time']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                w = Workout.objects.create(user=user, source='healthconnect', **norm)
                                created_workouts.append(w)
                            filled_dates.add(norm['start_time'].date())
            elif data_type == 'sleep':
                if source == 'healthconnect' and 'sleepSession' in hc_data:
                    from .normalization import normalize_hc_sleep
                    for sleep_session in hc_data['sleepSession']:
                        norm = normalize_hc_sleep(sleep_session)
                        if norm and norm['start_time'].date() not in filled_dates:
                            existing = Sleep.objects.filter(user=user, source='healthconnect', source_id=norm['source_id']).first()
                            if existing:
                                needs_update = (
                                    existing.start_time != norm['start_time'] or
                                    existing.end_time != norm['end_time'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.start_time = norm['start_time']
                                    existing.end_time = norm['end_time']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                Sleep.objects.create(user=user, source='healthconnect', **norm)
                            filled_dates.add(norm['start_time'].date())
            elif data_type == 'steps':
                if source == 'garmin':
                    from .normalization import normalize_garmin_steps
                    for day in garmin_steps:
                        norm = normalize_garmin_steps(day)
                        if norm['date'] not in filled_dates:
                            existing = DailySteps.objects.filter(user=user, source='garmin', date=norm['date']).first()
                            if existing:
                                needs_update = (
                                    existing.steps != norm['steps'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.steps = norm['steps']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                DailySteps.objects.create(user=user, source='garmin', date=norm['date'], steps=norm['steps'], data=norm['data'])
                            filled_dates.add(norm['date'])
                elif source == 'healthconnect' and 'steps' in hc_data:
                    from .normalization import normalize_hc_steps
                    for steps_record in hc_data['steps']:
                        norm = normalize_hc_steps(steps_record)
                        if norm and norm['date'] not in filled_dates:
                            existing = DailySteps.objects.filter(user=user, source='healthconnect', date=norm['date']).first()
                            if existing:
                                needs_update = (
                                    existing.steps != norm['steps'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.steps = norm['steps']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                DailySteps.objects.create(user=user, source='healthconnect', date=norm['date'], steps=norm['steps'], data=norm['data'])
                            filled_dates.add(norm['date'])
            elif data_type == 'water':
                logger.info(f"Starting water data sync for user {user.username}")
                logger.info(f"Processing water data from {source}")
                logger.info(f"Available sources for water: {priorities_by_type.get('water', [])}")
                logger.info(f"Garmin hydration records available: {len(garmin_hydration) if 'garmin_hydration' in locals() else 'N/A'}")
                logger.info(f"Health Connect hydration data available: {'hydration' in hc_data if 'hc_data' in locals() else 'N/A'}")
                if source == 'garmin':
                    from .normalization import normalize_garmin_hydration
                    for day in garmin_hydration:
                        norm = normalize_garmin_hydration(day)
                        if norm['date'] not in filled_dates:
                            existing = DailyWater.objects.filter(user=user, source='garmin', date=norm['date']).first()
                            if existing:
                                needs_update = (
                                    existing.amount_ounces != norm['amount_ounces'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.amount_ounces = norm['amount_ounces']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                logger.debug(f"Creating new Garmin water record: date={norm['date']}, amount={norm['amount_ounces']}")
                                DailyWater.objects.create(user=user, source='garmin', date=norm['date'], amount_ounces=norm['amount_ounces'], data=norm['data'])
                            filled_dates.add(norm['date'])
                elif source == 'healthconnect' and 'hydration' in hc_data:
                    from .normalization import normalize_hc_hydration
                    for record in hc_data['hydration']:
                        norm = normalize_hc_hydration(record)
                        if norm and norm['date'] not in filled_dates:
                            existing = DailyWater.objects.filter(user=user, source='healthconnect', date=norm['date']).first()
                            if existing:
                                needs_update = (
                                    existing.amount_ounces != norm['amount_ounces'] or
                                    existing.data != norm['data']
                                )
                                if needs_update:
                                    existing.amount_ounces = norm['amount_ounces']
                                    existing.data = norm['data']
                                    existing.save()
                            else:
                                logger.debug(f"Creating new Health Connect water record: date={norm['date']}, amount={norm['amount_ounces']}")
                                DailyWater.objects.create(user=user, source='healthconnect', **norm)
                            filled_dates.add(norm['date'])

    # 5. Process nutrition data (no priority system yet, just process from Health Connect)
    nutrition_count = 0
    if 'nutrition' in hc_data and hc_data['nutrition']:
        logger.info(f"Processing nutrition data from Health Connect for user {user.username}")
        for nutrition_record in hc_data['nutrition']:
            try:
                nutrition_data = nutrition_record.get('data', {})
                food_name = nutrition_data.get('name')
                if not food_name:
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

                if 'servingSize' in nutrition_record and isinstance(nutrition_record['servingSize'], dict):
                    serving_size = nutrition_record['servingSize']
                    if 'inGrams' in serving_size:
                        quantity_grams = serving_size['inGrams']
                    elif 'inMilliliters' in serving_size:
                        quantity_grams = serving_size['inMilliliters']

                # Parse datetime
                start_str = nutrition_record.get('start', '')
                if 'Z' in start_str:
                    start_str = start_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(start_str)

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
    summary = {
        'total_workouts': total_workouts,
        'workouts_from_liftosaur': workouts_from_liftosaur,
        'workouts_from_garmin': workouts_from_garmin,
        'workouts_from_hc': workouts_from_hc,
        'total_sleep': total_sleep,
        'total_steps': total_steps,
        'total_water': total_water,
        'total_nutrition': total_nutrition,
        'nutrition_processed': nutrition_count
    }
    logger.info(f"User {user.username} sync summary: {total_workouts} workouts ({workouts_from_liftosaur} from Liftosaur, {workouts_from_garmin} from Garmin, {workouts_from_hc} from Health Connect), {total_sleep} sleep records, {total_steps} step records, {total_water} water records, {total_nutrition} nutrition entries in the last 30 days")
    # --- Phase 1.3 & Phase 3.3: Award currencies & XP for processed workouts and update levels ---
    try:
        from .currency_service import (
            calculate_cardio_coins,
            calculate_gym_gems,
            award_currencies_and_xp,
            calculate_user_level,
            get_next_level_xp
        )

        # Use the user's synced weight if present, otherwise fallback to bodyweight_lbs
        user_bodyweight = getattr(user, 'weight') or getattr(user, 'bodyweight_lbs', 200)
        # Multipliers from profile (defaults already in model)
        cardio_multiplier = getattr(user, 'cardio_coins_multiplier', 1)
        gym_multiplier = getattr(user, 'gym_gems_multiplier', 1)

        processed_workouts = created_workouts + updated_workouts
        for w in processed_workouts:
            try:
                calories = 0
                if w.data and isinstance(w.data, dict):
                    calories = w.data.get('calories', 0) or 0
                # total lifting volume in lbs
                try:
                    volume_lbs = w.get_total_volume(unit='lb')
                except Exception:
                    volume_lbs = 0

                cardio_coins_amount = calculate_cardio_coins(calories, cardio_multiplier)
                gym_gems_amount = calculate_gym_gems(volume_lbs, user_bodyweight, gym_multiplier)

                # Centralized awarding — creates Transaction records and updates user balances & XP
                try:
                    award_result = award_currencies_and_xp(user, cardio_coins_amount, gym_gems_amount, garmin_activity=None)
                except Exception:
                    logger.exception(f"award_currencies_and_xp failed for user {user.username} workout {w.id}")
                    award_result = None

                # After awarding XP, check for level up and persist change
                try:
                    total_xp = user.xp or 0
                    new_level = calculate_user_level(total_xp)
                    if new_level and new_level != (user.level or 1):
                        logger.info(f"User {user.username} leveled up from {user.level} to {new_level}")
                        user.level = new_level
                        user.save()
                except Exception:
                    logger.exception(f"Error calculating/updating level for user {user.username}")
            except Exception as e:
                logger.exception(f"Error while processing currency awards for workout {w.id}: {e}")
    except Exception:
        logger.exception("Error in awarding currencies/XP during sync")
    return summary