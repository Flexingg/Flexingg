# Core Components Documentation

## Overview
The `Flexingg/core/components/` directory uses django-components for reusable UI elements. Each component is a Python class registered with `@component.register`, inheriting from `component.Component`, with `template_name` pointing to `template.html`.

## UI Basics
### Button
- **Description**: A reusable button component.
- **Props**: `text`, `variant`

### Coins
- **Description**: Displays the user's currencies.

### Stat Card
- **Description**: Shows daily quests and stats.

### Equipment Slot
- **Description**: A slot for equipping gear.
- **Props**: `slot`

### Level Card
- **Description**: Displays the user's level and XP progress.
- **Props**: `level`, `current_xp`, `next_level_xp`, `progress_percentage`

### Toast Notification
- **Description**: A notification that appears at the bottom of the screen.

## Charts
### Calories Chart Card
- **Description**: Renders a chart with cumulative calories data.

### Steps Chart Card
- **Description**: Renders a chart with cumulative steps data.

### Sweat Score Chart Card
- **Description**: Renders a chart with the user's sweat score.

### Weight Chart Card
- **Description**: Renders a chart for tracking weight.

## Social/Shop
### Competitions
- **Description**: Shows a list of competitions.

### Item Shop
- **Description**: The in-game shop for purchasing gear.
- **Props**: `items`

### Leaderboard
- **Description**: Renders the leaderboard.
- **Props**: `users`

### Gym Locker
- **Description**: Shows the user's equipped gear.
- **Props**: `slots`

## Navigation/Settings
### Top Navigation
- **Description**: The main header navigation.

### Sidebar Bottom Nav
- **Description**: The desktop sidebar navigation.

### Settings Icon
- **Description**: An icon that links to the settings page.

### Save Logout Buttons
- **Description**: Buttons for saving and logging out in the settings page.
- **Media**: `style.css`, `script.js` (Note: these files are not present in the component's directory)

### PWA Install
- **Description**: A banner for PWA installation.

## Other
### Account Section
- **Description**: The account management section in the settings page.
- **Props**: `profile`

### Integrations Section
- **Description**: The section for managing integrations like Garmin.
- **Media**: `script.js`, `template.html`

### Notifications Section
- **Description**: The section for managing notification settings.
- **Media**: `style.css`, `script.js`, `template.html`

### Profile Section
- **Description**: The section for rendering the profile form.
- **Props**: `profile`, `form`
