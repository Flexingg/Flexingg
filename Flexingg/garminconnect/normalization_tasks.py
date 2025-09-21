from celery import shared_task
from decimal import Decimal
import logging

from core.models import BodyWeight
from .models import GarminBodyWeight
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task
def normalize_garmin_weight_data(user_id):
    """
    Normalize Garmin body weight data to unified BodyWeight model.
    """
    try:
        user_weights = GarminBodyWeight.objects.filter(user_id=user_id)

        normalized_count = 0

        with transaction.atomic():
            for garmin_weight in user_weights:
                # Check if already normalized
                if BodyWeight.objects.filter(
                    user_id=user_id,
                    source='garmin',
                    source_id=str(garmin_weight.id)
                ).exists():
                    continue

                # Convert kg to lbs
                weight_lbs = (Decimal(garmin_weight.weight_kg) * Decimal('2.20462')).quantize(Decimal('0.01'))

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='garmin',
                    source_id=str(garmin_weight.id),
                    datetime=garmin_weight.datetime,
                    weight_lbs=weight_lbs,
                    data={
                        'original_weight_kg': garmin_weight.weight_kg,
                        'source_type': garmin_weight.source_type,
                        'garmin_raw_data': garmin_weight.raw_data
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing Garmin weight data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}