import logging
from django.contrib import messages
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, TemplateView, View, DetailView
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from datetime import date, timedelta, datetime, timezone as dt_timezone
from .forms import SignUpForm, LoginForm, ProfileForm, DataPriorityFormSet
from core.sync_service import *
from core.aggregation_service import *
from core.data_processor import *
from core.normalization import *
from core.formatters import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views import View
from .models import SweatScoreWeights, UserProfile, Friendship
from garminconnect.models import Garmin_Auth, GarminDailySteps, GarminActivity
from .models import Workout, DailySteps, Sleep, DailyWater
from .models import *  # JWT, Notification, Relationship
from healthconnect.utils import get_daily_consumed_calories
from healthconnect.sync_tasks import healthconnect_sync_task
from django.contrib.staticfiles.finders import find
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import html
from decimal import Decimal
import random
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Min
import os
from django.db import transaction
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from .currency_service import get_next_level_xp, get_level_progress_percentage

def _workout_volume_lbs(workout):
    """
    Robustly compute total workout volume in pounds.
    Tries multiple available helpers to remain compatible with different workout representations.
    Returns a float number of lbs (0 on failure).
    """
    try:
        # Prefer explicit get_total_volume if available
        if hasattr(workout, 'get_total_volume'):
            try:
                return float(workout.get_total_volume(unit='lb') or 0)
            except Exception:
                pass
        # Older helper that returns thousands (k) of lbs: get_total_volume_k()
        if hasattr(workout, 'get_total_volume_k'):
            try:
                return float(workout.get_total_volume_k() or 0) * 1000.0
            except Exception:
                pass
        # Fallback: sum unified_exercises volumes if present
        ex_qs = getattr(workout, 'unified_exercises', None)
        if ex_qs is not None:
            try:
                total = 0.0
                for ex in ex_qs.all():
                    if hasattr(ex, 'get_volume'):
                        total += float(ex.get_volume('lb') or 0)
                return total
            except Exception:
                pass
        # Final fallback: attempt to parse raw workout.data structure (entries -> sets/warmupSets)
        try:
            data = getattr(workout, 'data', None)
            if data and isinstance(data, dict):
                entries = data.get('entries', [])
                total = 0.0
                for entry in entries:
                    # regular sets
                    for set_data in entry.get('sets', []):
                        if set_data.get('isCompleted', False):
                            weight = set_data.get('completedWeight', {}).get('value') or set_data.get('completedWeight', {}).get('value', 0)
                            reps = set_data.get('completedReps', 0) or 0
                            unit = set_data.get('completedWeight', {}).get('unit') or entry.get('weightUnit') or 'lb'
                            if weight and reps:
                                try:
                                    w = float(weight)
                                except Exception:
                                    w = 0.0
                                if unit == 'kg':
                                    w *= 2.20462
                                total += w * float(reps)
                    # warmup sets
                    for warmup in entry.get('warmupSets', []):
                        if warmup.get('isCompleted', False):
                            weight = warmup.get('completedWeight', {}).get('value') or 0
                            reps = warmup.get('completedReps', 0) or 0
                            unit = warmup.get('completedWeight', {}).get('unit') or 'lb'
                            if weight and reps:
                                try:
                                    w = float(weight)
                                except Exception:
                                    w = 0.0
                                if unit == 'kg':
                                    w *= 2.20462
                                total += w * float(reps)
                if total > 0:
                    return total
        except Exception:
            pass
    except Exception:
        pass
    return 0.0



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
            # XP and dynamic level progress data
            context['xp'] = getattr(profile, 'xp', 0) or 0
            # Try to fetch the next_level_xp using Level table; fallback to simple multiplier if not present
            next_xp = get_next_level_xp(profile.level)
            if next_xp is None:
                next_xp = (profile.level or 1) * 10000
            context['next_level_xp'] = next_xp
            context['level_progress_percentage'] = get_level_progress_percentage(context['xp'], profile.level)
            recent_activities = []

            # Data sources sync debounce logic - use unified last_sync field
            debounce_minutes = getattr(profile, 'sync_debounce_minutes', 60)
            threshold = timezone.now() - timedelta(minutes=debounce_minutes)
            needs_sync = False

            # Check if we need to sync based on unified last_sync field
            if profile.last_sync is None or profile.last_sync < threshold:
                needs_sync = True

            # Also check if any services are connected (to determine if sync should be attempted)
            has_connected_services = (
                (profile.hc_username) or  # Health Connect
                (profile.liftosaur_user_id) or  # Liftosaur
                False  # Add check for Garmin if needed
            )

            # Try to get Garmin auth for context
            try:
                garmin_auth = Garmin_Auth.objects.get(user=profile)
                context['garmin_auth'] = garmin_auth
                has_connected_services = True
            except Garmin_Auth.DoesNotExist:
                pass

            if needs_sync and has_connected_services:
                sync_user_data.delay(profile.id)
                context['sync_triggered'] = True
                context['sync_user_id'] = profile.id
                logger.info(f"Triggered general sync for profile {profile.id}")
                # Show bodyweight prompt when user has no synced weight (manual entry helpful)
                context['show_bodyweight_prompt'] = True if (getattr(profile, 'weight') in [None, ''] ) else False
        
            # Calculate today's total calories from the current user's unified workouts
            today = timezone.localtime().date()
            context['todays_date'] = today.isoformat()
            todays_calories = 0
            workouts = Workout.objects.filter(user=self.request.user, start_time__date=today)
            for workout in workouts:
                if workout.source == 'garmin':
                    todays_calories += workout.data.get('calories', 0)
            context['todays_total_calories'] = todays_calories

            todays_steps = DailySteps.objects.filter(
                user=self.request.user,
                date=today
            ).aggregate(total=Sum('steps'))['total'] or 0
            context['todays_steps'] = todays_steps
            # Calculate today's water intake
            todays_water_ounces = DailyWater.objects.filter(
                user=self.request.user,
                date=today
            ).aggregate(total=Sum('amount_ounces'))['total'] or 0
            context['todays_water_ounces'] = todays_water_ounces

            # Calculate today's lifting volume using a robust helper
            total_volume = 0.0
            workouts = Workout.objects.filter(user=self.request.user, start_time__date=today)
            for workout in workouts:
                vol_lbs = _workout_volume_lbs(workout)
                # volume_k is thousands of lbs
                vol_k = vol_lbs / 1000.0
                print(f"Workout {workout.id} volume: {vol_k}k ({vol_lbs} lbs)")
                total_volume += vol_k
            context['todays_lifting_volume_k'] = total_volume



            # Calculate today's consumed calories from Health Connect nutrition
            todays_consumed_calories = get_daily_consumed_calories(profile)
            context['todays_consumed_calories'] = todays_consumed_calories
            context['todays_water_ounces'] = 0

        else:
            context['todays_total_calories'] = 0
            context['todays_steps'] = 0
            context['todays_lifting_volume_k'] = 0
            context['todays_consumed_calories'] = 0

        # Add recent sleep entries
        user = self.request.user
        recent_sleep = Sleep.objects.filter(user=user).order_by('-start_time')[:2]
        for sleep in recent_sleep:
            if sleep.end_time and sleep.start_time:
                sleep_hours = (sleep.end_time - sleep.start_time).total_seconds() / 3600
                days_ago = (timezone.now().date() - sleep.start_time.date()).days
                relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
                details = {
                    'source': sleep.source,
                    'start_time': sleep.start_time,
                    'end_time': sleep.end_time,
                    'data': sleep.data,
                }
                recent_activities.append({
                    'type': 'sleep',
                    'name': 'Sleep Session',
                    'relative_date': relative_date,
                    'time': sleep.start_time.strftime('%I:%M %p'),
                    'metric': round(sleep_hours, 1),
                    'unit': 'hrs',
                    'duration': None,
                    'xp': 0,  # Sleep doesn't give XP in this system
                    'sort_date': sleep.start_time if sleep.start_time.tzinfo else timezone.make_aware(sleep.start_time),
                    'details': details
                })

        # Add recent water intake entries
        recent_water = DailyWater.objects.filter(user=user).order_by('-date')[:2]
        for water in recent_water:
            days_ago = (timezone.now().date() - water.date).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            details = {
                'source': water.source,
                'date': water.date,
                'amount_ounces': water.amount_ounces,
                'data': water.data,
            }
            recent_activities.append({
                'type': 'water',
                'name': 'Water Intake',
                'relative_date': relative_date,
                'time': 'Daily Total',
                'metric': round(float(water.amount_ounces), 1),
                'unit': 'oz',
                'duration': None,
                'xp': 0,  # Water intake doesn't give XP
                'sort_date': timezone.make_aware(timezone.datetime.combine(water.date, timezone.datetime.min.time())),
                'details': details
            })

        # Add recent nutrition entries
        recent_nutrition = NutritionEntry.objects.filter(user=user).order_by('-datetime')[:2]
        for nutrition in recent_nutrition:
            days_ago = (timezone.now().date() - nutrition.datetime.date()).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            details = {
                'source': nutrition.source,
                'datetime': nutrition.datetime,
                'food_name': nutrition.food_name,
                'calories': nutrition.calories,
                'protein_grams': nutrition.protein_grams,
                'fat_grams': nutrition.fat_grams,
                'carbs_grams': nutrition.carbs_grams,
                'data': nutrition.data,
            }
            recent_activities.append({
                'type': 'nutrition',
                'name': nutrition.food_name,
                'relative_date': relative_date,
                'time': nutrition.datetime.strftime('%I:%M %p'),
                'metric': round(float(nutrition.calories or 0), 0),
                'unit': 'cal',
                'duration': None,
                'xp': 0,  # Nutrition doesn't give XP in this system
                'sort_date': nutrition.datetime if nutrition.datetime.tzinfo else timezone.make_aware(nutrition.datetime),
                'details': details
            })

        # Sort by date descending
        recent_activities.sort(key=lambda x: x['sort_date'], reverse=True)
        context['recent_activities'] = recent_activities[:5]

        return context


class StatsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        profile = request.user
        today = timezone.localtime().date()
        target_date_str = request.GET.get('date')
        get_earliest = request.GET.get('earliest') == 'true'

        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
                if target_date > today:
                    return JsonResponse({'error': 'Cannot view future dates'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'Invalid date format'}, status=400)
        else:
            target_date = today

        # Calculate stats for target_date
        # Calories burned
        calories = 0
        workouts = Workout.objects.filter(user=profile, start_time__date=target_date)
        for workout in workouts:
            if workout.source == 'garmin':
                calories += workout.data.get('calories', 0)

        # Steps
        steps = DailySteps.objects.filter(
            user=profile,
            date=target_date
        ).aggregate(total=Sum('steps'))['total'] or 0

        # Lifting volume
        # Calculate lifting volume robustly (sum of lbs -> convert to k)
        total_volume = 0.0
        workouts = Workout.objects.filter(user=profile, start_time__date=target_date)
        for workout in workouts:
            vol_lbs = _workout_volume_lbs(workout)
            vol_k = vol_lbs / 1000.0
            print(workout.id, vol_k)
            total_volume += vol_k
        volume_k = total_volume

        # Water intake
        water_ounces = DailyWater.objects.filter(
            user=profile,
            date=target_date
        ).aggregate(total=Sum('amount_ounces'))['total'] or 0

        # Lifting volume
        total_volume = 0
        print("Calculating lifting volume for date:", target_date)
        workouts = Workout.objects.filter(user=profile, start_time__date=target_date)
        for workout in workouts:
            print(workout.id, _workout_volume_lbs(workout) / 1000.0)
        # Lifting volume
        total_volume = 0
        print("Calculating lifting volume for date:", target_date)
        workouts = Workout.objects.filter(user=profile, start_time__date=target_date)
        for workout in workouts:
            print(workout.id, _workout_volume_lbs(workout) / 1000.0)
            
        
        
        
        
       








        # Consumed calories
        consumed = get_daily_consumed_calories(profile, target_date)

        response_data = {
            'date': target_date.isoformat(),
            'calories': int(calories),
            'steps': int(steps),
            'volume_k': volume_k,
            'consumed': consumed,
            'water_ounces': float(water_ounces)
        }
            

        if get_earliest:
            earliest_candidates = []
            # Steps earliest
            steps_min = DailySteps.objects.filter(user=profile).aggregate(min_date=Min('date'))['min_date']
            if steps_min:
                earliest_candidates.append(steps_min)
            # Workouts earliest
            workout_min = Workout.objects.filter(user=profile).aggregate(min_date=Min('start_time__date'))['min_date']
            if workout_min:
                earliest_candidates.append(workout_min)
            # Sleep earliest
            sleep_min = Sleep.objects.filter(user=profile).aggregate(min_date=Min('start_time__date'))['min_date']
            if sleep_min:
                earliest_candidates.append(sleep_min)

            if earliest_candidates:
                earliest_date = min(earliest_candidates)
                response_data['earliest_date'] = earliest_date.isoformat()
            else:
                response_data['earliest_date'] = today.isoformat()  # No data, use today

        return JsonResponse(response_data)

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


@login_required
def sync_data_view(request):
    if request.method == 'POST':
        # For manual sync triggered by the settings page, bypass automatic debounce so the user-forced sync runs immediately.
        sync_user_data.delay(request.user.id, True)
        messages.success(request, "Sync started! Your data will appear on your dashboard shortly.")
        return redirect('fitness:settings')
    # Redirect or show an error if accessed via GET
    messages.error(request, "This action can only be performed by clicking the button.")
    return redirect('fitness:settings')


@login_required
def bodyweight_submit(request):
    """
    Handle manual bodyweight submissions from the bodyweight_prompt template.
    Saves both the per-profile fallback (bodyweight_lbs) and the synced weight field.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('fitness:home')

    bw_value = request.POST.get('bodyweight_lbs')
    try:
        bw = float(bw_value)
        if bw <= 0:
            raise ValueError("Bodyweight must be positive")
    except Exception:
        messages.error(request, "Please enter a valid bodyweight value.")
        return redirect('fitness:home')

    # Save to both the user.weight (synced weight) and the fallback bodyweight_lbs
    user = request.user
    try:
        user.weight = bw
        user.bodyweight_lbs = bw
        user.save()
        messages.success(request, "Bodyweight saved.")
    except Exception:
        messages.error(request, "Failed to save bodyweight - try again.")
    return redirect('fitness:home')


class DataPriorityView(LoginRequiredMixin, View):
    template_name = 'data_priorities.html'

    def get(self, request):
        queryset = DataPriority.objects.filter(user=request.user)
        if not queryset.exists():
            # Create default priorities
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='workout',
                source='garmin',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='workout',
                source='liftosaur',
                defaults={'rank': 2}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='sleep',
                source='healthconnect',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='steps',
                source='garmin',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='steps',
                source='healthconnect',
                defaults={'rank': 2}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='water',
                source='healthconnect',
                defaults={'rank': 1}
            )
            DataPriority.objects.get_or_create(
                user=request.user,
                data_type='water',
                source='garmin',
                defaults={'rank': 2}
            )
            # Refresh queryset
            queryset = DataPriority.objects.filter(user=request.user)
        formset = DataPriorityFormSet(queryset=queryset)
        return render(request, self.template_name, {'formset': formset})

    def post(self, request):
        formset = DataPriorityFormSet(request.POST, queryset=DataPriority.objects.filter(user=request.user))
        logger.info(f"Formset validation: {formset.is_valid()}")
        if formset.is_valid():
            logger.info("Formset is valid. Processing data:")
            for form in formset:
                logger.info(f"Form cleaned_data: {form.cleaned_data}")
            from collections import defaultdict
            with transaction.atomic():
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.user = request.user
                
                groups = defaultdict(list)
                for form in formset:
                    if form.instance.pk:
                        groups[form.cleaned_data['data_type']].append((form.instance, form.cleaned_data['rank']))
                logger.info(f"Groups: {dict(groups)}")
                
                # Temporarily assign unique high ranks to avoid unique constraint violations during reassignment
                for data_type, items in groups.items():
                    for instance, _ in items:
                        instance.rank = 1000 + instance.pk
                        instance.save()
                
                # Assign sequential ranks based on submitted order per group
                for data_type, items in groups.items():
                    sorted_items = sorted(items, key=lambda x: x[1])
                    for i, (instance, _) in enumerate(sorted_items, 1):
                        instance.rank = i
                    for instance, _ in sorted_items:
                        instance.save()
                logger.info(f"After save, current priorities: {list(DataPriority.objects.filter(user=request.user).values('data_type', 'source', 'rank'))}")
            messages.success(request, 'Data priorities updated successfully!')
            return redirect('fitness:data_priorities')
        else:
            logger.error(f"Formset errors: {formset.errors}")
            logger.error(f"Formset non-form errors: {formset.non_form_errors()}")
            for form in formset:
                if form.errors:
                    logger.error(f"Form {form.instance.pk if form.instance.pk else 'new'} errors: {form.errors}")
        return render(request, self.template_name, {'formset': formset})


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
        form = self.form_class(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            avatar_file = request.FILES.get('avatar')
            if avatar_file:
                form.instance.avatar = avatar_file
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('fitness:settings')
        else:
            messages.error(request, 'Please correct the errors below.')
        context = {'form': form, 'profile': request.user}
        return render(request, self.template_name, context)


class LiftosaurConnectView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
        liftosaur_user_id = request.POST.get('liftosaur_user_id')
        if liftosaur_user_id:
            # Strip the prefix if present
            prefix = "https://www.liftosaur.com/profile/"
            if liftosaur_user_id.startswith(prefix):
                liftosaur_user_id = liftosaur_user_id[len(prefix):]
            request.user.liftosaur_user_id = liftosaur_user_id.strip()
            request.user.save()
            messages.success(request, 'Liftosaur connected successfully!')
        else:
            messages.error(request, 'Please enter your Liftosaur User ID.')
        return redirect('fitness:settings')


class LiftosaurDisconnectView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('fitness:sign_in')
        request.user.liftosaur_user_id = None
        request.user.save()
        messages.success(request, 'Liftosaur disconnected.')
        return redirect('fitness:settings')


class ComingSoonView(TemplateView):
    template_name = 'comingsoon.html'

class OfflineView(TemplateView):
    template_name = 'offline.html'

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user

        # Total calories burned
        from garminconnect.models import GarminActivity
        from django.db.models import Sum
        # Get calories from unified workouts (all sources)
        workouts = Workout.objects.filter(user=user)
        total_calories = 0
        for workout in workouts:
            if workout.data and 'calories' in workout.data:
                total_calories += workout.data['calories']

        # Also include Garmin activities for backward compatibility
        garmin_calories = GarminActivity.objects.filter(user=user).aggregate(Sum('calories'))['calories__sum'] or 0
        total_calories += garmin_calories
        context['total_calories'] = int(total_calories)

        # Total weight lifted (lbs) computed robustly
        total_weight_lifted = 0.0
        workouts = Workout.objects.filter(user=user)
        for workout in workouts:
            total_weight_lifted += _workout_volume_lbs(workout)
        context['total_weight_lifted'] = int(total_weight_lifted)

        # Developer debug: if we computed zero total but workouts exist, log per-workout diagnostics
        try:
            if total_weight_lifted == 0 and workouts.exists():
                logger.info(f"[DEBUG] User {user.username} total_weight_lifted==0; dumping per-workout diagnostics (up to 3)")
                for w in workouts[:3]:
                    try:
                        vol_get_total = None
                        if hasattr(w, 'get_total_volume'):
                            try:
                                vol_get_total = float(w.get_total_volume(unit='lb') or 0)
                            except Exception:
                                vol_get_total = None
                        vol_unified = 0.0
                        try:
                            for ex in getattr(w, 'unified_exercises', []).all():
                                if hasattr(ex, 'get_volume'):
                                    vol_unified += float(ex.get_volume('lb') or 0)
                        except Exception:
                            vol_unified = None
                        vol_fallback = _workout_volume_lbs(w)
                        # Log a compact summary (avoid dumping huge JSON)
                        logger.info(f"[DEBUG] Workout {w.id} | source={w.source} | get_total_volume={vol_get_total} | unified_sum={vol_unified} | fallback={vol_fallback} | data_keys={list(w.data.keys()) if isinstance(w.data, dict) else type(w.data)}")
                    except Exception as e:
                        logger.exception(f"[DEBUG] Error computing diagnostics for workout {w.id}: {e}")
        except Exception:
            logger.exception("Error while logging workout diagnostics")

        # Total sleep hours
        from .models import Sleep
        sleep_records = Sleep.objects.filter(user=user)
        total_sleep_seconds = 0
        for record in sleep_records:
            if record.end_time and record.start_time:
                total_sleep_seconds += (record.end_time - record.start_time).total_seconds()
        context['total_sleep_hours'] = round(total_sleep_seconds / 3600, 1) if total_sleep_seconds else 0

        # Total water intake
        from .models import DailyWater
        total_water_ounces = DailyWater.objects.filter(user=user).aggregate(Sum('amount_ounces'))['amount_ounces__sum'] or 0
        context['total_water_ounces'] = round(float(total_water_ounces), 1)

        # Total nutrition data
        from .models import NutritionEntry
        total_calories_consumed = NutritionEntry.objects.filter(user=user).aggregate(Sum('calories'))['calories__sum'] or 0
        total_protein_grams = NutritionEntry.objects.filter(user=user).aggregate(Sum('protein_grams'))['protein_grams__sum'] or 0
        context['total_calories_consumed'] = round(float(total_calories_consumed), 0)
        context['total_protein_grams'] = round(float(total_protein_grams), 1)


        # Next level XP and progress (use Level model helpers if available)
        from .currency_service import get_next_level_xp, get_level_progress_percentage
        next_xp = get_next_level_xp(user.level)
        if next_xp is None:
            next_xp = user.level * 10000
        context['next_level_xp'] = next_xp
        context['level_progress_percentage'] = get_level_progress_percentage(user.xp or 0, user.level or 1)


        # Recent activities (combine cardio and lifts, last 5)
        from .models import Transaction
        recent_activities = []

        # Cardio activities
        cardio_acts = GarminActivity.objects.filter(user=user).order_by('-start_time_utc')[:3]
        for act in cardio_acts:
            if act.distance_meters and act.activity_type in ['running', 'walking', 'hiking']:
                metric = act.distance_meters / 1609.34
                unit = 'mi'
            else:
                metric = act.calories or 0
                unit = 'cal'
            duration = act.duration_seconds / 60 if act.duration_seconds else 0
            xp_sum = Transaction.objects.filter(garmin_activity=act, currency_type='cardio_coins').aggregate(Sum('amount'))['amount__sum'] or 0
            xp = float(xp_sum) * 0.5 if xp_sum else 0
            days_ago = (timezone.now().date() - act.start_time_utc.date()).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            details = {
                'activity_type': act.activity_type,
                'start_time_utc': act.start_time_utc,
                'duration_seconds': act.duration_seconds,
                'distance_meters': act.distance_meters,
                'calories': act.calories,
                'average_hr': act.average_hr,
                'max_hr': act.max_hr,
                'synced_at': act.synced_at,
            }
            recent_activities.append({
                'type': 'cardio',
                'name': act.name or act.activity_type,
                'relative_date': relative_date,
                'time': act.start_time_utc.strftime('%I:%M %p'),
                'metric': round(metric, 1),
                'unit': unit,
                'duration': round(duration),
                'xp': round(xp, 0),
                'sort_date': act.start_time_utc if act.start_time_utc.tzinfo else timezone.make_aware(act.start_time_utc),
                'details': details
            })

        # Lifting workouts
        lift_workouts = Workout.objects.filter(user=user).order_by('-start_time')[:3]
        for workout in lift_workouts:
            # Use robust helper to compute workout total volume in lbs
            total_volume = _workout_volume_lbs(workout)
            # For XP, sum gym_gems transactions around workout start_time (approximate, last 24h)
            workout_date = workout.start_time.date()
            xp_sum = Transaction.objects.filter(
                user=user,
                currency_type='gym_gems',
                created_at__date=workout_date
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            xp = float(xp_sum) * 0.5 if xp_sum else 0
            days_ago = (timezone.now().date() - workout.start_time.date()).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            exercises_details = []
            for ex in workout.unified_exercises.all():
                sets_details = []
                for set_obj in ex.sets.all():
                    sets_details.append({
                        'reps': set_obj.reps,
                        'weight_value': set_obj.weight_value,
                        'weight_unit': set_obj.weight_unit,
                        'completed_reps': set_obj.completed_reps,
                        'completed_weight_value': set_obj.completed_weight_value,
                        'completed_weight_unit': set_obj.completed_weight_unit,
                        'rpe': set_obj.rpe,
                        'completed_rpe': set_obj.completed_rpe,
                        'is_completed': set_obj.is_completed,
                        'is_amrap': set_obj.is_amrap,
                        'is_warmup': set_obj.is_warmup,
                        'notes': set_obj.notes,
                    })
                exercises_details.append({
                    'exercise_name': ex.exercise_name,
                    'note': ex.note,
                    'timestamp': ex.timestamp,
                    'successes': ex.successes,
                    'failures': ex.failures,
                    'sets': sets_details,
                    'volume': ex.get_volume('lb') if hasattr(ex, 'get_volume') else 0,
                })
            details = {
                'source': workout.source,
                'start_time': workout.start_time,
                'end_time': workout.end_time,
                'duration_seconds': workout.duration_seconds,
                'data': workout.data,
                'exercises': exercises_details,
                'total_volume': total_volume,
            }
            recent_activities.append({
                'type': 'lift',
                'name': 'Lifting Session',
                'relative_date': relative_date,
                'time': workout.start_time.strftime('%I:%M %p'),
                'metric': int(total_volume),
                'unit': 'lbs',
                'duration': None,
                'xp': xp,
                'sort_date': workout.start_time if workout.start_time.tzinfo else timezone.make_aware(workout.start_time),
                'details': details
            })

        # Sort by date descending
        recent_activities.sort(key=lambda x: x['sort_date'], reverse=True)
        context['recent_activities'] = recent_activities[:5]

        # Add recent sleep entries
        user = self.request.user
        recent_sleep = Sleep.objects.filter(user=user).order_by('-start_time')[:2]
        for sleep in recent_sleep:
            if sleep.end_time and sleep.start_time:
                sleep_hours = (sleep.end_time - sleep.start_time).total_seconds() / 3600
                days_ago = (timezone.now().date() - sleep.start_time.date()).days
                relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
                details = {
                    'source': sleep.source,
                    'start_time': sleep.start_time,
                    'end_time': sleep.end_time,
                    'data': sleep.data,
                }
                recent_activities.append({
                    'type': 'sleep',
                    'name': 'Sleep Session',
                    'relative_date': relative_date,
                    'time': sleep.start_time.strftime('%I:%M %p'),
                    'metric': round(sleep_hours, 1),
                    'unit': 'hrs',
                    'duration': None,
                    'xp': 0,  # Sleep doesn't give XP in this system
                    'sort_date': sleep.start_time if sleep.start_time.tzinfo else timezone.make_aware(sleep.start_time),
                    'details': details
                })

        # Add recent water intake entries
        recent_water = DailyWater.objects.filter(user=user).order_by('-date')[:2]
        for water in recent_water:
            days_ago = (timezone.now().date() - water.date).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            details = {
                'source': water.source,
                'date': water.date,
                'amount_ounces': water.amount_ounces,
                'data': water.data,
            }
            recent_activities.append({
                'type': 'water',
                'name': 'Water Intake',
                'relative_date': relative_date,
                'time': 'Daily Total',
                'metric': round(float(water.amount_ounces), 1),
                'unit': 'oz',
                'duration': None,
                'xp': 0,  # Water intake doesn't give XP
                'sort_date': timezone.make_aware(timezone.datetime.combine(water.date, timezone.datetime.min.time())),
                'details': details
            })

        # Add recent nutrition entries
        recent_nutrition = NutritionEntry.objects.filter(user=user).order_by('-datetime')[:2]
        for nutrition in recent_nutrition:
            days_ago = (timezone.now().date() - nutrition.datetime.date()).days
            relative_date = 'Today' if days_ago == 0 else 'Yesterday' if days_ago == 1 else f'{days_ago} days ago'
            details = {
                'source': nutrition.source,
                'datetime': nutrition.datetime,
                'food_name': nutrition.food_name,
                'calories': nutrition.calories,
                'protein_grams': nutrition.protein_grams,
                'fat_grams': nutrition.fat_grams,
                'carbs_grams': nutrition.carbs_grams,
                'data': nutrition.data,
            }
            recent_activities.append({
                'type': 'nutrition',
                'name': nutrition.food_name,
                'relative_date': relative_date,
                'time': nutrition.datetime.strftime('%I:%M %p'),
                'metric': round(float(nutrition.calories or 0), 0),
                'unit': 'cal',
                'duration': None,
                'xp': 0,  # Nutrition doesn't give XP in this system
                'sort_date': nutrition.datetime if nutrition.datetime.tzinfo else timezone.make_aware(nutrition.datetime),
                'details': details
            })

        # Sort by date descending
        recent_activities.sort(key=lambda x: x['sort_date'], reverse=True)
        context['recent_activities'] = recent_activities[:5]

        return context


class ServiceWorkerView(View):
    def get(self, request):
        sw_path = find('app/sw.js')
        if not sw_path:
            return HttpResponse(status=404)
        
        with open(sw_path, 'r') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache'
        return response


class GymView(TemplateView):
    template_name = 'gym.html'

class LockerRoomView(TemplateView):
    template_name = 'locker_room.html'


class ShopView(TemplateView):
    template_name = 'shop.html'