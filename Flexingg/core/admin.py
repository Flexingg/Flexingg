from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered, AdminSite


# class CustomModelAdmin(admin.ModelAdmin): #For use with non unfold admin
#     def __init__(self, model, admin_site):
#         self.list_display = [field.name for field in model._meta.concrete_fields]
#         super(CustomModelAdmin, self).__init__(model, admin_site)

# Register your models here.
app_models = []
apps_to_register = ['core']

for app_name in apps_to_register:
    try:
        app_models.extend(apps.get_app_config(app_name).get_models())
    except LookupError:
        # Skip if app is not installed/found
        pass

for model in app_models:
    # Skip SweatScoreWeights as it has a custom admin class
    if model.__name__ == 'SweatScoreWeights':
        continue
    try:
        admin.site.register(model, admin.ModelAdmin) 
    except AlreadyRegistered:
        pass