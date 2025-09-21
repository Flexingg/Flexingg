from celery import shared_task
from decimal import Decimal
import logging
from django.db import transaction

from core.models import BodyWeight
from .models import BodyMeasurement

logger = logging.getLogger(__name__)


@shared_task
def normalize_liftosaur_weight_data(user_id):
    """
    Normalize existing Liftosaur BodyMeasurement data to unified BodyWeight model.
    """
    try:
        user_measurements = BodyMeasurement.objects.filter(
            user_id=user_id,
            measurement_type='bodyweight'
        )

        normalized_count = 0

        with transaction.atomic():
            for measurement in user_measurements:
                # Check if already normalized
                if BodyWeight.objects.filter(
                    user_id=user_id,
                    source='liftosaur',
                    source_id=str(measurement.id)
                ).exists():
                    continue

                # Convert weight to lbs if needed
                weight_lbs = measurement.value
                if measurement.unit == 'kg':
                    weight_lbs = (Decimal(str(measurement.value)) * Decimal('2.20462')).quantize(Decimal('0.01'))

                BodyWeight.objects.create(
                    user_id=user_id,
                    source='liftosaur',
                    source_id=str(measurement.id),
                    datetime=measurement.timestamp,
                    weight_lbs=weight_lbs,
                    data={
                        'original_unit': measurement.unit,
                        'original_value': measurement.value,
                        'measurement_type': measurement.measurement_type
                    }
                )
                normalized_count += 1

        logger.info(f"Normalized {normalized_count} weight measurements for user {user_id}")
        return {'status': 'success', 'normalized': normalized_count}

    except Exception as e:
        logger.error(f"Error normalizing weight data for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}