# Core Admin Documentation

## Overview
The `Flexingg/core/admin.py` file configures the Django admin interface for the core app's models. It uses a dynamic registration approach to automatically register all models from the 'core' app using the standard `ModelAdmin`, except for `SweatScoreWeights` which is skipped for custom admin (not implemented in the provided code). This setup provides a quick admin interface for managing models like UserProfile, GarminActivity, etc. No custom admin classes or actions are defined beyond basic registration.

## Key Components
- **Imports**:
  - `django.contrib.admin` for admin site.
  - `django.apps` to get app models.
  - `AdminSite` and `AlreadyRegistered` for handling registrations.

- **Commented Code**:
  - A commented `CustomModelAdmin` class that would set `list_display` to all concrete fields (not active).

- **Dynamic Registration**:
  - Defines `app_models = []` and `apps_to_register = ['core']`.
  - Loops through registered apps to collect models: `app_models.extend(apps.get_app_config(app_name).get_models())`.
  - For each model in `app_models`:
    - Skips if `model.__name__ == 'SweatScoreWeights'` (intended for custom admin, e.g., specific list_display or actions).
    - Registers with `admin.site.register(model, admin.ModelAdmin)`.
    - Catches `AlreadyRegistered` exceptions to avoid duplicates.

## Usage and Customization
- Run `python manage.py createsuperuser` to access `/admin/`.
- All core models (e.g., UserProfile, ColorPreferences, Friendship, Gear, DailySteps, Garmin_Auth, GarminCredentials, GarminDailySteps, GarminActivity) get default admin interfaces showing all fields.
- For SweatScoreWeights: No registration; add custom `admin.py` class like:
  ```
  @admin.register(SweatScoreWeights)
  class SweatScoreWeightsAdmin(admin.ModelAdmin):
      list_display = ['zone', 'name', 'weight']
      list_editable = ['weight']
  ```
  to enable editing weights via admin.
- Error Handling: Skips non-installed apps via `LookupError`.
- Best Practices: For production, add search_fields, filters, or inlines for related models (e.g., activities per user).

This provides a basic but extensible admin setup for the fitness data models.