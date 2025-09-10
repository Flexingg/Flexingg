from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import UserProfile
from django.urls import reverse
from django.db.models import Q
from .models import Friendship, Group, GroupMembership
from django import forms

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
        return redirect('friends:friend_requests')
    friendship.status = 'accepted'
    friendship.save()
    return redirect('friends:friend_list')

@login_required
def decline_friend_request(request, request_id):
    friendship = get_object_or_404(Friendship, id=request_id)
    if friendship.to_user != request.user:
        return redirect('friends:friend_requests')
    friendship.delete()
    return redirect('friends:friend_requests')

@login_required
def remove_friend(request, user_id):
    target_user = get_object_or_404(UserProfile, id=user_id)
    if target_user == request.user:
        return redirect('friends:friend_list')
    friendship1 = Friendship.objects.filter(from_user=request.user, to_user=target_user, status='accepted').first()
    friendship2 = Friendship.objects.filter(from_user=target_user, to_user=request.user, status='accepted').first()
    if friendship1:
        friendship1.delete()
    if friendship2:
        friendship2.delete()
    return redirect('friends:friend_list')

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
            return redirect('friends:friend_list')
        
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
        return redirect('friends:friend_list')

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
            return redirect('groups:group_list')
    else:
        form = GroupForm()
    return render(request, 'groups/create_group.html', {'form': form})


@login_required
def join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        GroupMembership.objects.create(user=request.user, group=group)
    return redirect('groups:group_detail', group_id=group.id)


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if membership:
        membership.delete()
    return redirect('groups:group_list')
