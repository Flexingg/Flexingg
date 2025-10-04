from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

# Import router objects from each app's api_views module and combine their URLs.
from core import api_views as core_api
from garminconnect import api_views as garmin_api
from healthconnect import api_views as health_api
from liftosaur import api_views as lift_api
from social import api_views as social_api


# Combine routers' urls into a single list to serve under /api/v1/
api_urlpatterns = []
api_urlpatterns += core_api.router.urls
api_urlpatterns += garmin_api.router.urls
api_urlpatterns += health_api.router.urls
api_urlpatterns += lift_api.router.urls
api_urlpatterns += social_api.router.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Web application URLs (no API prefix)
    path('', include('core.urls')),
    path('liftosaur/', include('liftosaur.urls')),
    path('social/', include('social.urls')),
    path('garminconnect/', include('garminconnect.urls')),
    path('healthconnect/', include('healthconnect.urls')),
    
    # API URLs with consistent prefix
    path('api/v1/', include(api_urlpatterns)),
]