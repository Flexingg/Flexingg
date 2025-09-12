from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .models import Garmin_Auth, GarminDailySteps, GarminActivity
from core.models import UserProfile
from core.forms import ProfileForm
from .forms import GarminConnectForm
import garth
from garth.sso import exchange
from garth.exc import GarthException, GarthHTTPError
import logging

logger = logging.getLogger(__name__)

def ensure_valid_tokens(garmin_auth):
    """
    Ensure Garmin tokens are valid by refreshing if expired.
    Returns True if successful, False otherwise.
    """
    if not garmin_auth.expired():
        return True

    logger.info(f"Tokens expired for user {garmin_auth.user.id}, refreshing...")
    try:
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }

        # Create token objects
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)

        # Refresh
        oauth1_token.refresh()
        oauth2_token.refresh()

        # Update stored tokens
        garmin_auth.oauth_token = oauth1_token.oauth_token
        garmin_auth.oauth_token_secret = oauth1_token.oauth_token_secret
        garmin_auth.mfa_token = getattr(oauth1_token, 'mfa_token', None)
        garmin_auth.mfa_expiration_timestamp = getattr(oauth1_token, 'mfa_expiration_timestamp', None)
        garmin_auth.domain = getattr(oauth1_token, 'domain', None)
        garmin_auth.scope = oauth2_token.scope
        garmin_auth.jti = oauth2_token.jti
        garmin_auth.token_type = oauth2_token.token_type
        garmin_auth.access_token = oauth2_token.access_token
        garmin_auth.refresh_token = oauth2_token.refresh_token
        garmin_auth.expires_in = oauth2_token.expires_in
        garmin_auth.expires_at = oauth2_token.expires_at
        garmin_auth.refresh_token_expires_in = getattr(oauth2_token, 'refresh_token_expires_in', None)
        garmin_auth.refresh_token_expires_at = getattr(oauth2_token, 'refresh_token_expires_at', None)
        garmin_auth.save()
        logger.info("Token refresh successful")
        return True
    except Exception as refresh_err:
        logger.error(f"Token refresh failed for user {garmin_auth.user.id}: {refresh_err}")
        return False

def perform_garmin_sync_steps(user, start_date, end_date):
    """
    Sync daily steps from Garmin for the given date range.
    Returns dict with success status and synced count.
    """
    try:
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except Garmin_Auth.DoesNotExist:
        return {'success': False, 'error': 'No Garmin auth record found'}

    steps_synced = 0

    try:
        # Ensure tokens are valid
        if not ensure_valid_tokens(garmin_auth):
            return {'success': False, 'error': 'Token refresh failed'}

        # Configure client with tokens
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

        # Sync steps for each day in range
        current_date = start_date
        while current_date <= end_date:
            try:
                if current_date > timezone.now().date():
                    current_date += timedelta(days=1)
                    continue

                # Fetch daily steps
                url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                try:
                    daily_steps_data = garth.client.connectapi(url)
                except Exception as api_err:
                    logger.warning(f"Steps API failed for {current_date}: {api_err}")
                    # Try alternative endpoint
                    alt_url = f"/usersummary-service/usersummary/daily/{current_date.isoformat()}"
                    daily_steps_data = garth.client.connectapi(alt_url)

                if daily_steps_data and len(daily_steps_data) > 0:
                    steps = daily_steps_data[0].get('totalSteps', 0)
                    if steps is not None:
                        obj, created = GarminDailySteps.objects.update_or_create(
                            user=user,
                            date=current_date,
                            defaults={'steps': steps}
                        )
                        if created: steps_synced += 1

                        # Also update DailySteps for general persistence
                        distance_miles = (steps * 2.2) / 5280.0  # 2.2 ft per step, 5280 ft per mile
                        daily_obj, daily_created = DailySteps.objects.update_or_create(
                            user=user,
                            calendar_date=current_date,
                            defaults={
                                'total_steps': steps,
                                'total_distance': distance_miles
                            }
                        )
                        if daily_created: steps_synced += 1  # Count for overall sync

            except Exception as step_err:
                logger.error(f"Error syncing steps for {current_date} for user {user.id}: {step_err}")

            current_date += timedelta(days=1)  # Update last_sync
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'steps_synced': steps_synced}

    except Exception as e:
        logger.error(f"Unexpected error during steps sync for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}

def perform_garmin_sync_activities(user, limit=500, start_date=None, end_date=None):
    """
    Sync recent Garmin activities for the user, optionally filtered by date range.
    Returns dict with success status and synced count.
    """
    try:
        garmin_auth = Garmin_Auth.objects.get(user=user)
    except Garmin_Auth.DoesNotExist:
        return {'success': False, 'error': 'No Garmin auth record found'}

    activities_synced = 0

    try:
        # Ensure tokens are valid
        if not ensure_valid_tokens(garmin_auth):
            return {'success': False, 'error': 'Token refresh failed'}

        # Configure client with tokens (same as steps)
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

        # Build URL with date filter if provided
        url = f"/activitylist-service/activities/search/activities?start=0&limit={limit}"
        if start_date and end_date:
            from_str = f"{start_date.isoformat()}T00:00:00"
            to_str = f"{end_date.isoformat()}T23:59:59"
            url += f"&startDateLocalFrom={from_str}&startDateLocalTo={to_str}"
        # Fetch activities
        activities = garth.client.connectapi(url)

        if not activities:
            logger.info(f"No activities found for user {user.id}")
            return {'success': True, 'activities_synced': 0}

        # Process each activity
        for activity in activities:
            try:
                activity_id = activity.get('activityId')
                if not activity_id:
                    logger.warning(f"Skipping activity with missing ID for user {user.id}: {activity}")
                    continue

                start_ts_gmt = activity.get('startTimeGMT')
                start_time_utc = None
                if start_ts_gmt:
                    try:
                        if isinstance(start_ts_gmt, str):
                            if ' ' in start_ts_gmt and '-' in start_ts_gmt:
                                # Parse datetime string
                                start_time_utc = datetime.strptime(start_ts_gmt, '%Y-%m-%d %H:%M:%S')
                                start_time_utc = start_time_utc.replace(tzinfo=dt_timezone.utc)
                            else:
                                # Unix timestamp string to float
                                start_ts_gmt = float(start_ts_gmt)
                                start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                        elif isinstance(start_ts_gmt, (int, float)):
                            # Unix timestamp in milliseconds
                            start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                        else:
                            logger.warning(f"Unexpected start time type for activity {activity_id}: {type(start_ts_gmt)}")
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid start time format for activity {activity_id}: {start_ts_gmt} - {e}")
                        continue
                else:
                    logger.warning(f"Missing start time for activity {activity_id} for user {user.id}")
                    continue

                defaults = {
                    'name': activity.get('activityName', 'Unnamed Activity'),
                    'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
                    'start_time_utc': start_time_utc,
                    'duration_seconds': activity.get('duration'),
                    'distance_meters': activity.get('distance'),
                    'calories': activity.get('calories'),
                    'average_hr': activity.get('averageHR'),
                    'max_hr': activity.get('maxHR'),
                    'raw_data': activity
                }
                # Filter None values
                defaults = {k: v for k, v in defaults.items() if v is not None}

                obj, created = GarminActivity.objects.update_or_create(
                    user=user,
                    activity_id=activity_id,
                    defaults=defaults
                )
                if created: activities_synced += 1

                # Integrate CardioCoin rewards
                if obj.calories and obj.calories > 0:
                    from ..core.models import Transaction
                    if not Transaction.objects.filter(
                        user=user,
                        currency_type='cardio_coins',
                        garmin_activity=obj
                    ).exists():
                        join_month_start = user.date_joined.replace(day=1).date()
                        one_week_after = (user.date_joined + timedelta(weeks=1)).date()
                        activity_date = obj.start_time_utc.date()
                        if join_month_start <= activity_date <= one_week_after:
                            user.earn_cardio_coins(Decimal(str(obj.calories)), garmin_activity=obj)

            except Exception as act_err:
                logger.error(f"Error processing activity {activity.get('activityId', 'N/A')} for user {user.id}: {act_err}")

        # Update last sync
        garmin_auth.last_sync = timezone.now()
        garmin_auth.save(update_fields=['last_sync'])

        return {'success': True, 'activities_synced': activities_synced}

    except Exception as e:
        logger.error(f"Unexpected error during activities sync for user {user.id}: {e}")
        return {'success': False, 'error': str(e)}

class ConnectGarminView(View):
    template_name = 'settings.html'

    def get(self, request):
        form = GarminConnectForm()
        context = {'form': ProfileForm(instance=request.user), 'profile': request.user, 'garmin_form': form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = GarminConnectForm(request.POST)
        if form.is_valid():
            garmin_email = form.cleaned_data['garmin_email']
            garmin_password = form.cleaned_data['garmin_password']

            try:
                # Clear any existing Garmin auth for this user first
                existing_auth = Garmin_Auth.objects.filter(user=request.user)
                if existing_auth.exists():
                    existing_auth.delete()
                # Use Garth SSO login
                garth.login(garmin_email, garmin_password)

                # Get the OAuth tokens from Garth
                oauth1_token = garth.client.oauth1_token
                oauth2_token = garth.client.oauth2_token

                if not oauth1_token or not oauth2_token:
                    raise ValueError("Failed to obtain OAuth tokens from Garth")

                # Extract OAuth1 data
                oauth1_data = {
                    'oauth_token': oauth1_token.oauth_token,
                    'oauth_token_secret': oauth1_token.oauth_token_secret,
                }
                # Add other OAuth1 attributes if available
                for attr in ['mfa_token', 'mfa_expiration_timestamp', 'domain']:
                    if hasattr(oauth1_token, attr):
                        oauth1_data[attr] = getattr(oauth1_token, attr)
                # Extract OAuth2 data
                oauth2_data = {}
                for attr in ['scope', 'jti', 'token_type', 'access_token', 'refresh_token',
                            'expires_in', 'expires_at', 'refresh_token_expires_in', 'refresh_token_expires_at']:
                    if hasattr(oauth2_token, attr):
                        oauth2_data[attr] = getattr(oauth2_token, attr)
                
                # Combine data for Garmin_Auth
                garmin_auth_data = {
                    'user': request.user,
                    'garmin_email': garmin_email,
                    **oauth1_data,
                    **oauth2_data
                }

                # Create Garmin_Auth record
                garmin_auth = Garmin_Auth.objects.create(**garmin_auth_data)
                
                messages.success(request, f'Garmin account ({garmin_email}) linked successfully!')
                return redirect('fitness:settings')

            except (GarthException, GarthHTTPError) as e:
                logger.warning(f"Garmin authentication failed for user {request.user.id} with email {garmin_email}: {e}")
                error_str = str(e).lower()
                if "invalid" in error_str or "credentials" in error_str:
                    messages.error(request, "Garmin login failed: Incorrect email or password.")
                elif "mfa" in error_str or "multi-factor" in error_str or "2fa" in error_str:
                    messages.error(request, "Multi-Factor Authentication (MFA) may be required. Please check your Garmin account settings.")
                else:
                    messages.error(request, f"Garmin login failed: {str(e)[:100]}...")
            except Exception as e:
                logger.error(f"Unexpected error during Garmin login for user {request.user.id}: {e}", exc_info=True)
                messages.error(request, f"Garmin login failed: {str(e)[:100]}... Please try again or contact support if the issue persists.")
        else:
            context = {'form': ProfileForm(instance=request.user), 'profile': request.user, 'garmin_form': form}
            return render(request, self.template_name, context)
        
        context = {'form': ProfileForm(instance=request.user), 'profile': request.user, 'garmin_form': form}
        return render(request, self.template_name, context)

class DisconnectGarminView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
        
        garmin_auth = Garmin_Auth.objects.filter(user=request.user).first()
        if garmin_auth:
            garmin_auth.delete()
            messages.success(request, 'Garmin Connect disconnected successfully!')
        
        return redirect('fitness:settings')

class SyncGarminView(LoginRequiredMixin, View):
    """
    View to trigger manual Garmin data sync (to be updated for async).
    Handles POST requests to sync steps and activities.
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')

        try:
            garmin_auth = Garmin_Auth.objects.get(user=request.user)
        except Garmin_Auth.DoesNotExist:
            messages.error(request, "Garmin account not linked. Please link your account first.")
            return redirect('fitness:settings')

        # Determine sync range from POST data, but limit to last 30 days for manual sync to prevent timeout
        date_range = request.POST.get('date_range', 'current_month')
        end_date = timezone.localtime().date()
        max_days = 30  # Limit for manual sync
        start_date = end_date.replace(day=1)
        activity_limit = 500

        # Sync steps
        steps_result = perform_garmin_sync_steps(request.user, start_date, end_date)
        steps_synced = steps_result.get('steps_synced', 0) if steps_result.get('success') else 0

        # Sync activities
        activities_result = perform_garmin_sync_activities(request.user, activity_limit)
        activities_synced = activities_result.get('activities_synced', 0) if activities_result.get('success') else 0

        if steps_result.get('success') and activities_result.get('success'):
            messages.success(request, f"Sync complete! Synced {steps_synced} step records and {activities_synced} activities for the last 30 days.")
        else:
            error_msg = []
            if not steps_result.get('success'):
                error_msg.append(f"Steps sync failed: {steps_result.get('error', 'Unknown error')}")
            if not activities_result.get('success'):
                error_msg.append(f"Activities sync failed: {activities_result.get('error', 'Unknown error')}")
            messages.error(request, "Sync failed. Errors: " + "; ".join(error_msg))

        return redirect('fitness:settings')

    def get(self, request, *args, **kwargs):
        # For GET, perhaps render a sync status or redirect
        messages.info(request, "Use the sync button to trigger data synchronization.")
        return redirect('fitness:settings')

class BackgroundGarminSyncView(LoginRequiredMixin, View):
    """
    API endpoint for background Garmin sync with cooldown check (to be updated for async).
    Returns JSON with sync results or skipped status.
    """

    def post(self, request, *args, **kwargs):
        try:
            garmin_auth = Garmin_Auth.objects.get(user=request.user)
        except Garmin_Auth.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Garmin account not linked'
            }, status=400)

        # Check cooldown (10 minutes = 600 seconds)
        now = timezone.now()
        last_attempt = garmin_auth.last_sync_attempt
        if last_attempt and (now - last_attempt).total_seconds() < 600:
            next_attempt = (last_attempt + timedelta(minutes=10)).isoformat()
            return JsonResponse({
                'success': False,
                'skipped': True,
                'reason': 'Sync attempted too recently',
                'next_attempt': next_attempt
            })

        # Update last attempt immediately
        garmin_auth.last_sync_attempt = now
        garmin_auth.save(update_fields=['last_sync_attempt'])

        logger.info(f"Background Garmin sync triggered for user {request.user.id} at {now}")

        # Default range for background sync: current month
        end_date = timezone.localtime().date()
        start_date = end_date.replace(day=1)
        activity_limit = 500

        # Sync steps
        steps_result = perform_garmin_sync_steps(request.user, start_date, end_date)
        steps_synced = steps_result.get('steps_synced', 0) if steps_result.get('success') else 0

        # Sync activities
        activities_result = perform_garmin_sync_activities(request.user, activity_limit)
        activities_synced = activities_result.get('activities_synced', 0) if activities_result.get('success') else 0

        if steps_result.get('success') and activities_result.get('success'):
            return JsonResponse({
                'success': True,
                'steps_synced': steps_synced,
                'activities_synced': activities_synced,
                'message': f'Synced {steps_synced} steps and {activities_synced} activities'
            })
        else:
            error_msg = []
            if not steps_result.get('success'):
                error_msg.append(steps_result.get('error', 'Steps sync failed'))
            if not activities_result.get('success'):
                error_msg.append(activities_result.get('error', 'Activities sync failed'))
            return JsonResponse({
                'success': False,
                'error': '; '.join(error_msg)
            }, status=500)