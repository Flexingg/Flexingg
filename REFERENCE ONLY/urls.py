from django.urls import path
from . import views
from .api import api

app_name = 'fitness'

urlpatterns = [
    # Dashboard URL
    path('', views.FitnessDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.FitnessDashboardView.as_view(), name='dashboard2'),

    # Health URL
    path('health/', views.HealthView.as_view(), name='health'),

    # Weight Record URLs
    path('weight/', views.WeightRecordListView.as_view(), name='weight-list'),
    path('weight/add/', views.WeightRecordCreateView.as_view(), name='weight-add'),
    path('weight/<uuid:pk>/edit/', views.WeightRecordUpdateView.as_view(), name='weight-edit'),
    path('weight/<uuid:pk>/delete/', views.WeightRecordDeleteView.as_view(), name='weight-delete'),
    path('weight/quick-add/', views.WeightQuickAddView.as_view(), name='weight-quick-add'),

    # Weight Goal URLs
    path('weight/goal/add/', views.WeightGoalCreateView.as_view(), name='weight-goal-add'),
    path('weight/goal/<int:pk>/edit/', views.WeightGoalUpdateView.as_view(), name='weight-goal-edit'),

    # Garmin Connect URLs
    path('garmin/link/start/', views.LinkGarminStartView.as_view(), name='link_garmin_start'),
    path('garmin/link/password/', views.LinkGarminPasswordView.as_view(), name='link_garmin_password'), # Page to enter password
    path('garmin/unlink/', views.UnlinkGarminView.as_view(), name='unlink_garmin'),
    path('garmin/sync/', views.SyncGarminDataView.as_view(), name='sync_garmin'), # URL to trigger sync
    path('garmin/sync/background/', views.BackgroundGarminSyncView.as_view(), name='background_garmin_sync'), # Background sync endpoint

    # Garmin Activity URLs
    path('garmin/activities/', views.GarminActivityListView.as_view(), name='garmin_activity_list'),
    path('garmin/activities/<uuid:pk>/', views.GarminActivityDetailView.as_view(), name='garmin_activity_detail'),

    # Social Activity Feed URL
    path('social/activities/', views.SocialActivityFeedView.as_view(), name='social_activity_feed'),

    # API URLs
    path('api/weight/chart-data/', views.get_chart_data, name='weight-chart-data'),
    path('api/weight/stats/', views.weight_stats, name='weight-stats'),
    path('api/weight/<uuid:record_id>/', views.api_weight_detail, name='api-weight-detail'),

    # Django-Ninja API URLs
    path('api/', api.urls),

    # Weight Trend Data URL
    path('weight/trend-data/', views.WeightTrendDataView.as_view(), name='weight-trend-data'),
    # Calories Chart Data URL
    path('api/calories/chart-data/', views.get_calories_chart_data, name='calories-chart-data'),
    # Steps Chart Data URL
    path('api/steps/chart-data/', views.get_steps_chart_data, name='steps-chart-data'),
    # Sweat Score Chart Data URL
    path('api/sweat-score/chart-data/', views.get_sweat_score_chart_data, name='sweat-score-chart-data'),
]