from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import UserProfile
from django.urls import reverse
from django.db.models import Q
from .models import Friendship, Group, GroupMembership
from django import forms
from liftosaur.models import Workout as LWorkout, WorkoutExercise, WorkoutSet
from django.db.models import Sum, F, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from django.db.models import FloatField
from core.models import *
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import FloatField
from django.http import JsonResponse
from django.views.decorators.http import require_GET

# Constants and helper functions for cumulative API
CUMULATIVE_METRICS = {'steps', 'calories', 'lifts', 'coins', 'gems', 'consumed', 'water'}
DAILY_METRICS = {'sleep', 'bodyweight'}

def get_time_range_and_granularity(history_label):
    """
    Returns (start_date, end_date, granularity).
    Weekly/Monthly -> daily granularity; All Time (or others) -> weekly sampling (last 52 weeks).
    """
    today = timezone.now().date()
    if history_label and history_label.lower() == 'weekly':
        start = today - timedelta(days=6)
        gran = 'daily'
    elif history_label and history_label.lower() == 'monthly':
        start = today - timedelta(days=29)
        gran = 'daily'
    else:
        # All Time -> sample last 52 weeks
        start = today - timedelta(weeks=52)
        gran = 'weekly'
    return start, today, gran

def daterange(start_date, end_date):
    """
    Yield each date between start_date and end_date inclusive.
    """
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def calculate_lift_volume(user, since_date):
    """
    Calculate total volume lifted (in lbs) for the user since the given date.
    Sums completed set volumes across all exercises and workouts.
    """
    from liftosaur.models import Workout, WorkoutExercise, WorkoutSet
    total = 0.0
    workouts = user.workouts.filter(timestamp__date__gte=since_date)
    for workout in workouts:
        for exercise in workout.exercises.all():
            for set_instance in exercise.sets.all():
                if set_instance.completed_reps > 0:
                    total += set_instance.get_set_volume('lb')
    return total

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']

@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(UserProfile, id=user_id)
    if to_user == request.user:
        return redirect(reverse('core:profile', args=[user_id]))
    existing = Friendship.objects.filter(from_user=request.user, to_user=to_user).first()
    if existing:
        return redirect(reverse('core:profile', args=[user_id]))
    Friendship.objects.create(from_user=request.user, to_user=to_user)
    return redirect(reverse('core:profile', args=[user_id]))

@login_required
def accept_friend_request(request, request_id):
    friendship = get_object_or_404(Friendship, id=request_id)
    if friendship.to_user != request.user:
        return redirect('social:friend_requests')
    friendship.status = 'accepted'
    friendship.save()
    return redirect('social:friend_list')

@login_required
def decline_friend_request(request, request_id):
    friendship = get_object_or_404(Friendship, id=request_id)
    if friendship.to_user != request.user:
        return redirect('social:friend_requests')
    friendship.delete()
    return redirect('social:friend_requests')

@login_required
def remove_friend(request, user_id):
    target_user = get_object_or_404(UserProfile, id=user_id)
    if target_user == request.user:
        return redirect('social:friend_list')
    friendship1 = Friendship.objects.filter(from_user=request.user, to_user=target_user, status='accepted').first()
    friendship2 = Friendship.objects.filter(from_user=target_user, to_user=request.user, status='accepted').first()
    if friendship1:
        friendship1.delete()
    if friendship2:
        friendship2.delete()
    return redirect('social:friend_list')

@login_required
def friend_list(request):
    friendships = Friendship.objects.filter(
        Q(from_user=request.user, status='accepted') | Q(to_user=request.user, status='accepted')
    )
    friends = []
    for f in friendships:
        other = f.from_user if f.to_user == request.user else f.to_user
        friends.append(other)
    return render(request, 'friends/friend_list.html', {'friends': friends})

@login_required
def friend_requests(request):
    requests = Friendship.objects.filter(to_user=request.user, status='pending')
    return render(request, 'friends/friend_requests.html', {'requests': requests})

@login_required
def search_users(request):
    if request.method == 'POST':
        q = request.POST.get('q', '').strip()
        if not q:
            return redirect('social:friend_list')
        
        users = UserProfile.objects.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        ).exclude(id=request.user.id)
        
        exclude_ids = set()
        accepted_friendships = Friendship.objects.filter(
            Q(status='accepted', from_user=request.user) | Q(status='accepted', to_user=request.user)
        )
        for f in accepted_friendships:
            if f.from_user != request.user:
                exclude_ids.add(f.from_user.id)
            if f.to_user != request.user:
                exclude_ids.add(f.to_user.id)
        
        incoming_pending = Friendship.objects.filter(to_user=request.user, status='pending')
        for f in incoming_pending:
            exclude_ids.add(f.from_user.id)
        
        outgoing_pending = Friendship.objects.filter(from_user=request.user, status='pending')
        for f in outgoing_pending:
            exclude_ids.add(f.to_user.id)
        
        users = users.exclude(id__in=exclude_ids)
        
        return render(request, 'friends/search.html', {'users': users, 'query': q})
    else:
        return redirect('social:friend_list')

@login_required
def group_list(request):
    groups = Group.objects.all()
    return render(request, 'groups/group_list.html', {'groups': groups})

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    memberships = GroupMembership.objects.filter(group=group)
    members = []
    for m in memberships:
        members.append({'user': m.user, 'role': m.role})
    is_member = GroupMembership.objects.filter(group=group, user=request.user).exists()
    context = {
        'group': group,
        'members': members,
        'is_member': is_member,
    }
    return render(request, 'groups/group_detail.html', context)

@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()
            GroupMembership.objects.create(user=request.user, group=group, role='admin')
            return redirect('social:group_list')
    else:
        form = GroupForm()
    return render(request, 'groups/create_group.html', {'form': form})


@login_required
def join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        GroupMembership.objects.create(user=request.user, group=group)
    return redirect('social:group_detail', group_id=group.id)


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if membership:
        membership.delete()
    return redirect('social:group_list')

@login_required
def social_main(request):
    from core.models import UserProfile
    from garminconnect.models import GarminDailySteps, GarminActivity
    from django.db.models import Sum, F, Value, IntegerField, DecimalField
    from django.db.models.functions import Coalesce
    from django.db.models import FloatField
    from core.models import Transaction
    from datetime import timedelta, date
    from django.utils import timezone
    from django.db.models import FloatField

    current_category = request.GET.get('category', 'steps')
    current_history = request.GET.get('history', 'All Time')
    current_scope = request.GET.get('scope', 'Global')
    group_id = request.GET.get('group_id')

    # Calculate cutoff based on history
    now = timezone.now()
    if current_history == 'All Time':
        cutoff = date(2000, 1, 1)
    elif current_history == 'Weekly':
        cutoff = now.date() - timedelta(days=7)
    elif current_history == 'Monthly':
        cutoff = now.date() - timedelta(days=30)
    else:
        cutoff = date(2000, 1, 1)

    # Base users queryset based on scope
    if current_scope == 'friends':
        users = UserProfile.objects.filter(
            Q(friendship_requests_sent__to_user=request.user, friendship_requests_sent__status='accepted') |
            Q(friendship_requests_received__from_user=request.user, friendship_requests_received__status='accepted')
        ).exclude(id=request.user.id)
    elif current_scope == 'group' and group_id:
        group = get_object_or_404(Group, id=group_id)
        # Check if user is in group
        if not GroupMembership.objects.filter(user=request.user, group=group).exists():
            # Redirect to global or error, but for now, use all
            users = UserProfile.objects.none()
        else:
            users = UserProfile.objects.filter(member_groups__group=group)
    else:
        users = UserProfile.objects.all()

    available_metrics = {
    'steps': {'field': Sum('garmin_daily_steps__steps', filter=Q(garmin_daily_steps__date__gte=cutoff)), 'label': 'Steps', 'default': 0, 'output_field': IntegerField()},
    'lifts': {'field': Value(0), 'label': 'lbs Lifted', 'default': 0.0, 'output_field': FloatField()},
    'calories': {'field': Sum('garmin_activities__calories', filter=Q(garmin_activities__start_time_utc__date__gte=cutoff)), 'label': 'Calories Burned', 'default': 0.0, 'output_field': FloatField()},
    'coins': {'field': Sum('transactions__amount', filter=Q(transactions__currency_type='cardio_coins', transactions__created_at__date__gte=cutoff)), 'label': 'Coins', 'default': 0.0, 'output_field': DecimalField()},
    'gems': {'field': Sum('transactions__amount', filter=Q(transactions__currency_type='gym_gems', transactions__created_at__date__gte=cutoff)), 'label': 'Gems', 'default': 0.0, 'output_field': DecimalField()},
    'sleep': {'field': Value(0), 'label': 'Hours Slept', 'default': 0, 'output_field': IntegerField()},
    'consumed': {'field': Sum('unified_nutrition__calories', filter=Q(unified_nutrition__datetime__date__gte=cutoff)), 'label': 'Calories Consumed', 'default': 0.0, 'output_field': FloatField()},
    'water': {'field': Sum('unified_water__amount_ounces', filter=Q(unified_water__date__gte=cutoff)), 'label': 'Oz of Water Drank', 'default': 0.0, 'output_field': FloatField()},
    }


    if current_category not in available_metrics:
        current_category = 'steps'

    info = available_metrics[current_category]

    if current_category == 'lifts':
        # Annotate with placeholder for consistency, but override with computation
        annotated_users = users.annotate(
            metric_value=Coalesce(info['field'], Value(info['default']), output_field=info['output_field'])
        )
        
        # Calculate total lift volume for each user
        lift_volumes = {}
        for user in users:
            # Use unified/core Workout.start_time for the social leaderboard aggregation
            workouts = LWorkout.objects.filter(
                user=user,
                timestamp__date__gte=cutoff
            )
            total_volume = 0
            for workout in workouts:
                total_volume += workout.get_total_volume(unit='lb')
            lift_volumes[user.id] = total_volume
        
        sorted_users = sorted(annotated_users, key=lambda u: lift_volumes.get(u.id, 0), reverse=True)

        # Top 5 for podium
        users_query = sorted_users[:5]
        users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': lift_volumes[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(users_query)
        ]

        # Top 10 for list
        list_users_query = sorted_users[:10]
        list_users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': lift_volumes[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(list_users_query)
        ]
        list_users = list_users[3:] if len(list_users) > 3 else []
    elif current_category == 'consumed':
        # Annotate with placeholder for consistency, but override with computation
        annotated_users = users.annotate(
            metric_value=Coalesce(info['field'], Value(info['default']), output_field=info['output_field'])
        )
        
        # Calculate total consumed calories for each user
        consumed_calories = {}
        for user in users:
            nutrition_entries = NutritionEntry.objects.filter(
                user=user, 
                datetime__date__gte=cutoff
            )
            total_calories = 0
            for entry in nutrition_entries:
                if entry.calories:
                    total_calories += float(entry.calories)
            consumed_calories[user.id] = total_calories
        
        sorted_users = sorted(annotated_users, key=lambda u: consumed_calories.get(u.id, 0), reverse=True)
        
        # Top 5 for podium
        users_query = sorted_users[:5]
        users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': consumed_calories[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(users_query)
        ]
        
        # Top 10 for list
        list_users_query = sorted_users[:10]
        list_users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': consumed_calories[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(list_users_query)
        ]
        list_users = list_users[3:] if len(list_users) > 3 else []
    elif current_category == 'water':
        # Annotate with placeholder for consistency, but override with computation
        annotated_users = users.annotate(
            metric_value=Coalesce(info['field'], Value(info['default']), output_field=info['output_field'])
        )
        
        # Calculate total water consumed for each user
        water_amounts = {}
        for user in users:
            water_entries = DailyWater.objects.filter(
                user=user, 
                date__gte=cutoff
            )
            total_water = 0
            for entry in water_entries:
                total_water += float(entry.amount_ounces)
            water_amounts[user.id] = total_water
        
        sorted_users = sorted(annotated_users, key=lambda u: water_amounts.get(u.id, 0), reverse=True)
        
        # Top 5 for podium
        users_query = sorted_users[:5]
        users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': water_amounts[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(users_query)
        ]
        
        # Top 10 for list
        list_users_query = sorted_users[:10]
        list_users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': water_amounts[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(list_users_query)
        ]
        list_users = list_users[3:] if len(list_users) > 3 else []

    elif current_category == 'sleep':
        # Calculate sleep duration manually since we can't sum JSON fields
        from core.models import Sleep
        from django.db.models import F, ExpressionWrapper, DurationField
        from datetime import timedelta
        
        # Annotate with placeholder for consistency, but override with computation
        annotated_users = users.annotate(
            metric_value=Coalesce(Value(0), Value(0), output_field=IntegerField())
        )
        
        # Calculate sleep hours for each user
        sleep_hours = {}
        for user in users:
            sleep_records = Sleep.objects.filter(
                user=user, 
                start_time__date__gte=cutoff
            )
            total_seconds = 0
            for record in sleep_records:
                if record.end_time and record.start_time:
                    total_seconds += (record.end_time - record.start_time).total_seconds()
            sleep_hours[user.id] = round(total_seconds / 3600, 1) if total_seconds else 0
        
        sorted_users = sorted(annotated_users, key=lambda u: sleep_hours.get(u.id, 0), reverse=True)
        
        # Top 5 for podium
        users_query = sorted_users[:5]
        users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': sleep_hours[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(users_query)
        ]
        
        # Top 10 for list
        list_users_query = sorted_users[:10]
        list_users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': sleep_hours[u.id],
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(list_users_query)
        ]
        list_users = list_users[3:] if len(list_users) > 3 else []

    else:
        # Annotate once
        annotated_users = users.annotate(
            metric_value=Coalesce(info['field'], Value(info['default']), output_field=info['output_field'])
        ).order_by('-metric_value')

        # Top 5 for podium
        users_query = annotated_users[:5]
        users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': float(u.metric_value) if u.metric_value is not None else float(info['default']),
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(users_query)
        ]

        # Top 10 for list
        list_users_query = annotated_users[:10]
        list_users = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': float(u.metric_value) if u.metric_value is not None else float(info['default']),
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(list_users_query)
        ]
        list_users = list_users[3:] if len(list_users) > 3 else []

    # Pass user groups for group selection
    user_groups = list(request.user.member_groups.values('id', 'name')) if current_scope == 'group' and not group_id else []

    return render(request, 'social/main.html', {
        'user': request.user,
        'users': users,
        'list_users': list_users,
        'metric': info['label'],
        'current_category': current_category,
        'current_history': current_history,
        'current_scope': current_scope,
        'group_id': group_id,
        'available_categories': list(available_metrics.keys()),
        'user_groups': user_groups
    })

@require_GET
def cumulative_data_api(request):
    """
    API endpoint: /social/api/cumulative-data/
    Parameters: category, history, scope, group_id
    Returns JSON structure described in Docs/plan.md
    """
    category = request.GET.get('category', 'steps')
    history = request.GET.get('history', 'All Time')
    scope = request.GET.get('scope', 'Global')
    group_id = request.GET.get('group_id')

    # normalize scope
    scope_lc = scope.lower() if scope else 'global'

    # determine date range and granularity
    start_date, end_date, granularity = get_time_range_and_granularity(history)

    # build base users queryset based on scope (reuse logic from social_main)
    if scope_lc == 'friends':
        users_qs = UserProfile.objects.filter(
            Q(friendship_requests_sent__to_user=request.user, friendship_requests_sent__status='accepted') |
            Q(friendship_requests_received__from_user=request.user, friendship_requests_received__status='accepted')
        ).exclude(id=request.user.id)
    elif scope_lc == 'group' and group_id:
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return JsonResponse({'error': 'Group not found'}, status=404)
        if not GroupMembership.objects.filter(user=request.user, group=group).exists():
            return JsonResponse({'error': 'Not a member of group'}, status=403)
        users_qs = UserProfile.objects.filter(member_groups__group=group)
    else:
        users_qs = UserProfile.objects.all()

    # Batch-aggregate totals per user for ranking to avoid per-user queries
    user_ids = list(users_qs.values_list('id', flat=True)[:1000])  # cap for safety

    totals_map = {}
    if category == 'steps':
        from garminconnect.models import GarminDailySteps
        qs = GarminDailySteps.objects.filter(user_id__in=user_ids, date__gte=start_date, date__lte=end_date)
        for row in qs.values('user_id').annotate(total=Coalesce(Sum('steps'), Value(0), output_field=IntegerField())):
            totals_map[row['user_id']] = row['total'] or 0
    elif category == 'calories':
        from garminconnect.models import GarminActivity
        qs = GarminActivity.objects.filter(user_id__in=user_ids, start_time_utc__date__gte=start_date, start_time_utc__date__lte=end_date)
        for row in qs.values('user_id').annotate(total=Coalesce(Sum('calories'), Value(0), output_field=FloatField())):
            totals_map[row['user_id']] = row['total'] or 0
    elif category == 'lifts':
        # Aggregate from both liftosaur.Workout (uses `timestamp`) and core.models.Workout (uses `start_time`)
        try:
            from liftosaur.models import Workout as LWorkout
        except Exception:
            LWorkout = None
        try:
            from core.models import Workout as CoreWorkout
        except Exception:
            CoreWorkout = None

        lworkouts = LWorkout.objects.filter(user_id__in=user_ids, timestamp__date__gte=start_date, timestamp__date__lte=end_date).select_related('user') if (LWorkout is not None and hasattr(LWorkout, 'timestamp')) else []
        cworkouts = CoreWorkout.objects.filter(user_id__in=user_ids, start_time__date__gte=start_date, start_time__date__lte=end_date).select_related('user') if (CoreWorkout is not None and hasattr(CoreWorkout, 'start_time')) else []

        for w in list(lworkouts) + list(cworkouts):
            try:
                uid = getattr(w, 'user_id', None) or (getattr(w, 'user', None).id if getattr(w, 'user', None) else None)
                totals_map.setdefault(uid, 0)
                if hasattr(w, 'get_total_volume'):
                    totals_map[uid] += float(w.get_total_volume(unit='lb') or 0)
                else:
                    # fallback: attempt common attribute name if present
                    if hasattr(w, 'total_volume'):
                        totals_map[uid] += float(getattr(w, 'total_volume') or 0)
            except Exception:
                continue
    elif category == 'coins':
        total_qs = Transaction.objects.filter(user_id__in=user_ids, currency_type='cardio_coins', created_at__date__gte=start_date, created_at__date__lte=end_date)
        for row in total_qs.values('user_id').annotate(total=Coalesce(Sum('amount'), Value(0), output_field=FloatField())):
            totals_map[row['user_id']] = float(row['total'] or 0)
    elif category == 'gems':
        total_qs = Transaction.objects.filter(user_id__in=user_ids, currency_type='gym_gems', created_at__date__gte=start_date, created_at__date__lte=end_date)
        for row in total_qs.values('user_id').annotate(total=Coalesce(Sum('amount'), Value(0), output_field=FloatField())):
            totals_map[row['user_id']] = float(row['total'] or 0)
    elif category == 'consumed':
        total_qs = NutritionEntry.objects.filter(user_id__in=user_ids, datetime__date__gte=start_date, datetime__date__lte=end_date)
        for row in total_qs.values('user_id').annotate(total=Coalesce(Sum('calories'), Value(0), output_field=FloatField())):
            totals_map[row['user_id']] = float(row['total'] or 0)
    elif category == 'water':
        total_qs = DailyWater.objects.filter(user_id__in=user_ids, date__gte=start_date, date__lte=end_date)
        for row in total_qs.values('user_id').annotate(total=Coalesce(Sum('amount_ounces'), Value(0), output_field=FloatField())):
            totals_map[row['user_id']] = float(row['total'] or 0)
    elif category == 'sleep':
        # aggregate total sleep hours per user by scanning Sleep rows in batch
        sleep_qs = Sleep.objects.filter(user_id__in=user_ids, start_time__date__gte=start_date, start_time__date__lte=end_date)
        for s in sleep_qs:
            if s.end_time and s.start_time:
                secs = (s.end_time - s.start_time).total_seconds()
                totals_map.setdefault(s.user_id, 0)
                totals_map[s.user_id] += secs / 3600.0
            else:
                pass
    else:
        pass

    # Ensure every user has an entry (default 0)
    for uid in user_ids:
        totals_map.setdefault(uid, 0)

    # Build sorted list of (UserProfile, total) for top 10
    users_with_totals = []
    users_by_id = {u.id: u for u in users_qs}
    for uid, tot in totals_map.items():
        user_obj = users_by_id.get(uid)
        if user_obj:
            users_with_totals.append((user_obj, tot))
    user_totals_sorted = sorted(users_with_totals, key=lambda x: x[1], reverse=True)[:10]

    # Build labels depending on granularity
    labels = []
    if granularity == 'daily':
        for d in daterange(start_date, end_date):
            labels.append(d.isoformat())
    else:
        # weekly buckets starting on start_date, label by week-start ISO date
        cur = start_date
        while cur <= end_date:
            labels.append(cur.isoformat())
            cur = cur + timedelta(weeks=1)

    # For the selected top users, fetch per-label aggregates in bulk to minimize queries.
    top_user_ids = [u.id for u, _ in user_totals_sorted]
    users_response = []

    # Preload mappings per (user_id, date) for supported categories
    per_user_date_map = {}  # (user_id, date_iso) -> value
    if category in ('steps',):
        from garminconnect.models import GarminDailySteps
        qs = GarminDailySteps.objects.filter(user_id__in=top_user_ids, date__gte=start_date, date__lte=end_date)
        for row in qs.values('user_id', 'date').annotate(total=Coalesce(Sum('steps'), Value(0), output_field=IntegerField())):
            per_user_date_map[(row['user_id'], row['date'].isoformat())] = row['total'] or 0
    elif category in ('calories',):
        from garminconnect.models import GarminActivity
        qs = GarminActivity.objects.filter(user_id__in=top_user_ids, start_time_utc__date__gte=start_date, start_time_utc__date__lte=end_date)
        for row in qs.values('user_id', start_date_field:= 'start_time_utc__date').annotate(total=Coalesce(Sum('calories'), Value(0), output_field=FloatField())):
            # values() with dynamic field name returns key like start_time_utc__date
            d = row.get(start_date_field) or row.get('start_time_utc__date')
            if d:
                per_user_date_map[(row['user_id'], d.isoformat())] = row['total'] or 0
    elif category in ('coins', 'gems'):
        tx_filter = {'currency_type': 'cardio_coins' if category == 'coins' else 'gym_gems'}
        qs = Transaction.objects.filter(user_id__in=top_user_ids, created_at__date__gte=start_date, created_at__date__lte=end_date, **tx_filter)
        # use created_at__date key and sum the amount field
        for row in qs.values('user_id', 'created_at__date').annotate(total=Coalesce(Sum('amount'), Value(0), output_field=FloatField())):
            d = row.get('created_at__date')
            if d:
                per_user_date_map[(row['user_id'], d.isoformat())] = row['total'] or 0
    elif category in ('consumed',):
        qs = NutritionEntry.objects.filter(user_id__in=top_user_ids, datetime__date__gte=start_date, datetime__date__lte=end_date)
        for row in qs.values('user_id', 'datetime__date').annotate(total=Coalesce(Sum('calories'), Value(0), output_field=FloatField())):
            d = row.get('datetime__date')
            if d:
                per_user_date_map[(row['user_id'], d.isoformat())] = float(row['total'] or 0)
    elif category in ('water',):
        qs = DailyWater.objects.filter(user_id__in=top_user_ids, date__gte=start_date, date__lte=end_date)
        for row in qs.values('user_id', 'date').annotate(total=Coalesce(Sum('amount_ounces'), Value(0), output_field=FloatField())):
            per_user_date_map[(row['user_id'], row['date'].isoformat())] = float(row['total'] or 0)
    elif category in ('sleep',):
        qs = Sleep.objects.filter(user_id__in=top_user_ids, start_time__date__gte=start_date, start_time__date__lte=end_date)
        for s in qs:
            if s.end_time and s.start_time:
                d = s.start_time.date().isoformat()
                secs = (s.end_time - s.start_time).total_seconds()
                per_user_date_map.setdefault((s.user_id, d), 0)
                per_user_date_map[(s.user_id, d)] += round(secs / 3600.0, 2)
    elif category in ('lifts',):
        # fetch workouts for all top users in range from both liftosaur and core Workouts,
        # compute per-workout volume, then bucket by date (using timestamp or start_time)
        try:
            from liftosaur.models import Workout as LWorkout
        except Exception:
            LWorkout = None
        try:
            from core.models import Workout as CoreWorkout
        except Exception:
            CoreWorkout = None

        lws = LWorkout.objects.filter(user_id__in=top_user_ids, timestamp__date__gte=start_date, timestamp__date__lte=end_date).select_related('user') if (LWorkout is not None and hasattr(LWorkout, 'timestamp')) else []
        cws = CoreWorkout.objects.filter(user_id__in=top_user_ids, start_time__date__gte=start_date, start_time__date__lte=end_date).select_related('user') if (CoreWorkout is not None and hasattr(CoreWorkout, 'start_time')) else []

        for w in list(lws) + list(cws):
            try:
                # determine user id
                uid = getattr(w, 'user_id', None) or (getattr(w, 'user', None).id if getattr(w, 'user', None) else None)
                # determine date from timestamp or start_time
                dt = None
                if hasattr(w, 'timestamp') and getattr(w, 'timestamp') is not None:
                    dt = getattr(w, 'timestamp')
                elif hasattr(w, 'start_time') and getattr(w, 'start_time') is not None:
                    dt = getattr(w, 'start_time')
                if dt is None:
                    continue
                # Prefer object-level get_total_volume (core.Workout). If missing (Liftosaur Workout),
                # compute by summing exercises' volumes via their get_volume method.
                vol = 0.0
                if hasattr(w, 'get_total_volume'):
                    try:
                        vol = float(w.get_total_volume(unit='lb') or 0)
                    except Exception:
                        vol = 0.0
                else:
                    # Try to sum related exercises (Liftosaur model uses .exercises related_name)
                    ex_qs = getattr(w, 'exercises', None) or getattr(w, 'unified_exercises', None)
                    if ex_qs is not None and hasattr(ex_qs, 'all'):
                        try:
                            for ex in ex_qs.all():
                                if hasattr(ex, 'get_volume'):
                                    vol += float(ex.get_volume('lb') or 0)
                        except Exception:
                            vol = vol or 0.0
                d = dt.date().isoformat()
                per_user_date_map.setdefault((uid, d), 0)
                per_user_date_map[(uid, d)] += vol
            except Exception:
                continue

    # Now build the response per user using the per_user_date_map to avoid per-user DB hits
    for idx, (user, total_val) in enumerate(user_totals_sorted):
        running = 0
        data_points = []
        for lbl in labels:
            # If we're using weekly granularity, sum the 7-day bucket starting at the label date.
            if granularity == 'weekly':
                try:
                    start_lbl_date = date.fromisoformat(lbl)
                except Exception:
                    # Fallback: treat label as daily if parsing fails
                    start_lbl_date = None
                if start_lbl_date:
                    week_sum = 0.0
                    for i in range(7):
                        key_date = (start_lbl_date + timedelta(days=i)).isoformat()
                        week_sum += float(per_user_date_map.get((user.id, key_date), 0) or 0)
                    v_num = week_sum
                else:
                    v_num = float(per_user_date_map.get((user.id, lbl), 0) or 0)
            else:
                v = per_user_date_map.get((user.id, lbl), 0)
                try:
                    v_num = float(v)
                except Exception:
                    v_num = v if v is not None else 0
            if category in CUMULATIVE_METRICS:
                running += (v_num or 0)
                data_points.append({'date': lbl, 'value': v_num, 'cumulative_value': running})
            else:
                data_points.append({'date': lbl, 'value': v_num})

        users_response.append({
            'id': user.id,
            'name': user.username,
            'avatar': user.avatar.url if getattr(user, 'avatar', None) else '',
            'rank': idx + 1,
            'podium_position': 'gold' if idx == 0 else ('silver' if idx == 1 else ('bronze' if idx == 2 else '')),
            'data_points': data_points
        })

    resp = {
        'users': users_response,
        'date_range': {'start': labels[0] if labels else start_date.isoformat(), 'end': labels[-1] if labels else end_date.isoformat()},
        'granularity': granularity,
        'metric_type': 'cumulative' if category in CUMULATIVE_METRICS else 'daily'
    }
    return JsonResponse(resp, safe=True)