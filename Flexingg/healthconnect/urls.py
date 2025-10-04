from django.urls import path
from . import views

app_name = 'healthconnect'

urlpatterns = [
    path('connect/', views.connect_healthconnect, name='connect'),
    path('sync/', views.sync_healthconnect, name='sync'),
    path('disconnect/', views.disconnect_healthconnect, name='disconnect'),
    path('download-apk/', views.download_flexingg_sync_apk, name='download_apk'),
    # Trigger a fast staging sync (write-only staging + background processing)
    path('trigger-staged-sync/', views.trigger_healthconnect_staged_sync, name='trigger_staged_sync'),
]