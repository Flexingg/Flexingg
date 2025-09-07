import logging
logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, TemplateView, View, DetailView
from django.utils import timezone
from datetime import date, timedelta
from .forms import SignUpForm, LoginForm, ProfileForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views import View
from .models import Garmin_Auth, GarminDailySteps, GarminActivity, SweatScoreWeights, UserProfile, Friendship
from django.views.generic import TemplateView, ListView, View
from .models import *
# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import html



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


class SyncGarminView(TemplateView):   # Create this template later if needed 
    template_name = 'core/garmin_sync.html'  # Create this template later if needed 
    def get_context_data(self, **kwargs): 
        context = super().get_context_data(**kwargs) 
        # Stub context for Garmin sync page
        context['message'] = 'Garmin Sync Page' 
        return context


class BackgroundGarminSyncView(View): 
    def post(self, request): 
        # Stub for background sync
        if request.user.is_authenticated: 
            # Dummy sync logic 
            return JsonResponse({'success': True, 'steps_synced': 0, 'activities_synced': 0}) 
        return JsonResponse({'error': 'Authentication required'}, status=401)


class StepsChartDataView(View): 
    def get(self, request): 
        # Stub for steps chart data
        if request.user.is_authenticated: 
            # Dummy data 
            data = {
                'user_data': [{'date': '2024-09-01', 'steps': 10000}, {'date': '2024-09-02', 'steps': 12000},            # Add more dummy data
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


def get_calories_chart_data(request):  
    logger.info(f"Calories chart data access - User authenticated: {request.user.is_authenticated}, Type: {type(request.user)}")
    """API endpoint for calories chart data with friends' data and podium rankings"""
    
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
    user_data = [] ###################################################
    current_date = start_date
    while current_date <= end_date:    ## Cannot use a comprehension 
        date_key = current_date.isoformat()  ### here as below
        daily_calories = user_calories_by_date.get(date_key, 0)
        cumulative_calories += daily_calories
        user_data.append({'date': date_key, 'calories': cumulative_calories})    
        current_date += timedelta(days=1)
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
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True) #

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)
    friends_data = []
    all_users_calories = []

def get_steps_chart_data(request):
    """API endpoint for steps chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

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
        if friend_data['data']:
            # Get the last (most recent) cumulative value
            final_value = friend_data['data'][-1]['steps']
            friends_totals.append(final_value)
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
        'sentence': 'relate_steps(int(user_total_steps))' if user_total_steps > 0 else "No steps taken yet!"
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
    })


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
        return JsonResponse({'error': 'Authentication required'}, status=401)

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
    weights_dict = {weight.zone: weight.weight for weight in weights} # Don't assume tiers are 0-5


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
    all_users_scores = []  # For podium ranking

    # Add user's total for ranking
    user_total_score = sum(calculate_sweat_score(activity, weights_dict) for activity in user_activities)
    if user_total_score > 0:
        all_users_scores.append({'user_id': request.user.id, 'name': request.user.username, 'score': user_total_score})


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
                all_users_scores.append({'user_id': friend.id, 'name': friend.username, 'score': friend_total})

        except User.DoesNotExist:
            continue


    # Calculate podium rankings
    all_users_scores.sort(key=lambda x: x['score'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_scores[:3]): 
        podium_data.append({'name': user_info['name'], 'score': int(user_info['score'])})


    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data: 
        if friend_data['data']: 
            # Get the last (most recent) cumulative value
            final_value = friend_data['data'][-1]['score'] 
            friends_totals.append(final_value)

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
    })
