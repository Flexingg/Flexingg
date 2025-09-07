# Core URLs Documentation

## Overview
The `Flexingg/core/urls.py` file defines the URL configuration for the core app. It imports all views (`from .views import *`) and sets `app_name = 'fitness'` for namespaced URLs. The `urlpatterns` list maps paths to class-based views (via .as_view()) or function-based views. This handles routing for home, auth, settings, Garmin sync, and API endpoints for chart data. Included in the main project URLs via include('core.urls') presumably in Flexingg/urls.py.

## URL Patterns
All paths are relative to the app namespace 'fitness'. Here's the complete list:

- **Path**: `''`  
  **Name**: `home`  
  **Mapped to**: `HomeView.as_view()`  
  **Description**: Root route for the main dashboard/home page.

- **Path**: `'sign-up/'`  
  **Name**: `sign_up`  
  **Mapped to**: `SignUpView.as_view()`  
  **Description**: User registration page.

- **Path**: `'sign-in/'`  
  **Name**: `sign_in`  
  **Mapped to**: `SignInView.as_view()`  
  **Description**: User login page.

- **Path**: `'sign-out/'`  
  **Name**: `sign_out`  
  **Mapped to**: `SignOutView.as_view()`  
  **Description**: User logout endpoint.

- **Path**: `'settings/'`  
  **Name**: `settings`  
  **Mapped to**: `SettingsView.as_view()`  
  **Description**: Profile settings update page.

- **Path**: `'sync-garmin/'`  
  **Name**: `sync_garmin`  
  **Mapped to**: `SyncGarminView.as_view()`  
  **Description**: Garmin sync page (stub).

- **Path**: `'background-garmin-sync/'`  
  **Name**: `background_garmin_sync`  
  **Mapped to**: `BackgroundGarminSyncView.as_view()`  
  **Description**: Background Garmin sync API (POST, stub).

- **Path**: `'steps-chart-data/'`  
  **Name**: `steps_chart_data`  
  **Mapped to**: `StepsChartDataView.as_view()`  
  **Description**: Steps chart data API (GET, stub).

- **Path**: `'api/calories/chart-data/'`  
  **Name**: `calories-chart-data`  
  **Mapped to**: `get_calories_chart_data` (function)  
  **Description**: API for calories chart data (JSON, with ranges).

- **Path**: `'api/steps/chart-data/'`  
  **Name**: `steps-chart-data`  
  **Mapped to**: `get_steps_chart_data` (function)  
  **Description**: API for steps chart data (JSON, cumulative with friends).

- **Path**: `'api/sweat-score/chart-data/'`  
  **Name**: `sweat-score-chart-data`  
  **Mapped to**: `get_sweat_score_chart_data` (function)  
  **Description**: API for sweat score chart data (JSON, HR-based).

## Usage Notes
- **Namespace**: Use `{% url 'fitness:home' %}` in templates.
- **APIs**: Chart endpoints support `?range=current_month` etc.; require authentication.
- **Integration**: Likely included in main urls.py as `path('fitness/', include('core.urls'))` or similar.
- **Extensions**: Add more paths for social/health views (e.g., SocialIndexView, HealthView) as implemented.
- **No Regex**: All use simple path converters; no custom converters.

This configuration routes all core app functionality, supporting the fitness PWA's pages and data APIs.