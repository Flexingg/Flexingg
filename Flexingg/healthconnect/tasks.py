from celery import shared_task
from .utils import HCGatewayClient
from .models import HealthConnectData
from core.models import UserProfile
from django.utils import timezone
from django.utils.timezone import make_aware, is_aware
import logging

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

    if not profile.hc_username:
        logger.warning(f"No HC connection for profile {profile_id}")
        return {'success': False, 'error': 'No Health Connect connection'}

    client = HCGatewayClient()
    # Restore tokens from profile if present
    if profile.hc_token:
        client.token = profile.hc_token
        client.refresh_token = profile.hc_refresh_token
        client.expiry = profile.hc_token_expiry

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

        # Update profile with tokens and last_sync
        profile.hc_token = client.token
        profile.hc_refresh_token = client.refresh_token
        if client.expiry and not is_aware(client.expiry):
            client.expiry = make_aware(client.expiry)
        profile.hc_token_expiry = client.expiry
        profile.hc_last_sync = timezone.now()
        profile.save(update_fields=['hc_token', 'hc_refresh_token', 'hc_token_expiry', 'hc_last_sync'])

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
                weight_lbs = weight_kg * 2.20462

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