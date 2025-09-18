from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import make_aware, is_aware
from .utils import HCGatewayClient
from .models import HealthConnectData
from core.models import UserProfile


@login_required
def connect_healthconnect(request):
    """
    Connect to Health Connect Gateway.
    Expects POST with hc_username and hc_password.
    Supports AJAX requests with JSON response.
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        username = request.POST.get('hc_username')
        password = request.POST.get('hc_password')
        if not username or not password:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Username and password are required.'}, status=400)
            messages.error(request, 'Username and password are required.')
            return redirect('fitness:settings')

        profile = request.user
        client = HCGatewayClient()
        try:
            result = client.login(username, password)
            # Save to profile
            profile.hc_username = username
            profile.hc_password = password  # Store plain for now; consider hashing if needed
            profile.hc_token = result['token']
            profile.hc_refresh_token = result['refresh']
            expiry_str = result['expiry'].replace('Z', '+00:00')
            expiry = timezone.datetime.fromisoformat(expiry_str)
            if not is_aware(expiry):
                expiry = make_aware(expiry)
            profile.hc_token_expiry = expiry
            profile.hc_last_sync = None  # Reset last sync on new connection
            profile.save()
            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Successfully connected to Health Connect.'})
            messages.success(request, 'Successfully connected to Health Connect.')
        except Exception as e:
            error_msg = f'Connection failed: {str(e)}'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            messages.error(request, error_msg)
            client.revoke()  # Clean up if partial
        if not is_ajax:
            return redirect('fitness:settings')
    if is_ajax:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    return render(request, 'healthconnect/connect.html')  # Or redirect if GET


@login_required
@require_http_methods(["GET", "POST"])
@csrf_exempt
def sync_healthconnect(request):
    """
    Sync health data from HCGateway.
    GET/POST: Trigger sync and return JSON status.
    """
    profile = request.user
    if not profile.hc_username:
        return JsonResponse({'error': 'Not connected to Health Connect.'}, status=400)

    client = HCGatewayClient()
    # Restore tokens if present
    if profile.hc_token:
        client.token = profile.hc_token
        client.refresh_token = profile.hc_refresh_token
        client.expiry = profile.hc_token_expiry

    try:
        client._ensure_auth()  # Will login or refresh
        # Fetch recent data (last 7 days for example)
        data = client.fetch_recent(hours=168)  # 7 days
        saved_count = 0
        for method, records in data.items():
            for record in records:
                # Extract key fields; assume record has _id, start, end, etc.
                record_id = record.get('_id', str(timezone.now()))
                start_time_str = record.get('start', '').replace('Z', '+00:00')
                start_time = timezone.datetime.fromisoformat(start_time_str)
                end_time_str = record.get('end', '').replace('Z', '+00:00') if record.get('end') else None
                end_time = timezone.datetime.fromisoformat(end_time_str) if end_time_str else None
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
        # Update tokens in profile
        profile.hc_token = client.token
        profile.hc_refresh_token = client.refresh_token
        if client.expiry and not is_aware(client.expiry):
            client.expiry = make_aware(client.expiry)
        profile.hc_token_expiry = client.expiry
        profile.hc_last_sync = timezone.now()
        profile.save(update_fields=['hc_token', 'hc_refresh_token', 'hc_token_expiry', 'hc_last_sync'])
        return JsonResponse({'success': True, 'saved': saved_count, 'message': 'Sync completed.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def disconnect_healthconnect(request):
    """
    Disconnect from Health Connect Gateway.
    Supports AJAX requests with JSON response.
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    profile = request.user
    if profile.hc_username:
        client = HCGatewayClient()
        if profile.hc_token:
            client.token = profile.hc_token
            client.refresh_token = profile.hc_refresh_token
            client.expiry = profile.hc_token_expiry
            try:
                client.revoke()
            except:
                pass  # Ignore revoke errors
        # Clear fields
        profile.hc_username = None
        profile.hc_password = None
        profile.hc_token = None
        profile.hc_refresh_token = None
        profile.hc_token_expiry = None
        profile.hc_last_sync = None
        profile.save()
        # Optionally delete local data
        # profile.health_data.all().delete()
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': 'Disconnected from Health Connect.'})
        messages.success(request, 'Disconnected from Health Connect.')
    else:
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'Not connected to Health Connect.'}, status=400)
    if not is_ajax:
        return redirect('fitness:settings')
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=405)


# Placeholder for render views if needed
def healthconnect_dashboard(request):
    return render(request, 'healthconnect/dashboard.html')