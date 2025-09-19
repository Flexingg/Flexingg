import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import * #LEAVE AS IS*
from core.models import UserProfile
import json

logger = logging.getLogger(__name__)




@shared_task
def sync_liftosaur_data(user_id, data, session_token=None):
    """
    Process already-fetched Liftosaur data for the user asynchronously.
    """
    if not data:
        logger.error(f"No data provided for user_id: {user_id}")
        return {'status': 'error', 'message': 'No data to process'}

    return _process_liftosaur_data(user_id, data, session_token)