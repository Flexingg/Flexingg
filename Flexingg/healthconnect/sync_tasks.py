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
# ... existing code …

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
        # profile is a UserProfile (not a wrapper), use it directly as the FK target
        hc_auth = ConnectedService.objects.get(user=profile, service_name='healthconnect')
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

# New imports for staging & normalization-by-plan
from .models import HealthConnectRawData
from .normalizers import normalize_and_aggregate_record

@shared_task
def healthconnect_sync_and_stage_task(profile_id):
    """
    New task (plan-driven): fetches data from the HC gateway and writes raw JSON
    into HealthConnectRawData (staging). This is a fast, write-only operation.
    After staging, it triggers the processing task to normalize and aggregate data.
    """
    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        logger.error(f"No UserProfile for ID {profile_id}")
        return {'success': False, 'error': 'No profile found'}

    try:
        # profile is the UserProfile instance used by ConnectedService.user FK
        hc_auth = ConnectedService.objects.get(user=profile, service_name='healthconnect')
    except ConnectedService.DoesNotExist:
        logger.warning(f"No HC connection for profile {profile_id}")
        return {'success': False, 'error': 'No Health Connect connection'}

    client = HCGatewayClient(auth_data=hc_auth.auth_data)
    saved_count = 0
    try:
        client._ensure_auth()
        data = client.fetch_recent(hours=168)
        for method, records in data.items():
            for record in records:
                record_id = record.get('_id', str(timezone.now()))
                # parse start/end times defensively
                start_time = None
                end_time = None
                try:
                    start_s = record.get('start', '')
                    if start_s:
                        start_time = timezone.datetime.fromisoformat(start_s.replace('Z', '+00:00'))
                except Exception:
                    start_time = None

                try:
                    end_s = record.get('end', '')
                    if end_s:
                        end_time = timezone.datetime.fromisoformat(end_s.replace('Z', '+00:00'))
                except Exception:
                    end_time = None

                if end_time and not is_aware(end_time):
                    end_time = make_aware(end_time)

                app_source = record.get('app', 'unknown')

                # Write to staging model quickly
                HealthConnectRawData.objects.update_or_create(
                    profile=profile,
                    method=method,
                    record_id=record_id,
                    defaults={
                        'start_time': start_time or timezone.now(),
                        'end_time': end_time,
                        'data': record.get('data', {}),
                        'app_source': app_source,
                        'is_processed': False,
                    }
                )
                saved_count += 1

        # Persist tokens and last sync timestamp
        hc_auth.auth_data.update({
            'token': client.token,
            'refresh': client.refresh_token,
            'expiry': client.expiry.isoformat() if client.expiry else None,
        })
        hc_auth.save()

        profile.hc_last_sync = timezone.now()
        profile.save(update_fields=['hc_last_sync'])

        # Trigger the staged processing task
        try:
            process_staged_healthconnect_data.delay(profile_id)
            logger.info(f"Triggered staged processing for profile {profile_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger staged processing for profile {profile_id}: {e}")

        logger.info(f"Health Connect (staging) sync completed for profile {profile_id}: {saved_count} staged")
        return {'success': True, 'staged': saved_count}

    except Exception as e:
        logger.exception("Error during healthconnect_sync_and_stage_task for profile %s: %s", profile_id, e)
        return {'success': False, 'error': str(e)}


@shared_task
def process_staged_healthconnect_data(profile_id, limit: int = 1000):
    """
    Processes unprocessed HealthConnectRawData rows for a profile using the new
    normalization pipeline (normalize_and_aggregate_record). Marks rows processed.
    The limit parameter can be used to batch-process large backfills.
    """
    qs = HealthConnectRawData.objects.filter(profile_id=profile_id, is_processed=False).order_by('created_at')[:limit]
    records = list(qs)
    if not records:
        logger.info(f"No staged HealthConnectRawData to process for profile {profile_id}")
        return {'processed': 0}

    processed = 0
    for rec in records:
        try:
            normalize_and_aggregate_record(rec)
            processed += 1
        except Exception as e:
            logger.exception("Failed to process staged record %s: %s", rec.record_id, e)

    # Mark batch as processed
    try:
        HealthConnectRawData.objects.filter(profile_id=profile_id, record_id__in=[r.record_id for r in records]).update(is_processed=True)
    except Exception:
        logger.exception("Failed to mark staged records as processed for profile %s", profile_id)

    logger.info("Processed %d staged HealthConnectRawData records for profile %s", processed, profile_id)
    return {'processed': processed}