import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import *
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
    Fetches from API using liftosaur_id, then processes.
    """
    user = request.user
    liftosaur_id = user.liftosaur_user_id
    if not liftosaur_id:
        return JsonResponse({'status': 'error', 'message': 'Liftosaur User ID not configured for this user.'}, status=400)

    data = liftosaur_download(liftosaur_id)
    if not data:
        return JsonResponse({'status': 'error', 'message': 'Failed to fetch data from API'}, status=400)

    task = sync_liftosaur_data.delay(user.id, data)
    
    return JsonResponse({
        'status': 'success',
        'message': 'Sync initiated asynchronously.',
        'task_id': task.id
    })
@login_required
@require_POST
def store_body_measurement(request):
    """
    Reads bodyweight from the reference Liftosaur JSON and stores it as a BodyMeasurement
    for the current user.
    """
    json_path = r'REFERENCE\ ONLY/liftosaur_data\ (small).json'
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        settings = data.get('storage', {}).get('settings', {})
        bodyweight_data = settings.get('currentBodyweight', {})
        
        if not bodyweight_data:
            return JsonResponse({'status': 'error', 'message': 'No bodyweight data found in JSON'}, status=400)
        
        value = bodyweight_data.get('value')
        unit = bodyweight_data.get('unit')
        
        if value is None or unit is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid bodyweight data'}, status=400)
        
        user_profile = request.user.userprofile
        measurement_type = 'bodyweight'
        timestamp = datetime.now()
        
        BodyMeasurement.objects.update_or_create(
            user=user_profile,
            measurement_type=measurement_type,
            defaults={
                'value': value,
                'unit': unit,
                'timestamp': timestamp
            }
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Stored bodyweight: {value} {unit}'
        })
    
    except FileNotFoundError:
        return JsonResponse({'status': 'error', 'message': 'JSON file not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def store_programs(request):
    """
    Reads programs from the reference Liftosaur JSON and stores them as Program
    instances for the current user.
    """
    json_path = r'REFERENCE\ ONLY/liftosaur_data\ (small).json'
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        programs_data = data.get('storage', {}).get('programs', [])
        
        if not programs_data:
            return JsonResponse({'status': 'error', 'message': 'No programs data found in JSON'}, status=400)
        
        user_profile = request.user.userprofile
        
        created_count = 0
        updated_count = 0
        
        for prog in programs_data:
            external_id = prog.get('id')
            if not external_id:
                continue
            
            name = prog.get('name', 'Unknown Program')
            
            obj, created = Program.objects.update_or_create(
                user=user_profile,
                external_id=external_id,
                defaults={
                    'name': name,
                    'data': prog
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return JsonResponse({
            'status': 'success',
            'message': f'Stored/Updated {len(programs_data)} programs (created: {created_count}, updated: {updated_count})'
        })
    
    except FileNotFoundError:
        return JsonResponse({'status': 'error', 'message': 'JSON file not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)




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