from django.urls import path
from .views import SyncGarminView, BackgroundGarminSyncView, ConnectGarminView, DisconnectGarminView

app_name = 'garminconnect'

urlpatterns = [
    path('sync/', SyncGarminView.as_view(), name='sync_garmin'),
    path('background-sync/', BackgroundGarminSyncView.as_view(), name='background_garmin_sync'),
    path('connect/', ConnectGarminView.as_view(), name='connect_garmin'),
    path('disconnect/', DisconnectGarminView.as_view(), name='disconnect_garmin'),
]