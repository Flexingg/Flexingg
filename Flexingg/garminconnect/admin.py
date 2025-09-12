from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered, AdminSite



# Register your models here.
app_models = []
apps_to_register = ['garminconnect']

for app_name in apps_to_register:
    try:
        app_models.extend(apps.get_app_config(app_name).get_models())
    except LookupError:
        # Skip if app is not installed/found
        pass

for model in app_models:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass
