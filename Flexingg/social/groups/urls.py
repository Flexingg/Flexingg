from django.urls import path
from ..views import *

app_name = 'groups'

urlpatterns = [
    path('', group_list, name='group_list'),
    path('create/', create_group, name='create_group'),
    path('<int:group_id>/', group_detail, name='group_detail'),
    path('<int:group_id>/join/', join_group, name='join_group'),
    path('<int:group_id>/leave/', leave_group, name='leave_group'),
]