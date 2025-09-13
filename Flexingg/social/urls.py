from django.urls import path, include
from .views import *

app_name = 'social'

urlpatterns = [
    path('', social_main, name='main'),
    path('friends/', friend_list, name='friend_list'),
    path('friends/request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('friends/decline/<int:request_id>/', decline_friend_request, name='decline_friend_request'),
    path('friends/remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('friends/search/', search_users, name='search_users'),
    path('friends/requests/', friend_requests, name='friend_requests'),
    path('groups/', group_list, name='group_list'),
    path('groups/create/', create_group, name='create_group'),
    path('groups/<int:group_id>/', group_detail, name='group_detail'),
    path('groups/<int:group_id>/join/', join_group, name='join_group'),
    path('groups/<int:group_id>/leave/', leave_group, name='leave_group'),
]