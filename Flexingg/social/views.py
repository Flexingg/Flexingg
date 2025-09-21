from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import UserProfile
from django.urls import reverse
from django.db.models import Q
from .models import Friendship, Group, GroupMembership
from django import forms
from liftosaur.models import Workout, WorkoutExercise, WorkoutSet
from django.db.models import Sum, F, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from django.db.models import FloatField
from core.models import *
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import FloatField

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
            workouts = Workout.objects.filter(
                user=user, 
                start_time__date__gte=cutoff
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