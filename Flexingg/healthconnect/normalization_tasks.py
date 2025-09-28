from celery import shared_task
from decimal import Decimal, InvalidOperation
import logging
import json
from django.db import transaction
import re
import decimal

from core.models import BodyWeight, DailySteps, NutritionEntry, DailyWater, Sleep
from .models import HealthConnectData

logger = logging.getLogger(__name__)


@shared_task
def normalize_healthconnect_weight_data(user_id):
    """
    Extract and normalize weight data from HealthConnectData to unified BodyWeight model.
    """
    try:
        # Find weight-related records in HealthConnectData
        weight_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='weight'
        )

        normalized_count = 0

        def _parse_weight_to_kg(raw):
            """
            Accepts various shapes for weight values and returns a Decimal in kilograms or None.
            Handles:
              - numeric types (int/float/Decimal)
              - numeric strings ("70", "70.5")
              - strings with units ("155 lb", "155lbs", "70 kg")
              - dicts like {'value': 70, 'unit': 'kg'} or {'inKilograms': 70}
            Returns: Decimal (kg) or None
            """
            from decimal import InvalidOperation
            import re

            if raw is None:
                return None

            # Numeric types
            if isinstance(raw, (int, float, Decimal)):
                try:
                    return Decimal(str(raw))
                except InvalidOperation:
                    return None

            # Dict shapes
            if isinstance(raw, dict):
                # Common Health Connect shapes
                if 'inKilograms' in raw:
                    try:
                        return Decimal(str(raw['inKilograms']))
                    except InvalidOperation:
                        return None
                if 'kg' in raw:
                    try:
                        return Decimal(str(raw['kg']))
                    except InvalidOperation:
                        return None
                # value + unit
                if 'value' in raw:
                    val = raw['value']
                    unit = (raw.get('unit') or '').lower()
                    try:
                        dval = Decimal(str(val))
                    except InvalidOperation:
                        return None
                    if 'lb' in unit:
                        return (dval / Decimal('2.20462'))
                    return dval
                # last-resort: try to stringify and extract number
                raw_str = json.dumps(raw) if not isinstance(raw, str) else raw
            else:
                raw_str = str(raw).strip()

            # Strings: extract first numeric token and detect unit
            m = re.search(r'([-+]?\d{1,3}(?:[,\d]*\d)?(?:\.\d+)?)', raw_str)
            if not m:
                return None
            num_str = m.group(1).replace(',', '')
            try:
                val = Decimal(num_str)
            except InvalidOperation:
                return None

            # Detect unit keywords in the remainder of the string
            low = raw_str.lower()
            if 'lb' in low or 'lbs' in low or 'pound' in low:
                # convert pounds to kg
                return (val / Decimal('2.20462'))
            # assume kilograms otherwise
            return val

        with transaction.atomic():
            for record in weight_records:
                # Check if already normalized
                if BodyWeight.objects.filter(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id
                ).exists():
                    continue

                # Extract weight data from JSON
                data = record.data
                weight_raw = data.get('weight')
                weight_kg = None
                try:
                    weight_kg = _parse_weight_to_kg(weight_raw)
                except Exception as e:
                    logger.warning(f"Failed to parse weight for record {record.record_id}: {e}; raw={weight_raw}")

                if weight_kg is None:
                    logger.warning(f"No parsable weight data in record {record.record_id}; raw={weight_raw}")
                    continue

                # Convert kg to lbs (keep two decimal places)
                try:
                    weight_lbs = (Decimal(weight_kg) * Decimal('2.20462')).quantize(Decimal('0.01'))
                except Exception as e:
                    logger.warning(f"Failed to convert weight to lbs for record {record.record_id}: {e}; kg={weight_kg}")
                    continue

                # Ensure values placed into the JSON/data field are JSON-serializable
                try:
                    original_weight_kg_serialized = float(weight_kg) if isinstance(weight_kg, Decimal) else weight_kg
                except Exception:
                    # Fallback to string representation if float conversion fails
                    original_weight_kg_serialized = str(weight_kg)

                try:
                    weight_lbs_for_data = float(weight_lbs) if isinstance(weight_lbs, Decimal) else weight_lbs
                except Exception:
                    weight_lbs_for_data = str(weight_lbs)

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id,
                    datetime=record.start_time,
                    weight_lbs=weight_lbs,
                    data={
                        'original_weight_kg': original_weight_kg_serialized,
                        'weight_lbs': weight_lbs_for_data,
                        'healthconnect_data': data,
                        'app_source': record.app_source
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect weight data for user {user_id}: {str(e)}")
        # Return the exception class names for clarity
        try:
            import traceback
            tb = traceback.format_exc()
        except Exception:
            tb = str(e)
        return {'status': 'error', 'message': str(e), 'trace': tb}


@shared_task
def normalize_healthconnect_steps_data(user_id):
    """
    Extract and normalize steps data from HealthConnectData to unified DailySteps model.
    """
    try:
        # Find steps-related records in HealthConnectData
        steps_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='steps'
        )

        normalized_count = 0

        with transaction.atomic():
            for record in steps_records:
                # Check if already normalized
                if DailySteps.objects.filter(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id
                ).exists():
                    continue

                # Extract steps data from JSON
                data = record.data
                steps_count = data.get('steps')

                if steps_count is None:
                    logger.warning(f"No steps data in record {record.record_id}")
                    continue

                # Use the date part of start_time for daily aggregation
                record_date = record.start_time.date()

                # Check if we already have steps for this date from Health Connect
                existing_steps = DailySteps.objects.filter(
                    user=user_id,
                    source='healthconnect',
                    date=record_date
                ).first()

                if existing_steps:
                    # Update existing record if new data is different
                    if existing_steps.steps != steps_count:
                        existing_steps.steps = steps_count
                        existing_steps.data = {
                            'healthconnect_data': data,
                            'app_source': record.app_source,
                            'record_id': record.record_id
                        }
                        existing_steps.save()
                else:
                    # Create new record
                    DailySteps.objects.create(
                        user_id=user_id,
                        source='healthconnect',
                        source_id=record.record_id,
                        date=record_date,
                        steps=steps_count,
                        data={
                            'healthconnect_data': data,
                            'app_source': record.app_source
                        }
                    )
                    normalized_count += 1

        logger.info(f"Normalized {normalized_count} steps records for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect steps data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def normalize_healthconnect_nutrition_data(user_id):
    """
    Extract and normalize nutrition data from HealthConnectData to unified NutritionEntry model.
    """
    try:
        # Find nutrition-related records in HealthConnectData
        nutrition_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='nutrition'
        )

        normalized_count = 0

        with transaction.atomic():
            for record in nutrition_records:
                # Check if already normalized
                if NutritionEntry.objects.filter(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id
                ).exists():
                    continue

                # Extract nutrition data from JSON
                data = record.data

                # Skip if no nutrition data
                if not data:
                    logger.warning(f"No nutrition data in record {record.record_id}")
                    continue

                # Extract basic nutrition info
                food_name = data.get('name')
                if not food_name:
                    # Fallback to app_source or a descriptive name
                    app_source = record.app_source or 'unknown'
                    if app_source == 'com.sbs.diet':
                        food_name = 'Diet App Meal'
                    else:
                        food_name = f'Food from {app_source}'

                calories = data.get('energy', {}).get('inCalories') if isinstance(data.get('energy'), dict) else None
                protein_grams = data.get('protein', {}).get('inGrams') if isinstance(data.get('protein'), dict) else None
                fat_grams = data.get('totalFat', {}).get('inGrams') if isinstance(data.get('totalFat'), dict) else None
                carbs_grams = data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(data.get('totalCarbohydrate'), dict) else None
                # Convert to Decimal for database storage
                try:
                    calories = Decimal(str(calories)) if calories is not None else None
                    protein_grams = Decimal(str(protein_grams)) if protein_grams is not None else None
                    fat_grams = Decimal(str(fat_grams)) if fat_grams is not None else None
                    carbs_grams = Decimal(str(carbs_grams)) if carbs_grams is not None else None
                except (ValueError, TypeError, decimal.InvalidOperation):
                    logger.warning(f"Invalid numeric data in record {record.record_id}")
                    continue

                # Convert calories from cal to kcal (divide by 1000)
                calories = calories / Decimal('1000') if calories is not None else None

                # Extract quantity information
                quantity_description = None
                quantity_grams = None

                # Try to get quantity from serving size or other fields
                if 'servingSize' in data and isinstance(data['servingSize'], dict):
                    serving_size = data['servingSize']
                    if 'inGrams' in serving_size:
                        quantity_grams = serving_size['inGrams']
                    elif 'inMilliliters' in serving_size:
                        # Convert mL to grams (approximate for liquids)
                        quantity_grams = serving_size['inMilliliters']

                # Create nutrition entry
                NutritionEntry.objects.create(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id,
                    datetime=record.start_time,
                    food_name=food_name,
                    quantity_description=quantity_description,
                    quantity_grams=quantity_grams,
                    calories=calories,
                    protein_grams=protein_grams,
                    fat_grams=fat_grams,
                    carbs_grams=carbs_grams,
                    data={
                        'healthconnect_data': data,
                        'app_source': record.app_source,
                        'raw_record': record.data
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} nutrition entries for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect nutrition data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def normalize_healthconnect_hydration_data(user_id):
    """
    Extract and normalize hydration data from HealthConnectData to unified DailyWater model.
    """
    try:
        # Find hydration-related records in HealthConnectData
        hydration_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='hydration'
        )

        normalized_count = 0

        with transaction.atomic():
            for record in hydration_records:
                # Check if already normalized
                if DailyWater.objects.filter(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id
                ).exists():
                    continue

                # Extract hydration data from JSON
                data = record.data
                hydration_amount = data.get('volume')

                if hydration_amount is None:
                    logger.warning(f"No hydration volume data in record {record.record_id}")
                    continue

                # Convert to ounces (Health Connect likely returns in liters or ml)
                # Assume hydration_amount is in liters, convert to ounces
                hydration_ounces = hydration_amount * 33.814  # liters to ounces

                # Use the date part of start_time for daily aggregation
                record_date = record.start_time.date()

                # Check if we already have water intake for this date from Health Connect
                existing_water = DailyWater.objects.filter(
                    user=user_id,
                    source='healthconnect',
                    date=record_date
                ).first()

                if existing_water:
                    # Update existing record by adding the new amount
                    existing_water.amount_ounces += hydration_ounces
                    existing_water.data = {
                        'healthconnect_data': data,
                        'app_source': record.app_source,
                        'record_id': record.record_id,
                        'aggregated': True
                    }
                    existing_water.save()
                else:
                    # Create new record
                    DailyWater.objects.create(
                        user_id=user_id,
                        source='healthconnect',
                        source_id=record.record_id,
                        date=record_date,
                        amount_ounces=hydration_ounces,
                        data={
                            'healthconnect_data': data,
                            'app_source': record.app_source
                        }
                    )
                    normalized_count += 1

        logger.info(f"Normalized {normalized_count} hydration records for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect hydration data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def normalize_healthconnect_sleep_data(user_id):
    """
    Extract and normalize sleep data from HealthConnectData to unified Sleep model.
    """
    try:
        # Find sleep-related records in HealthConnectData
        sleep_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='sleepSession'
        )

        normalized_count = 0

        with transaction.atomic():
            for record in sleep_records:
                # Check if already normalized
                if Sleep.objects.filter(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id
                ).exists():
                    continue

                # Extract sleep data from JSON
                data = record.data

                # Sleep sessions have start and end times from the record
                start_time = record.start_time
                end_time = record.end_time

                if not start_time or not end_time:
                    logger.warning(f"Missing start or end time in sleep record {record.record_id}")
                    continue

                Sleep.objects.create(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id,
                    start_time=start_time,
                    end_time=end_time,
                    data={
                        'healthconnect_data': data,
                        'app_source': record.app_source
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} sleep records for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect sleep data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}