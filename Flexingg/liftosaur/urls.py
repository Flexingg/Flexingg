from django.urls import path
from .views import sync_workout_data

urlpatterns = [
    # Changed the name to be more descriptive
    path('sync/', sync_workout_data, name='sync_workout_data'),
]

