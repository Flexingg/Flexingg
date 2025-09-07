# Core Components Documentation

## Overview
The `Flexingg/core/components/` directory uses django-components for reusable UI elements. Each component is a Python class registered with `@component.register`, inheriting from `component.Component`, with `template_name` pointing to `template.html`. Most have minimal `get_context_data` (super or basic context like is_authenticated). Props are passed via kwargs in usage. Templates handle rendering; some have media (css/js). Grouped by category for efficiency: UI Basics, Charts, Social/Shop, Navigation/Settings, Other. Usage: `{% component "name" prop=value %}{% endcomponent %}` in templates.

## UI Basics
### Button
- **Python Class**: Button(Component)
  - Inheritance: component.Component
  - Methods: get_context_data(**kwargs) – Returns super.
  - Props: text, variant (e.g., "cyan", "red").
  - Template: button/template.html
  - Usage: `{% component "button" text="START CARDIO" variant="cyan" %}` – Renders styled pixel button for actions.

### Coins
- **Python Class**: Coins(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None explicit; uses request.user.gym_gems.
  - Template: coins/template.html
  - Usage: `{% component "coins" %}` – Displays user currencies (gym_gems) in header.

### Stat Card
- **Python Class**: StatCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None; uses user stats.
  - Template: stat_card/template.html
  - Usage: `{% component "stat_card" %}` – Shows daily quests/stats card.

### Equipment Slot
- **Python Class**: EquipmentSlot(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: slot (e.g., "head").
  - Template: equipment_slot/template.html
  - Usage: For equipping gear in slots.

### Level Card
- **Python Class**: LevelCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Adds 'is_authenticated' from request.user.
  - Props: level, current_xp, next_level_xp, progress_percentage.
  - Template: level_card/template.html
  - Usage: `{% component "level_card" level=12 current_xp=750 next_level_xp=1000 progress_percentage=75 %}` – Displays user level and XP progress.

## Charts
### Calories Chart Card
- **Python Class**: CaloriesChartCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None; fetches from API via JS.
  - Template: calories_chart_card/template.html
  - Usage: `{% component "calories_chart_card" %}` – Renders chart with cumulative calories data.

### Steps Chart Card
- **Python Class**: StepsChartCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: steps_chart_card/template.html
  - Usage: `{% component "steps_chart_card" %}` – Steps chart with friends/podium.

### Sweat Score Chart Card
- **Python Class**: SweatScoreChartCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: sweat_score_chart_card/template.html
  - Usage: `{% component "sweat_score_chart_card" %}` – Sweat score based on HR zones.

### Weight Chart Card
- **Python Class**: WeightChartCard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: weight_chart_card/template.html
  - Usage: `{% component "weight_chart_card" %}` – Weight tracking chart (stub).

## Social/Shop
### Competitions
- **Python Class**: Competitions(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: competitions/template.html
  - Usage: `{% component "competitions" %}` – Shows competitions list.

### Item Shop
- **Python Class**: ItemShop(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: items (list of dicts with name, description, price).
  - Template: item_shop/template.html
  - Usage: `{% component "item_shop" items="[{ 'name': 'Daily Deal', 'description': 'New gear just dropped.', 'price': 100 }]" %}` – Shop for gear.

### Leaderboard
- **Python Class**: Leaderboard(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: users (list of dicts with rank, name, score).
  - Template: leaderboard/template.html
  - Usage: `{% component "leaderboard" users="[{ 'rank': 1, 'name': 'GIGA', 'score': 5000 }..." %}` – Renders leaderboard.

### Gym Locker
- **Python Class**: GymLocker(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: slots (list of dicts with name, item).
  - Template: gym_locker/template.html
  - Usage: `{% component "gym_locker" slots="[{name': 'Common', 'item': null}, ...]" %}` – Shows equipped gear.

## Navigation/Settings
### Top Navigation
- **Python Class**: TopNavigation(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: top_navigation/template.html
  - Usage: `{% component "top_navigation" %}` – Header navigation.

### Sidebar Bottom Nav
- **Python Class**: SidebarBottomNav(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: sidebar_bottom_nav/template.html
  - Usage: `{% component "sidebar_bottom_nav" %}` – Desktop sidebar.

### Settings Icon
- **Python Class**: SettingsIcon(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Super.
  - Props: None.
  - Template: settings_icon/template.html
  - Usage: `{% component "settings_icon" %}` – Icon for settings.

### Save Logout Buttons
- **Python Class**: SaveLogoutButtons(Component)
  - Inheritance: component.Component
  - Media: css/style.css, js/script.js
  - Methods: None beyond default.
  - Props: None.
  - Template: save_logout_buttons/template.html
  - Usage: `{% component "save_logout_buttons" %}` – Buttons for save/logout in settings.

### PWA Install
- **Python Class**: PwaInstall(Component)
  - Inheritance: component.Component
  - Methods: get_context_data – Adds 'show_pwa_install': True.
  - Props: None.
  - Template: pwa_install/template.html
  - Usage: `{% component "pwa_install" %}` – Banner for PWA installation.

## Other
### Account Section
- **Python Class**: AccountSection(Component)
  - Inheritance: component.Component
  - Media: None.
  - Methods: None.
  - Props: profile.
  - Template: account_section/template.html
  - Usage: `{% component "account_section" profile=profile %}` – Account management.

### Integrations Section
- **Python Class**: IntegrationsSection(Component)
  - Inheritance: component.Component
  - Media: css/style.css, js/script.js
  - Methods: None.
  - Props: None.
  - Template: integrations_section/template.html
  - Usage: `{% component "integrations_section" %}` – For Garmin linking.

### Notifications Section
- **Python Class**: NotificationsSection(Component)
  - Inheritance: component.Component
  - Media: css/style.css, js/script.js
  - Methods: None.
  - Props: None.
  - Template: notifications_section/template.html
  - Usage: `{% component "notifications_section" %}` – Notification settings.

### Profile Section
- **Python Class**: ProfileSection(Component)
  - Inheritance: component.Component
  - Media: css/style.css, js/script.js
  - Methods: None.
  - Props: profile, form.
  - Template: profile_section/template.html
  - Usage: `{% component "profile_section" profile=profile form=form %}` – Profile form rendering.

## Notes
- All components are minimal; logic in templates/JS.
- Props passed as kwargs; access via context in template.
- Media for some (css/js) loaded via {{ component.media.css }} in base.html.
- Usage in home.html, settings.html, etc.
- For full implementation, add props/methods as needed.