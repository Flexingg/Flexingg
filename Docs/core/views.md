# Core Views Documentation

## Overview
The `Flexingg/core/views.py` file defines Django views for the fitness app: class-based views for rendering templates (home, auth, settings, stubs) and function-based API views for chart data (steps, calories, sweat score) with friend comparisons and rankings. Imports include logging, generic views, forms, auth utils, models, and timezone. User authentication is checked in most views. Chart APIs support date ranges (current_month, last_month, etc.) and return JSON with cumulative data, friends_data, podium, stats. Stub views for Garmin sync. calculate_sweat_score is a helper function.

## Class-Based Views

### HomeView (extends TemplateView)
- **Purpose**: Renders the main dashboard/home page.
- **Template**: 'home.html'.
- **Methods**:
  - `get_context_data(self, **kwargs)`: Adds user profile data if authenticated (profile, total_gems=gym_gems, total_coins=cardio_coins, level).
- **Handling**: GET only; redirects authenticated users to home.
- **Usage**: Root URL; displays user stats/currencies/level.

### SignUpView (extends View)
- **Purpose**: Handles user registration.
- **Template**: 'sign_up.html'.
- **Form**: SignUpForm.
- **Methods**:
  - `get(self, request)`: Renders form if not authenticated; redirects to home if authenticated.
  - `post(self, request)`: Validates form; saves user if valid, redirects to sign_in; re-renders on error.
- **Handling**: GET/POST; auth check.
- **Usage**: Signup flow; creates UserProfile.

### SignInView (extends View)
- **Purpose**: Handles user login.
- **Template**: 'sign_in.html'.
- **Form**: LoginForm.
- **Methods**:
  - `get(self, request)`: Renders form if not authenticated; redirects to home if authenticated.
  - `post(self, request)`: Validates form; authenticates user; logs in and redirects to home if success; re-renders on error.
- **Handling**: GET/POST; uses authenticate/login.
- **Usage**: Login flow with Gamertag.

### SignOutView (extends View)
- **Purpose**: Logs out user.
- **Methods**:
  - `get(self, request)`: Calls logout and redirects to sign_in.
- **Handling**: GET only.
- **Usage**: Logout endpoint.

### SyncGarminView (extends TemplateView)
- **Purpose**: Stub for Garmin sync page (template not created).
- **Template**: 'core/garmin_sync.html'.
- **Methods**:
  - `get_context_data(self, **kwargs)`: Adds {'message': 'Garmin Sync Page'}.
- **Handling**: GET only.
- **Usage**: Future Garmin sync UI.

### BackgroundGarminSyncView (extends View)
- **Purpose**: Stub for background Garmin sync API.
- **Methods**:
  - `post(self, request)`: If authenticated, returns JSON {'success': True, 'steps_synced': 0, 'activities_synced': 0}; else 401 error.
- **Handling**: POST only; dummy logic.
- **Usage**: AJAX sync trigger.

### StepsChartDataView (extends View)
- **Purpose**: Stub for steps chart data API.
- **Methods**:
  - `get(self, request)`: If authenticated, returns dummy JSON {'user_data': [{'date': '2024-09-01', 'steps': 10000}, ...]}; else 401.
- **Handling**: GET only.
- **Usage**: Chart JS data fetch (replace with real).

### SocialIndexView (extends TemplateView)
- **Purpose**: Renders social index page (template not listed).
- **Template**: 'social_index.html'.
- **Methods**:
  - `get_context_data(self, **kwargs)`: Adds profile if authenticated.
- **Handling**: GET only.
- **Usage**: Social features page.

### HealthView (extends TemplateView)
- **Purpose**: Renders health page (template not listed).
- **Template**: 'health.html'.
- **Methods**:
  - `get_context_data(self, **kwargs)`: Adds profile if authenticated.
- **Handling**: GET only.
- **Usage**: Health metrics page.

### SettingsView (extends View)
- **Purpose**: Handles profile settings update.
- **Template**: 'settings.html'.
- **Form**: ProfileForm.
- **Methods**:
  - `get(self, request)`: If authenticated, renders form with instance=user; redirects to sign_in if not.
  - `post(self, request)`: Validates form; saves if valid, redirects to settings; re-renders on error.
- **Handling**: GET/POST; context includes form and profile.
- **Usage**: Update username, email, height, weight, sex.

## Function-Based Views (APIs)

### get_calories_chart_data(request)
- **Purpose**: API for cumulative calories chart data with friends and podium (incomplete in code; cuts off at friends_data setup).
- **Handling**: GET; requires auth (else error).
- **Logic**:
  - Parses range_param (current_month default) to set start_date/end_date.
  - Queries GarminActivity for user calories in range, aggregates by date, makes cumulative.
  - Sets up friends via Friendship 'accepted' (from/to_user).
  - Prepares all_users_calories for ranking (user + friends).
  - Code incomplete: cuts off before returning JSON.
- **Response**: Expected JsonResponse with user_data (cumulative list), friends_data, podium_data (top 3), stats (totals, average, rank), date_range.
- **Usage**: Chart endpoint; supports ranges like last_year, alltime.

### get_steps_chart_data(request)
- **Purpose**: API for cumulative steps chart data from GarminDailySteps with friends/podium.
- **Handling**: GET; requires auth (401 else).
- **Logic**:
  - Parses range_param for date range.
  - Queries GarminDailySteps for user, aggregates by date, cumulative.
  - Gets friend IDs from accepted Friendships.
  - For each friend: Queries their steps, cumulative data (includes 0 days).
  - Aggregates totals for ranking (user + friends with >0 steps), sorts for podium (top 3).
  - Stats: user_total, friends_average, user_rank, sentence (placeholder).
- **Response**: JsonResponse({'user_data': list of {'date', 'steps'} cumulative, 'friends_data': list of {'name', 'data': cumulative}, 'podium_data': top 3, 'stats': dict, 'date_range': dict}).
- **Usage**: Steps chart; includes flat lines for friends with no data.

### calculate_sweat_score(activity, weights_dict)
- **Purpose**: Helper to compute sweat score from activity HR zones.
- **Logic**:
  - If raw_data has 'hrTimeInZone': Extracts times (seconds/60 to minutes) for zones 1-5; t0 = total_duration - sum(t1-t5).
  - Score = sum(t * weight for each zone, defaults 1,2,3,5,8,12).
  - Fallback: calories / 2 if no HR data, else 0.
- **Usage**: Called in get_sweat_score_chart_data for each activity.

### get_sweat_score_chart_data(request)
- **Purpose**: API for cumulative sweat score chart from activities with friends/podium.
- **Handling**: GET; requires auth (401 else).
- **Logic**:
  - Parses range_param for date range.
  - Gets weights_dict from all SweatScoreWeights.
  - Queries GarminActivity (duration >0) for user, aggregates scores by date via calculate_sweat_score, cumulative.
  - Gets friend IDs from accepted Friendships.
  - For each friend: Similar aggregation/cumulative (includes 0).
  - Totals for ranking (user + friends >0), sorts for podium.
  - Stats: user_total, friends_average, user_rank.
- **Response**: JsonResponse similar to steps (user_data, friends_data, podium_data, stats, date_range).
- **Usage**: Sweat score chart; uses HR zones for gamified scoring.

## Notes
- Logging: Logger for __name__; used in get_calories_chart_data.
- Stubs: Some views (e.g., StepsChartDataView) are dummies; implement real logic.
- Auth: Consistent checks; uses get_user_model() as User.
- Signals: Not in views, but post_save in models affects context.
- Templates: Some referenced but not in file list (e.g., social_index.html); create as needed.