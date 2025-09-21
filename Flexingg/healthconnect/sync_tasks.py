from celery import shared_task
from .utils import HCGatewayClient
from .models import HealthConnectData
from core.models import UserProfile, ConnectedService
from django.utils import timezone
from django.utils.timezone import make_aware, is_aware
from decimal import Decimal
import logging

# Import normalization tasks
from .normalization_tasks import (
    normalize_healthconnect_weight_data,
    normalize_healthconnect_steps_data,
    normalize_healthconnect_nutrition_data,
    normalize_healthconnect_sleep_data,
    normalize_healthconnect_hydration_data,
)

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
                if not is_aware(end_time) and end_time is not None:
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