from django.urls import path
from .views import *

app_name = 'fitness'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('sign-up/', SignUpView.as_view(), name='sign_up'),
    path('sign-in/', SignInView.as_view(), name='sign_in'),
    path('sign-out/', SignOutView.as_view(), name='sign_out'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('data-priorities/', DataPriorityView.as_view(), name='data_priorities'),
    path('sync-data/', sync_data_view, name='sync_data_view'),
    path('bodyweight/submit/', bodyweight_submit, name='bodyweight_submit'),
    path('connect-liftosaur/', LiftosaurConnectView.as_view(), name='connect_liftosaur'),
    path('disconnect-liftosaur/', LiftosaurDisconnectView.as_view(), name='disconnect_liftosaur'),
    
    # Placeholders
    path('comingsoon/', ComingSoonView.as_view(), name='comingsoon'),
    path('offline/', OfflineView.as_view(), name='offline'),
    path('sw.js', ServiceWorkerView.as_view(), name='service_worker'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('gym/', GymView.as_view(), name='gym'),
    path('locker_room/', LockerRoomView.as_view(), name='locker_room'),
    path('shop/', ShopView.as_view(), name='shop'),
    path('api/stats/', StatsAPIView.as_view(), name='stats_api'),
]
