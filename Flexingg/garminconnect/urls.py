from django.urls import path
from .views import SyncGarminView, BackgroundGarminSyncView, ConnectGarminView, DisconnectGarminView

app_name = 'garminconnect'

urlpatterns = [
    path('sync-garmin/', SyncGarminView.as_view(), name='sync_garmin'),
    path('background-garmin-sync/', BackgroundGarminSyncView.as_view(), name='background_garmin_sync'),
    path('connect-garmin/', ConnectGarminView.as_view(), name='connect_garmin'),
    path('disconnect-garmin/', DisconnectGarminView.as_view(), name='disconnect_garmin'),
]