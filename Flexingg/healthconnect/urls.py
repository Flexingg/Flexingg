from django.urls import path
from . import views

app_name = 'healthconnect'

urlpatterns = [
    path('connect/', views.connect_healthconnect, name='connect'),
    path('sync/', views.sync_healthconnect, name='sync'),
    path('disconnect/', views.disconnect_healthconnect, name='disconnect'),
]