from django.urls import path
from ..views import *

app_name = 'friends'

urlpatterns = [
    path('request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('accept/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('decline/<int:request_id>/', decline_friend_request, name='decline_friend_request'),
    path('remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('search/', search_users, name='search_users'),
    path('', friend_list, name='friend_list'),
    path('requests/', friend_requests, name='friend_requests'),
]