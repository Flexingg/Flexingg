import logging
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


def convert_timestamp_to_datetime(ts):
    """Converts millisecond timestamp to a timezone-aware datetime object."""
    if ts:
        try:
            dt = datetime.fromtimestamp(ts / 1000.0)
            return timezone.make_aware(dt)
        except Exception as e:
            logger.warning(f"Failed to convert timestamp {ts}: {e}")
    return timezone.now()


__all__ = ['convert_timestamp_to_datetime']