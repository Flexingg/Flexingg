import logging
from django.utils import timezone
from .models import HealthConnectData

logger = logging.getLogger(__name__)


def save_healthconnect_records(profile, data: dict) -> int:
    """
    Persist fetched Health Connect records into HealthConnectData model.
    Returns number of records saved.
    """
    saved_count = 0
    for method, records in data.items():
        for record in records:
            try:
                record_id = record.get('_id', str(timezone.now()))
                start_time_str = record.get('start', '').replace('Z', '+00:00')
                start_time = timezone.datetime.fromisoformat(start_time_str)
                end_time = None
                if record.get('end'):
                    end_time_str = record.get('end', '').replace('Z', '+00:00')
                    end_time = timezone.datetime.fromisoformat(end_time_str)
                app_source = record.get('app', 'unknown')

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
            except Exception as e:
                logger.error(f"Failed to save Health Connect record for profile {getattr(profile, 'id', 'unknown')}: {e}")
                continue
    return saved_count