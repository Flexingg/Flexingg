# Flexingg Project Overview

## Project Purpose
Flexingg is a Progressive Web App (PWA) built with Django, designed as a gamified fitness tracking platform. It integrates with Garmin Connect for syncing activity data (steps, calories, heart rate zones) and calculates custom metrics like "Sweat Score" based on configurable weights. Users can track progress, earn virtual currencies (Gym Gems, Cardio Coins), level up, equip gear for stat bonuses, form friendships for social features, and compete on leaderboards. The app emphasizes pixel-art aesthetics with retro gaming elements, including stats like strength (str_stat), endurance (end_stat), etc.

Key features:
- User authentication and profile management (custom UserProfile model extending AbstractUser).
- Garmin API integration for daily steps, activities, and auth.
- Component-based UI using django-components for reusable elements (e.g., charts, notifications, item shop).
- Social interactions via Friendship model.
- PWA support for offline functionality and installability.
- Chart data APIs for visualizing cumulative metrics (steps, calories, sweat score) with friend comparisons and podium rankings.

## High-Level Architecture
- **Backend**: Django 5.2.6 with a single custom app `core` handling models, views, forms, and components. Uses SQLite for development (configurable via settings). ASGI/WSGI for deployment.
- **Frontend**: Server-rendered templates with django-components for modularity. Custom template tags/filters for fitness calculations. Static files include PWA manifest, service worker, icons, and screenshots.
- **Data Flow**: Views handle auth, profile updates, and API endpoints for chart data. Models store user data, Garmin syncs, and relationships. Migrations manage schema evolution.
- **Integrations**: Garmin OAuth for auth and data sync; potential for Docker deployment.
- **Deployment**: Dockerized with compose; Whitenoise for static files; PWA for mobile/web.

## Key Directories and Files
- **Root**:
  - `manage.py`: Django management script.
  - `Flexingg/`: Project package with settings, urls, asgi/wsgi.
  - `core/`: Main app with models (UserProfile, GarminActivity, etc.), views (HomeView, chart APIs), forms, admin, templatetags, templates, components, migrations.
  - `static/`: PWA assets (manifest.json, sw.js, icons, screenshots).
  - `requirements.txt`: Dependencies (Django, django-components, pwa, etc.).
  - Docker files for containerization.

- **core/models.py**: Core data models including custom user, Garmin entities, Friendship, Gear, SweatScoreWeights.
- **core/views.py**: Class-based views for auth/pages and function-based APIs for charts (get_steps_chart_data, etc.).
- **core/components/**: Reusable UI components (e.g., calories_chart_card.py + template.html) for dashboard elements.
- **core/templates/**: Base templates like base.html, home.html; auth pages.
- **core/templatetags/**: Custom filters for math, fitness calculations.
- **migrations/**: Schema changes from initial user model to height/weight additions.

## Technologies and Dependencies
- Django, django-components, pwa, whitenoise.
- Custom signals for post-save actions (e.g., creating ColorPreferences).
- JSONFields for raw Garmin data.
- UUID primaries for some models.

This documentation covers the entire codebase systematically. See linked files for details.