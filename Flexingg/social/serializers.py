from rest_framework import serializers
from .models import Friendship, GroupMembership, Group

class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friendship
        fields = ['from_user', 'to_user', 'status', 'created_at']

class GroupMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMembership
        fields = ['user', 'group', 'date_joined', 'role']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description', 'creator', 'created_at', 'members']