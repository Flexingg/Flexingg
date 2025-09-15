from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .utils import HCGatewayClient
from .models import HealthConnectData
from core.models import UserProfile
from datetime import timedelta
from django.utils import timezone


@login_required
@require_http_methods(["POST"])
def connect_healthconnect(request):
    username = request.POST.get('hc_username')
    password = request.POST.get('hc_password')
    if not username or not password:
        return JsonResponse({'status': 'error', 'message': 'Username and password required.'}, status=400)

    profile = request.user
    client = HCGatewayClient()

    try:
        # Login
        tokens = client.login(username, password)
        
        # Store in profile
        profile.hc_username = username
        profile.hc_password = password  # Note: Store hashed/encrypted in production
        profile.hc_token = client.token
        profile.hc_refresh_token = client.refresh_token
        profile.hc_token_expiry = client.expiry
        profile.save()

        # Fetch historical data (last 90 days)
        historical_data = client.fetch_historical(days=90)
        
        # Store data
        stored_count = 0
        for method, records in historical_data.items():
            for record in records:
                record_id = record.get('_id')
                start_time = timezone.datetime.fromisoformat(record['start'].replace('Z', '+00:00'))
                end_time = timezone.datetime.fromisoformat(record['end'].replace('Z', '+00:00')) if record.get('end') else None
                data_obj = record.get('data', {})
                app_source = record.get('app', '')

                # Dedupe: get or create
                obj, created = HealthConnectData.objects.get_or_create(
                    profile=profile,
                    method=method,
                    record_id=record_id,
                    defaults={
                        'start_time': start_time,
                        'end_time': end_time,
                        'data': data_obj,
                        'app_source': app_source,
                    }
                )
                if created:
                    stored_count += 1

        messages.success(request, f'Connected and synced {stored_count} records.')
        return JsonResponse({
            'status': 'success',
            'message': f'Connected and synced {stored_count} records.',
            'stored_count': stored_count
        })

    except Exception as e:
        messages.error(request, str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def sync_healthconnect(request):
    profile = request.user
    if not profile.hc_token:
        return JsonResponse({'status': 'error', 'message': 'Not connected to Health Connect.'}, status=400)

    client = HCGatewayClient()
    client.token = profile.hc_token
    client.refresh_token = profile.hc_refresh_token
    client.expiry = profile.hc_token_expiry

    try:
        # Ensure authentication
        client._ensure_auth()

        # Update profile with new tokens if refreshed
        if client.expiry != profile.hc_token_expiry:
            profile.hc_token = client.token
            profile.hc_refresh_token = client.refresh_token
            profile.hc_token_expiry = client.expiry
            profile.save()

        # Fetch recent data (last 24 hours)
        recent_data = client.fetch_recent(hours=24)
        
        # Store or update data
        stored_count = 0
        updated_count = 0
        for method, records in recent_data.items():
            for record in records:
                record_id = record.get('_id')
                start_time = timezone.datetime.fromisoformat(record['start'].replace('Z', '+00:00'))
                end_time = timezone.datetime.fromisoformat(record['end'].replace('Z', '+00:00')) if record.get('end') else None
                data_obj = record.get('data', {})
                app_source = record.get('app', '')

                # Update or create
                obj, created = HealthConnectData.objects.update_or_create(
                    profile=profile,
                    method=method,
                    record_id=record_id,
                    defaults={
                        'start_time': start_time,
                        'end_time': end_time,
                        'data': data_obj,
                        'app_source': app_source,
                    }
                )
                if created:
                    stored_count += 1
                else:
                    updated_count += 1

        messages.success(request, f'Synced data: {stored_count} new, {updated_count} updated records.')
        return JsonResponse({
            'status': 'success',
            'message': f'Synced data: {stored_count} new, {updated_count} updated records.',
            'new_records': stored_count,
            'updated_records': updated_count
        })

    except Exception as e:
        messages.error(request, str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def disconnect_healthconnect(request):
    profile = request.user
    if not profile.hc_token:
        return JsonResponse({'status': 'error', 'message': 'Not connected to Health Connect.'}, status=400)

    client = HCGatewayClient()
    client.token = profile.hc_token

    try:
        client.revoke()

        # Clear profile fields
        profile.hc_username = ''
        profile.hc_password = ''
        profile.hc_token = ''
        profile.hc_refresh_token = ''
        profile.hc_token_expiry = None
        profile.save()

        # Optionally delete stored data (commented for now to keep history)
        # HealthConnectData.objects.filter(profile=profile).delete()

        messages.success(request, 'Health Connect disconnected successfully.')
        return JsonResponse({'status': 'success', 'message': 'Disconnected successfully.'})

    except Exception as e:
        messages.error(request, str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)