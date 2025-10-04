from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Friendship, GroupMembership, Group
from .serializers import FriendshipSerializer, GroupMembershipSerializer, GroupSerializer
from core.api_views import router

class FriendshipViewSet(viewsets.ModelViewSet):
    queryset = Friendship.objects.all()
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

class GroupMembershipViewSet(viewsets.ModelViewSet):
    queryset = GroupMembership.objects.all()
    serializer_class = GroupMembershipSerializer
    permission_classes = [IsAuthenticated]

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]



router.register(r'social-friendships', FriendshipViewSet, basename="social-friendships")
router.register(r'social-group-memberships', GroupMembershipViewSet)
router.register(r'social-groups', GroupViewSet)