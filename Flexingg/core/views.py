import logging
from django.contrib import messages
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, TemplateView, View, DetailView
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from datetime import date, timedelta, datetime, timezone as dt_timezone
from .forms import SignUpForm, LoginForm, ProfileForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views import View
from .models import SweatScoreWeights, UserProfile, Friendship
from django.contrib import messages
from garminconnect.models import Garmin_Auth, GarminDailySteps, GarminActivity
from liftosaur.models import Workout
from .models import *  # JWT, Notification, Relationship
from healthconnect.utils import get_daily_consumed_calories
from healthconnect.tasks import healthconnect_sync_task
from django.contrib.staticfiles.finders import find
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import html
from decimal import Decimal
import random
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
import os
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

            # Garmin sync debounce logic (updated for async)
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
                    # Trigger async sync
                    local_tz = get_current_timezone()
                    last_sync_local = garmin_auth.last_sync.astimezone(local_tz) if garmin_auth.last_sync else None
                    local_today = timezone.localtime().date()
                    steps_start = last_sync_local.date() + timedelta(days=1) if last_sync_local else local_today - timedelta(days=30)
                    activities_start = last_sync_local.date() if last_sync_local else local_today - timedelta(days=30)
                    from garminconnect.tasks import garmin_sync_steps_task, garmin_sync_activities_task
                    garmin_sync_steps_task.delay(profile.id, start_date=steps_start, end_date=local_today)
                    garmin_sync_activities_task.delay(profile.id, limit=500, start_date=activities_start, end_date=local_today)
                    context['garmin_sync_triggered'] = True
        
                    # Set user for sync progress indicator
                    context['sync_user_id'] = profile.id

                    # Health Connect sync debounce logic
                    if profile.hc_username:
                        debounce_minutes = getattr(profile, 'sync_debounce_minutes', 60)
                        threshold = timezone.now() - timedelta(minutes=debounce_minutes)
                        if profile.hc_last_sync is None or profile.hc_last_sync < threshold:
                            # Trigger async sync
                            healthconnect_sync_task.delay(profile.id)
                            context['hc_sync_triggered'] = True
                            logger.info(f"Triggered Health Connect sync for profile {profile.id}")
        
            # Calculate today's total calories from the current user's Garmin activities
            today = timezone.localtime().date()
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

            # Calculate today's lifting volume
            total_volume = 0
            workouts = Workout.objects.filter(user=self.request.user, timestamp__date=today)
            for workout in workouts:
                for exercise in workout.exercises.all():
                    total_volume += exercise.get_volume(unit='lb')
            todays_lifting_volume_k = round(total_volume / 1000) if total_volume > 0 else 0
            context['todays_lifting_volume_k'] = todays_lifting_volume_k

            # Calculate today's consumed calories from Health Connect nutrition
            todays_consumed_calories = get_daily_consumed_calories(profile)
            context['todays_consumed_calories'] = todays_consumed_calories

        else:
            context['todays_total_calories'] = 0
            context['todays_steps'] = 0
            context['todays_lifting_volume_k'] = 0
            context['todays_consumed_calories'] = 0

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
        context['user'] = self.request.user
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