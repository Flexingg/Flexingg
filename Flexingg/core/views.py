import garth
from garth.sso import exchange
from garth.exc import GarthException, GarthHTTPError
import logging
import uuid
import time
from django.contrib import messages
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, TemplateView, View, DetailView
from django.utils import timezone
from datetime import date, timedelta, datetime, timezone as dt_timezone
from .forms import SignUpForm, LoginForm, ProfileForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, StreamingHttpResponse, FileResponse
from django.views import View
from .models import Garmin_Auth, GarminDailySteps, GarminActivity, SweatScoreWeights, UserProfile, Friendship
from .models import *  # JWT, Notification, Relationship
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import html
from .forms import GarminConnectForm
from .models import Garmin_Auth, UserProfile
from decimal import Decimal
import random
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
import os
logging.basicConfig(level=logging.INFO)
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
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)
        exchange(oauth1_token, client=garth.client)

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


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            profile = self.request.user
            context['profile'] = profile
            context['total_gems'] = profile.gym_gems
            context['total_coins'] = profile.cardio_coins
            context['level'] = profile.level

            # Garmin sync debounce logic
            garmin_auth = None
            try:
                garmin_auth = Garmin_Auth.objects.get(user=profile)
                context['garmin_auth'] = garmin_auth
            except Garmin_Auth.DoesNotExist:
                pass  # No auth, skip sync

            if garmin_auth:
                debounce_minutes = getattr(profile, 'sync_debounce_minutes', 60)
                threshold = timezone.now() - timedelta(minutes=debounce_minutes)
                if garmin_auth.last_sync is None or garmin_auth.last_sync < threshold:
                    # Ensure tokens are valid before syncing
                    if not ensure_valid_tokens(garmin_auth):
                        logger.error(f"Failed to refresh tokens for user {profile.id}, skipping sync")
                        context['garmin_sync_failed'] = True
                    else:
                        # Now sync
                        now = timezone.now()
                        calculated_start = garmin_auth.last_sync.date() + timedelta(days=1) if garmin_auth.last_sync else now.date() - timedelta(days=30)
                        start_date = min(calculated_start, now.date())
                        end_date = now.date() + timedelta(days=1)

                        # Sync steps
                        steps_result = perform_garmin_sync_steps(profile, start_date, end_date)

                        # Sync activities
                        activities_result = perform_garmin_sync_activities(profile, limit=500, start_date=start_date, end_date=end_date)

                        # Update last_sync if at least one succeeded
                        if steps_result.get('success') or activities_result.get('success'):
                            garmin_auth.last_sync = now
                            garmin_auth.save(update_fields=['last_sync'])
                            context['garmin_sync_triggered'] = True
                            logger.info(f"Garmin sync triggered for user {profile.id}: steps {steps_result.get('steps_synced', 0)}, activities {activities_result.get('activities_synced', 0)}")
                        else:
                            logger.error(f"Garmin sync failed for user {profile.id}: steps {steps_result.get('error')}, activities {activities_result.get('error')}")
                            context['garmin_sync_failed'] = True

                    # Set user for sync progress indicator
                    context['sync_user_id'] = profile.id

            # Calculate today's total calories from the current user's Garmin activities
            today = timezone.now().date()
            todays_calories = GarminActivity.objects.filter(
                user=self.request.user,
                start_time_utc__date=today
            ).aggregate(total=Sum('calories'))['total'] or 0
            context['todays_total_calories'] = todays_calories

            todays_steps = GarminDailySteps.objects.filter(
                user=self.request.user,
                date=today
            ).aggregate(total=Sum('steps'))['total'] or 0
            context['todays_steps'] = todays_steps

            context['todays_lifting_calories'] = 0

        else:
            context['todays_total_calories'] = 0
            context['todays_steps'] = 0
            context['todays_lifting_calories'] = 0

        return context


class SignUpView(View):
    template_name = 'sign_up.html'
    form_class = SignUpForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('fitness:home')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('fitness:home')
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect('fitness:sign_in')
        return render(request, self.template_name, {'form': form})


class SignInView(View):
    template_name = 'sign_in.html'
    form_class = LoginForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('fitness:home')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('fitness:home')
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('fitness:home')
        return render(request, self.template_name, {'form': form})


class SignOutView(View):
    def get(self, request):
        logout(request)
        return redirect('fitness:sign_in')


class SyncGarminView(LoginRequiredMixin, View):
    """
    View to trigger manual Garmin data sync.
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
        end_date = timezone.now().date()
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
    API endpoint for background Garmin sync with cooldown check.
    Returns JSON with sync results or skipped status.
    """

    def post(self, request, *args, **kwargs):
        try:
            garmar_auth = Garmin_Auth.objects.get(user=request.user)
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
        end_date = now.date()
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


class StepsChartDataView(View):
    def get(self, request):
        # Stub for steps chart data
        if request.user.is_authenticated:
            # Dummy data
            data = {
                'user_data': [{'date': '2024-09-01', 'steps': 10000}, {'date': '2024-09-02', 'steps': 12000},
                # Add more dummy data
                ]
            }
            return JsonResponse(data)
        return JsonResponse({'error': 'Authentication required'}, status=401)


class SocialIndexView(TemplateView):
    template_name = 'social_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['profile'] = self.request.user
        return context


class HealthView(TemplateView):
    template_name = 'health.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['profile'] = self.request.user
        return context


class SettingsView(View):
    template_name = 'settings.html'
    form_class = ProfileForm

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
        form = self.form_class(instance=request.user)
        context = {'form': form, 'profile': request.user}
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
        form = self.form_class(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('fitness:settings')
        context = {'form': form, 'profile': request.user}
        return render(request, self.template_name, context)


# Step equivalents dictionary
step_equivalents = {
    "miles walked": 2000,  # Average steps per mile
    "kilometers walked": 1250,  # Average steps per kilometer
    "flights of stairs climbed": 20,  # Average steps per flight
    "heights of the CN Tower": 500,  # CN Tower height in steps
    "lengths of the Amazon River": 60000000,  # Amazon River length in steps
    "widths of Australia": 400000000,  # Australia width in steps
    "depths of Lake Baikal": 10000,  # Lake Baikal depth in steps
    "spans of the Brooklyn Bridge": 500,  # Brooklyn Bridge span in steps
    "lengths of a T-Rex": 150,  # T-Rex length in steps
    "heights of the Leaning Tower of Pisa": 60,  # Leaning Tower height in steps
    "widths of the English Channel": 3000000,  # English Channel width in steps
    "distances to the North Pole": 200000000,  # North Pole distance in steps
    "lengths of the Yangtze River": 60000000,  # Yangtze River length in steps
    "depths of the Grand Canyon": 2000,  # Grand Canyon depth in steps
    "spans of the Tacoma Narrows Bridge": 1000,  # Tacoma Narrows span in steps
    "heights of the Washington Monument": 170,  # Washington Monument height in steps
    "lengths of a school bus": 150,  # School bus length in steps
    "distances to the South Pole": 250000000,  # South Pole distance in steps
    "circumferences of Earth": 22500000,  # Earth's circumference in steps
    "widths of the Pacific Ocean": 15000000000,  # Pacific Ocean width in steps
    "heights of the Space Needle": 180,  # Space Needle height in steps
    "lengths of the Mississippi River": 40000000,  # Mississippi River length in steps
    "depths of the Challenger Deep": 10000,  # Challenger Deep depth in steps
    "spans of the Verrazzano Bridge": 1500,  # Verrazzano Bridge span in steps
}

def relate_steps(steps):
    """
    Relates a given step count to random items from the step_equivalents dictionary,
    ensuring the quantity is less than 100 and not rounded to 0.00.
    """
    if steps < 0:
        return "How?"
    else:
        # Filter items so the resulting quantity is less than 100 and not rounded to 0.00
        suitable_items = {
            name: equiv for name, equiv in step_equivalents.items()
            if equiv > 0 and steps / equiv < 100
        }

        if not suitable_items:
            # If no suitable items are found, pick the item with the largest equivalent value
            item_name, item_equiv = max(step_equivalents.items(), key=lambda item: item[1])
            quantity = steps / item_equiv
            return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."

        else:
            # Select items where the resulting quantity is not rounded to 0.00
            displayable_items = {
                name: equiv for name, equiv in suitable_items.items()
                if f"{steps / equiv:.2f}" != "0.00"
            }

            if not displayable_items:
                # If no displayable items are found, pick the item with the smallest equivalent value
                item_name, item_equiv = min(suitable_items.items(), key=lambda item: item[1])
                quantity = steps / item_equiv
                return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."

            else:
                item_name, item_equiv = random.choice(list(displayable_items.items()))
                quantity = steps / item_equiv
                return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."


# Energy equivalents dictionary (purely energy-based)
calorie_equivalents = {
    "energy to boil a cup of water": 10000,
    "energy in a AA battery": 2000,
    "energy to run a 100W lightbulb for 1 hour": 86000,
    "energy to run a satellite for 5 minutes": 800000
}

def relate_calories(calories):
    """
    Relates a given calorie amount to random items from the calorie_equivalents dictionary,
    ensuring the quantity is less than 100 and not rounded to 0.00.
    """
    if calories < 0:
        return "How? "
    else:
        # Filter items so the resulting quantity is less than 100 and not rounded to 0.00
        suitable_items = {
            name: cal for name, cal in calorie_equivalents.items()
            if cal > 0 and calories / cal < 100
        }

        if not suitable_items:
            # If no suitable items are found, pick the item with the largest calorie value
            item_name, item_calories = max(calorie_equivalents.items(), key=lambda item: item[1])
            quantity = calories / item_calories
            return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."

        else:
            # Select items where the resulting quantity is not rounded to 0.00
            displayable_items = {
                name: cal for name, cal in suitable_items.items()
                if f"{calories / cal:.2f}" != "0.00"
            }

            if not displayable_items:
                # If no displayable items are found, pick the item with the smallest calorie value
                item_name, item_calories = min(suitable_items.items(), key=lambda item: item[1])
                quantity = calories / item_calories
                return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."

            else:
                item_name, item_calories = random.choice(list(displayable_items.items()))
                quantity = calories / item_calories
                return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."


def get_calories_chart_data(request):
    """API endpoint for calories chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required", "status_code": 401}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get user's calories data
    user_activities = GarminActivity.objects.filter(
        user=request.user,
        start_time_utc__date__range=[start_date, end_date],
        calories__isnull=False
    ).exclude(calories=0)

    # Aggregate user calories by date
    user_calories_by_date = {}
    for activity in user_activities:
        date_key = activity.start_time_utc.date().isoformat()
        user_calories_by_date[date_key] = user_calories_by_date.get(date_key, 0) + (activity.calories or 0)

    # Make user data cumulative
    cumulative_calories = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_calories = user_calories_by_date.get(date_key, 0)
        cumulative_calories += daily_calories
        user_data.append({'date': date_key, 'calories': cumulative_calories})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)
    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)
    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)
    friends_data = []
    all_users_calories = []  # For podium ranking
    # Add user's total for ranking
    user_total_calories = sum(activity.calories or 0 for activity in user_activities)
    if user_total_calories > 0:
        all_users_calories.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'calories': user_total_calories
        })
    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_activities = GarminActivity.objects.filter(
                user=friend,
                start_time_utc__date__range=[start_date, end_date],
                calories__isnull=False
            ).exclude(calories=0)
            friend_calories_by_date = {}
            for activity in friend_activities:
                date_key = activity.start_time_utc.date().isoformat()
                friend_calories_by_date[date_key] = friend_calories_by_date.get(date_key, 0) + (activity.calories or 0)
            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_calories = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_calories = friend_calories_by_date.get(date_key, 0)
                cumulative_calories += daily_calories
                friend_data.append({'date': date_key, 'calories': cumulative_calories})
                current_date += timedelta(days=1)
            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })
            # Add to ranking (only if they have activities)
            friend_total = sum(activity.calories or 0 for activity in friend_activities)
            if friend_total > 0:
                all_users_calories.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'calories': friend_total
                })
        except User.DoesNotExist:
            continue
        # Calculate podium rankings
        if all_users_calories:
            all_users_calories.sort(key=lambda x: x['calories'], reverse=True)
            podium_data = []
            for i, user_info in enumerate(all_users_calories[:3]):
                podium_data.append({
                    'name': user_info['name'],
                    'calories': int(user_info['calories'])
                })
            # Calculate stats - get the final cumulative value for each friend
            friends_totals = []
            for friend_data in friends_data:
                if friend_data['data'] and friend_data['data'][-1]['calories']:
                    friends_totals.append(friend_data['data'][-1]['calories'])
            friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0
            # Find user's rank
            user_rank = None
            for i, user_info in enumerate(all_users_calories):
                if user_info['user_id'] == request.user.id:
                    user_rank = i + 1
                    break
            stats = {
                'user_total': int(user_total_calories),
                'friends_average': int(friends_average) if friends_average else 0,
                'user_rank': user_rank,
                'sentence': relate_calories(int(user_total_calories)) if user_total_calories > 0 else "No calories burned yet!"
            }
            return JsonResponse({
                'user_data': user_data,
                'friends_data': friends_data,
                'podium_data': podium_data,
                'stats': stats,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }, status=200)
    else:
        return JsonResponse({"error": "No friends found for the user", "status_code": 404}, status=404)


def get_steps_chart_data(request):
    """API endpoint for steps chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required", "status_code": 401}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get user's steps data from GarminDailySteps
    user_steps_records = GarminDailySteps.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('date')

    # Aggregate user steps by date
    user_steps_by_date = {}
    for record in user_steps_records:
        date_key = record.date.isoformat()
        user_steps_by_date[date_key] = record.steps

    # Make user data cumulative
    cumulative_steps = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_steps = user_steps_by_date.get(date_key, 0)
        cumulative_steps += daily_steps
        user_data.append({'date': date_key, 'steps': cumulative_steps})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)

    friends_data = []
    all_users_steps = []  # For podium ranking

    # Add user's total for ranking
    user_total_steps = sum(record.steps for record in user_steps_records)
    if user_total_steps > 0:
        all_users_steps.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'steps': user_total_steps
        })

    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_steps_records = GarminDailySteps.objects.filter(
                user=friend,
                date__range=[start_date, end_date]
            )

            friend_steps_by_date = {}
            for record in friend_steps_records:
                date_key = record.date.isoformat()
                friend_steps_by_date[date_key] = record.steps

            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_steps = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_steps = friend_steps_by_date.get(date_key, 0)
                cumulative_steps += daily_steps
                friend_data.append({'date': date_key, 'steps': cumulative_steps})
                current_date += timedelta(days=1)

            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })

            # Add to ranking (only if they have steps)
            friend_total = sum(record.steps for record in friend_steps_records)
            if friend_total > 0:
                all_users_steps.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'steps': friend_total
                })

        except User.DoesNotExist:
            continue

    # Calculate podium rankings
    all_users_steps.sort(key=lambda x: x['steps'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_steps[:3]):
        podium_data.append({
            'name': user_info['name'],
            'steps': int(user_info['steps'])
        })

    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data:
        if friend_data['data'] and friend_data['data'][-1]['steps']:
            friends_totals.append(friend_data['data'][-1]['steps'])
    friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0

    # Find user's rank
    user_rank = None
    for i, user_info in enumerate(all_users_steps):
        if user_info['user_id'] == request.user.id:
            user_rank = i + 1
            break

    stats = {
        'user_total': int(user_total_steps),
        'friends_average': int(friends_average) if friends_average else 0,
        'user_rank': user_rank,
        'sentence': relate_steps(int(user_total_steps)) if user_total_steps > 0 else "No steps taken yet!"
    }

    return JsonResponse({
        'user_data': user_data,
        'friends_data': friends_data,
        'podium_data': podium_data,
        'stats': stats,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }, status=200)


def calculate_sweat_score(activity, weights_dict):
    """
    Calculate sweat score for a single activity based on HR zones and weights.
    Returns the calculated score or fallback value.
    """
    # Try to get HR zone data from raw_data
    if activity.raw_data and 'hrTimeInZone' in activity.raw_data:
        hr_zones = activity.raw_data['hrTimeInZone']

        # Extract time in each zone (convert from seconds to minutes)
        t1 = hr_zones.get('hrTimeInZone_1', 0) / 60  # Zone 1
        t2 = hr_zones.get('hrTimeInZone_2', 0) / 60  # Zone 2
        t3 = hr_zones.get('hrTimeInZone_3', 0) / 60  # Zone 3
        t4 = hr_zones.get('hrTimeInZone_4', 0) / 60  # Zone 4
        t5 = hr_zones.get('hrTimeInZone_5', 0) / 60  # Zone 5

        # Calculate T0 (time below zone 1)
        total_duration = (activity.duration_seconds or 0) / 60  # Convert to minutes
        t0 = max(0, total_duration - (t1 + t2 + t3 + t4 + t5))

        # Calculate score using weights
        score = (
            (t0 * float(weights_dict.get(0, 1))) +
            (t1 * float(weights_dict.get(1, 2))) +
            (t2 * float(weights_dict.get(2, 3))) +
            (t3 * float(weights_dict.get(3, 5))) +
            (t4 * float(weights_dict.get(4, 8))) +
            (t5 * float(weights_dict.get(5, 12)))
        )

        return score
    else:
        # Fallback: use calories / 2
        if activity.calories:
            return activity.calories / 2
        return 0


def get_sweat_score_chart_data(request):
    """API endpoint for sweat score chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required", "status_code": 401}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get sweat score weights
    weights = SweatScoreWeights.objects.all()
    weights_dict = {weight.zone: weight.weight for weight in weights}
    weights_dict_dict = {int(k): Decimal(v) if Decimal(v).is_finite() else 0 for k, v in weights_dict.items()}  
    logger.info(f"Sweat score weights: {weights_dict_dict}")


    # Get user's activities data
    user_activities = GarminActivity.objects.filter(
        user=request.user,
        start_time_utc__date__range=[start_date, end_date]
    ).exclude(duration_seconds__isnull=True).exclude(duration_seconds=0)

    # Aggregate user sweat scores by date
    user_scores_by_date = {}
    for activity in user_activities:
        date_key = activity.start_time_utc.date().isoformat()
        score = calculate_sweat_score(activity, weights_dict)
        user_scores_by_date[date_key] = user_scores_by_date.get(date_key, 0) + score

    # Make user data cumulative
    cumulative_score = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_score = user_scores_by_date.get(date_key, 0)
        cumulative_score += daily_score
        user_data.append({'date': date_key, 'score': cumulative_score})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)

    friends_data = []
    all_users_scores = []  # For podium rankings

    # Add user's total for ranking
    user_total_score = sum(calculate_sweat_score(activity, weights_dict) for activity in user_activities)
    if user_total_score > 0:
        all_users_scores.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'score': user_total_score
        })

    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_activities = GarminActivity.objects.filter(
                user=friend,
                start_time_utc__date__range=[start_date, end_date]
            ).exclude(duration_seconds__isnull=True).exclude(duration_seconds=0)

            friend_scores_by_date = {}
            for activity in friend_activities:
                date_key = activity.start_time_utc.date().isoformat()
                score = calculate_sweat_score(activity, weights_dict)
                friend_scores_by_date[date_key] = friend_scores_by_date.get(date_key, 0) + score

            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_score = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_score = friend_scores_by_date.get(date_key, 0)
                cumulative_score += daily_score
                friend_data.append({'date': date_key, 'score': cumulative_score})
                current_date += timedelta(days=1)

            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })

            # Add to ranking (only if they have activities)
            friend_total = sum(calculate_sweat_score(activity, weights_dict) for activity in friend_activities)
            if friend_total > 0:
                all_users_scores.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'score': friend_total
                })

        except User.DoesNotExist:
            continue

    # Calculate podium rankings
    all_users_scores.sort(key=lambda x: x['score'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_scores[:3]):
        podium_data.append({
            'name': user_info['name'],
            'score': int(user_info['score'])
        })

    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data:
        if friend_data['data'] and friend_data['data'][-1]['score']:
            friends_totals.append(friend_data['data'][-1]['score'])
    friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0

    # Find user's rank
    user_rank = None
    for i, user_info in enumerate(all_users_scores):
        if user_info['user_id'] == request.user.id:
            user_rank = i + 1
            break

    stats = {
        'user_total': int(user_total_score),
        'friends_average': int(friends_average) if friends_average else 0,
        'user_rank': user_rank
    }

    return JsonResponse({
        'user_data': user_data,
        'friends_data': friends_data,
        'podium_data': podium_data,
        'stats': stats,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }, status=200)


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

            except Exception as step_err:
                logger.error(f"Error syncing steps for {current_date} for user {user.id}: {step_err}")
                # Removed invalid measure call
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
                    from .models import Transaction
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

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
            
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


from django.db.models import F, Q
from social.models import Friendship as SocialFriendship, Group
from django.shortcuts import get_object_or_404


class LeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = 'leaderboards.html'

    def get_context_data(self, **kwargs):
        metric = self.kwargs['metric']
        period = self.kwargs['period']
        scope = self.request.GET.get('scope', 'global')
        group_id = self.request.GET.get('group_id')

        # Validate metric
        valid_metrics = ['steps', 'calories', 'cardiocoins', 'gymgems']
        if metric not in valid_metrics:
            # Redirect to default or raise 404
            from django.shortcuts import redirect
            return redirect('fitness:leaderboards', metric='cardiocoins', period='all')

        # Calculate cutoff for period
        now = timezone.now()
        if period == 'all':
            cutoff = date(2000, 1, 1)
        elif period == 'week':
            cutoff = now - timedelta(days=7)
        elif period == 'month':
            cutoff = now - timedelta(days=30)
        else:
            # Invalid period, default to all
            cutoff = date(2000, 1, 1)
            period = 'all'

        # Base queryset
        users = UserProfile.objects.all()

        # Filter by scope
        if scope == 'friends':
            friendships = SocialFriendship.objects.filter(
                (Q(from_user=self.request.user) | Q(to_user=self.request.user)) &
                Q(status='accepted')
            ).values_list('from_user_id', flat=True).distinct()
            friend_ids = list(friendships) + list(
                SocialFriendship.objects.filter(
                    (Q(from_user=self.request.user) | Q(to_user=self.request.user)) &
                    Q(status='accepted')
                ).values_list('to_user_id', flat=True).distinct()
            )
            friend_ids = list(set(friend_ids))  # Remove duplicates
            if self.request.user.id in friend_ids:
                friend_ids.remove(self.request.user.id)
            users = users.filter(id__in=friend_ids)
        elif scope == 'group' and group_id:
            group = get_object_or_404(Group, id=group_id)
            # Check if user is in group
            if not group.members.filter(id=self.request.user.id).exists():
                # Redirect or error
                from django.shortcuts import redirect
                return redirect('fitness:leaderboards', metric=metric, period=period)
            users = group.members.all()

        # Annotate value based on metric
        if metric == 'steps':
            value_expr = Sum('daily_steps__total_steps', filter=Q(daily_steps__calendar_date__gte=cutoff))
            users = users.annotate(value=value_expr)
        elif metric == 'calories':
            value_expr = Sum('garmin_activities__calories', filter=Q(garmin_activities__start_time_utc__gte=cutoff))
            users = users.annotate(value=value_expr)
        elif metric == 'cardiocoins':
            users = users.annotate(value=F('cardio_coins'))
        elif metric == 'gymgems':
            users = users.annotate(value=F('gym_gems'))

        # For balances, no date filter needed
        # Filter out users with null value
        users = users.filter(value__isnull=False).order_by('-value', 'username')

        # Assign ranks
        ranked_users = []
        for i, user in enumerate(users, 1):
            user_obj = user
            user_obj.rank = i
            user_obj.metric_value = user.value
            ranked_users.append(user_obj)

        # Pagination for list starting from 4th
        from django.core.paginator import Paginator
        list_users = ranked_users[3:]
        paginator = Paginator(list_users, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        top3 = ranked_users[:3]

        context = super().get_context_data(**kwargs)
        context.update({
            'top3': top3,
            'page_obj': page_obj,
            'metric': metric,
            'period': period,
            'scope': scope,
            'group_id': group_id,
        })

        return context
