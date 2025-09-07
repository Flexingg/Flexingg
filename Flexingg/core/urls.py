from django.urls import path
from .views import *

app_name = 'fitness'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('sign-up/', SignUpView.as_view(), name='sign_up'),
    path('sign-in/', SignInView.as_view(), name='sign_in'),
    path('sign-out/', SignOutView.as_view(), name='sign_out'),
    path('settings/', SettingsView.as_view(), name='settings'),
    
    path('sync-garmin/', SyncGarminView.as_view(), name='sync_garmin'),
    path('background-garmin-sync/', BackgroundGarminSyncView.as_view(), name='background_garmin_sync'),
    path('connect-garmin/', ConnectGarminView.as_view(), name='connect_garmin'),
    path('disconnect-garmin/', DisconnectGarminView.as_view(), name='disconnect_garmin'),
    path('steps-chart-data/', StepsChartDataView.as_view(), name='steps_chart_data'),

    # Calories Chart Data URL
    path('api/calories/chart-data/', get_calories_chart_data, name='calories-chart-data'),
    # Steps Chart Data URL
    path('api/steps/chart-data/', get_steps_chart_data, name='steps-chart-data'),
    # Sweat Score Chart Data URL
    path('api/sweat-score/chart-data/', get_sweat_score_chart_data, name='sweat-score-chart-data'),
]
