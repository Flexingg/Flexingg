import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import *
from core.models import ConnectedService
from .tasks import *
import logging
# --- Helper Functions ---

def convert_timestamp_to_datetime(ts):
    """Converts millisecond timestamp to a datetime object."""
    from django.utils import timezone
    if ts:
        from datetime import datetime
        dt = datetime.fromtimestamp(ts / 1000.0)
        return timezone.make_aware(dt)
    return timezone.now()

# --- Main View ---

@login_required
@require_POST
def sync_workout_data(request):
    """
    Triggers asynchronous sync of Liftosaur data for the logged-in user.
    Fetches from API using liftosaur_id and session_token if available, then processes.
    """
    user = request.user
    liftosaur_id = user.liftosaur_user_id
    if not liftosaur_id:
        return JsonResponse({'status': 'error', 'message': 'Liftosaur User ID not configured for this user.'}, status=400)

    session_token = user.liftosaur_session_token
    data = liftosaur_download(liftosaur_id, session_token)
    if not data:
        return JsonResponse({'status': 'error', 'message': 'Failed to fetch data from API'}, status=400)

    task = sync_liftosaur_data.delay(user.id, data, session_token)
    
    return JsonResponse({
        'status': 'success',
        'message': 'Sync initiated asynchronously.',
        'task_id': task.id
    })





logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["POST"])
def import_data(request):
    """
    Upload and import Liftosaur JSON file for the user.
    """
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
    
    json_file = request.FILES['file']
    if not json_file.name.endswith('.json'):
        return JsonResponse({'status': 'error', 'message': 'File must be JSON'}, status=400)
    
    try:
        json_data_str = json_file.read().decode('utf-8')
        logger.info(f"File size for user {request.user.id}: {len(json_data_str)} characters")
        task = sync_liftosaur_data.delay(request.user.id, json_data_str)
        return JsonResponse({
            'status': 'success',
            'task_id': task.id,
            'message': 'Import started asynchronously. Check Celery logs for progress.'
        })
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error for user {request.user.id}: {e}")
        return JsonResponse({'status': 'error', 'message': 'File encoding error (try UTF-8) or non-text file'}, status=400)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for user {request.user.id}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON file (check for BOM or structure)'}, status=400)
    except Exception as e:
        logger.error(f"Import error for user {request.user.id}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Import failed'}, status=500)
    
@login_required
def SaveLiftosaurTokenView(request):
    token = request.POST.get('liftosaur_session_token')
    if not token:
        return JsonResponse({'status': 'error', 'message': 'No token provided'})
    
    try:
        request.user.liftosaur_session_token = token
        request.user.save()
    
        s = requests.Session()
        s.cookies.set('session', token, domain='liftosaur.com')
        r = s.get('https://api3.liftosaur.com/api/storage')
        if r.ok:
            data = r.json()
            user_id = data.get('user_id') or data.get('id')
            if user_id:
                request.user.liftosaur_user_id = str(user_id)
                request.user.save()

                # Create or update the ConnectedService
                ConnectedService.objects.update_or_create(
                    user=request.user,
                    service_name='liftosaur',
                    defaults={'auth_data': {'user_id': str(user_id), 'session_token': token}}
                )

                return JsonResponse({'status': 'success', 'message': 'Token saved and Liftosaur connected successfully!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Token valid but could not fetch user ID'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid token or API error'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})