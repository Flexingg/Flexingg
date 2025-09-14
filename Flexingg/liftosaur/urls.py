app_name = 'liftosaur'

from django.urls import path
from .views import sync_workout_data, import_data

urlpatterns = [
    # Changed the name to be more descriptive
    path('sync/', sync_workout_data, name='sync_workout_data'),
    path('import/', import_data, name='import_data'),
]

