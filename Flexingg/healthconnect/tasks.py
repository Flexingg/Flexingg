from celery import shared_task
from .utils import HCGatewayClient
from .models import HealthConnectData
from core.models import UserProfile, ConnectedService
from django.utils import timezone
from django.utils.timezone import make_aware, is_aware
from decimal import Decimal
import logging
import decimal

logger = logging.getLogger(__name__)

@shared_task
def healthconnect_sync_task(profile_id):
    """
    Celery task for syncing Health Connect data asynchronously.
    Fetches recent data (last 7 days) and updates HealthConnectData records.
    """
    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        logger.error(f"No UserProfile for ID {profile_id}")
        return {'success': False, 'error': 'No profile found'}

    try:
        hc_auth = ConnectedService.objects.get(user=profile.user, service_name='healthconnect')
    except ConnectedService.DoesNotExist:
        logger.warning(f"No HC connection for profile {profile_id}")
        return {'success': False, 'error': 'No Health Connect connection'}

    client = HCGatewayClient(auth_data=hc_auth.auth_data)

    saved_count = 0
    try:
        client._ensure_auth()  # Will login or refresh using hc_username/hc_password
        # Fetch recent data (last 7 days)
        data = client.fetch_recent(hours=168)  # 7 days * 24 hours
        for method, records in data.items():
            for record in records:
                # Extract key fields (mirror sync_healthconnect view)
                record_id = record.get('_id', str(timezone.now()))
                start_time_str = record.get('start', '').replace('Z', '+00:00')
                start_time = timezone.datetime.fromisoformat(start_time_str)
                end_time_str = record.get('end', '').replace('Z', '+00:00') if record.get('end') else None
                end_time = timezone.datetime.fromisoformat(end_time_str) if end_time_str else None
                if not is_aware(end_time):
                    end_time = make_aware(end_time)
                app_source = record.get('app', 'unknown')
                # Save or update
                HealthConnectData.objects.update_or_create(
                    profile=profile,
                    method=method,
                    record_id=record_id,
                    defaults={
                        'start_time': start_time,
                        'end_time': end_time,
                        'data': record.get('data', {}),
                        'app_source': app_source,
                    }
                )
                saved_count += 1

        # Update ConnectedService with tokens
        hc_auth.auth_data.update({
            'token': client.token,
            'refresh': client.refresh_token,
            'expiry': client.expiry.isoformat() if client.expiry else None,
        })
        hc_auth.save()

        profile.hc_last_sync = timezone.now()
        profile.save(update_fields=['hc_last_sync'])

        # Trigger normalization tasks for the synced data
        try:
            normalize_healthconnect_weight_data.delay(profile_id)
            normalize_healthconnect_steps_data.delay(profile_id)
            normalize_healthconnect_nutrition_data.delay(profile_id)
            normalize_healthconnect_sleep_data.delay(profile_id)
            normalize_healthconnect_hydration_data.delay(profile_id)
            logger.info(f"Triggered normalization tasks for profile {profile_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger normalization tasks for profile {profile_id}: {e}")

        logger.info(f"Health Connect sync completed for profile {profile_id}: {saved_count} records saved")
        return {'success': True, 'saved': saved_count}

    except Exception as e:
        logger.error(f"Error during Health Connect sync for profile {profile_id}: {str(e)}")
        return {'success': False, 'error': str(e)}
@shared_task
def normalize_healthconnect_weight_data(user_id):
    """
    Extract and normalize weight data from HealthConnectData to unified BodyWeight model.
    """
    from core.models import BodyWeight
    from .models import HealthConnectData
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Find weight-related records in HealthConnectData
        weight_records = HealthConnectData.objects.filter(
            profile_id=user_id,
            method='weight'
        )

        normalized_count = 0

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
                weight_kg = data.get('weight')

                if not weight_kg:
                    logger.warning(f"No weight data in record {record.record_id}")
                    continue

                # Convert kg to lbs
                weight_lbs = (Decimal(str(weight_kg)) * Decimal('2.20462')).quantize(Decimal('0.01'))

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='healthconnect',
                    source_id=record.record_id,
                    datetime=record.start_time,
                    weight_lbs=weight_lbs,
                    data={
                        'original_weight_kg': weight_kg,
                        'healthconnect_data': data,
                        'app_source': record.app_source
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Health Connect weight data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def normalize_healthconnect_steps_data(user_id):
    """
    Extract and normalize steps data from HealthConnectData to unified DailySteps model.
    """
    from core.models import DailySteps
    from .models import HealthConnectData
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

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
    from core.models import NutritionEntry
    from .models import HealthConnectData
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

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
@shared_task
def normalize_healthconnect_hydration_data(user_id):
    """
    Extract and normalize hydration data from HealthConnectData to unified DailyWater model.
    """
    from core.models import DailyWater
    from .models import HealthConnectData
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

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
    from core.models import Sleep
    from .models import HealthConnectData
    from django.db import transaction
    import logging

    logger = logging.getLogger(__name__)

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