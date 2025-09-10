from django.urls import path, include
from .views import *

urlpatterns = [
    path('friends/', include('social.friends.urls')),
    path('groups/', include('social.groups.urls')),
]