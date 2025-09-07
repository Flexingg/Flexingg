# Flexingg Documentation Index

Welcome to the comprehensive documentation for the Flexingg fitness PWA project. This index provides links to all key sections covering the codebase structure, configuration, and components.

## Project Overview
- [Overview](overview.md): High-level project structure, purpose, architecture, and key directories.

## Root Files
- [Root Files](root-files.md): Documentation of manage.py, asgi.py, wsgi.py, docker-compose.yml, Dockerfile, requirements.txt, .gitignore, LICENSE, README.md.

## Core App
### Configuration
- [Settings](settings.md): Django settings.py configuration (apps, middleware, database, static files, PWA).

### Admin
- [Admin](core/admin.md): Admin.py for model registrations.

### Forms
- [Forms](core/forms.md): LoginForm, ProfileForm, SignUpForm details and validation.

### Models
- [Models](core/models.md): All models (UserProfile, ColorPreferences, etc.), fields, relationships, methods, signals (includes Mermaid ER diagram).

### Views
- [Views](core/views.md): Class-based views and API functions for pages and chart data.

### URLs
- [URLs](core/urls.md): URL patterns and mapped views.

### Template Tags
- [Template Tags](core/templatetags.md): Custom filters from custom_filters.py, filters.py, fitness_filters.py, math_filters.py with examples.

### Templates
- [Templates](core/templates.md): Overviews of base.html, home.html, offline.html, settings.html, sign_in.html, sign_up.html.

### Components
- [Components](core/components.md): Reusable UI components grouped by category (UI Basics, Charts, Social/Shop, Navigation/Settings, Other).

### Migrations
- [Migrations](core/migrations.md): Summary of schema changes from 0001_initial to 0006_userprofile_height_ft...

## Static Files
- [Static Files](static.md): PWA manifest.json, sw.js, icons, screenshots, app structure.

## Additional Resources
- Review the [Mermaid diagrams](core/models.md#model-relationships-diagram-mermaid) in models.md for relationships.
- For deployment, see root-files.md Docker sections.

This documentation is generated systematically to cover the entire codebase. Update as the project evolves.