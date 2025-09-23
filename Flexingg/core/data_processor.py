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

    for data_type in ['workout', 'sleep', 'steps', 'water']:
        if data_type not in priorities_by_type:
            logger.warning(f"No priorities set for {data_type} for user {user.username}; skipping.")
            continue
        filled_dates = set()
        for source in priorities_by_type[data_type]:
            if data_type == 'workout':
                if source == 'garmin':
                    for activity in garmin_activities:
                        # Normalization should be done upstream (core.normalization)
                        from .normalization import normalize_garmin_activity_to_workout
                        norm = normalize_garmin_activity_to_workout(activity)
                        if norm:
                            existing = Workout.objects.filter(user=user, source='garmin', source_id=norm['source_id']).first()
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
                                    updated_workouts.append(existing)
                            else:
                                w = Workout.objects.create(user=user, source='garmin', **norm)
                                created_workouts.append(w)
                elif source == 'liftosaur' and liftosaur_data:
                    from .normalization import normalize_liftosaur_workout
                    for workout in liftosaur_data.get('storage', {}).get('history', []):
                        norm = normalize_liftosaur_workout(workout)
                        if norm['start_time'].date() not in filled_dates:
                            existing = Workout.objects.filter(user=user, source='liftosaur', source_id=norm['source_id']).first()
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
                                    updated_workouts.append(existing)
                            else:
                                w = Workout.objects.create(user=user, source='liftosaur', **norm)
                                created_workouts.append(w)
                            filled_dates.add(norm['start_time'].date())
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
                                    updated_workouts.append(existing)
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