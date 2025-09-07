# Root Files Documentation

## Overview
The root directory contains standard Django project files for management, deployment, dependencies, and configuration. Some files like manage.py, asgi.py, wsgi.py are standard and not readable due to path issues, but described based on Django conventions. Others are provided. These enable development, deployment (Docker), and project setup.

## manage.py
- **Description**: Standard Django management script for commands like runserver, migrate, createsuperuser.
- **Usage**: `python manage.py runserver` to start dev server; `python manage.py migrate` for DB changes; `python manage.py collectstatic` for static files.
- **Location**: Root (`Flexingg/manage.py`).
- **Standard Content**: Calls django.core.management.execute_from_command_line with settings module.

## Flexingg/asgi.py
- **Description**: ASGI configuration for async deployment (e.g., with Daphne/Uvicorn). Standard for Django 3+.
- **Usage**: For async features like channels/websockets; run with `daphne Flexingg.asgi:application`.
- **Standard Content**:
  ```
  import os
  from django.core.asgi import get_asgi_application
  os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flexingg.settings')
  application = get_asgi_application()
  ```
- **Location**: `Flexingg/Flexingg/asgi.py`.

## Flexingg/wsgi.py
- **Description**: WSGI configuration for traditional deployment (e.g., Gunicorn).
- **Usage**: Run with `gunicorn Flexingg.wsgi:application`; used in Dockerfile.
- **Standard Content**:
  ```
  import os
  from django.core.wsgi import get_wsgi_application
  os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flexingg.settings')
  application = get_wsgi_application()
  ```
- **Location**: `Flexingg/Flexingg/wsgi.py`.

## docker-compose.yml
- **Description**: Docker Compose configuration for services: db (PostgreSQL 15), web (Django app).
- **Key Sections**:
  - **db**: Postgres image, volumes for data, env vars for DB, port 5432.
  - **web**: Builds from Dockerfile, command for migrations and gunicorn on port 8000, volumes for code, env vars for DB, depends on db, port 1234:8000.
  - **volumes**: postgres_data for persistence.
- **Usage**: `docker-compose up --build` to start; `docker-compose down` to stop. Auto-runs migrations.
- **Location**: Root.

## Dockerfile
- **Description**: Docker image for the Django app using Python 3.12-slim.
- **Steps**:
  - WORKDIR /app.
  - COPY requirements.txt; RUN pip install.
  - COPY . .
  - EXPOSE 8000.
  - CMD gunicorn on port 8000.
- **Usage**: Built by docker-compose; for production deployment.
- **Location**: Root.

## requirements.txt
- **Description**: Python dependencies for the project.
- **List**:
  - django==5.2.6
  - psycopg2-binary==2.9.10 (PostgreSQL adapter)
  - gunicorn==21.2.0 (WSGI server)
  - django-components==0.141.4 (UI components)
  - django-pwa==2.0.1 (PWA support)
  - whitenoise==6.9.0 (static files serving)
  - garth==0.5.17 (Garmin API client)
  - garminconnect>=0.1.30 (Garmin Connect)
  - python-dotenv==1.0.1 (env vars)
- **Usage**: `pip install -r requirements.txt` to install; pinned for reproducibility.

## .gitignore
- **Description**: Git ignore patterns for Python/Django/Docker.
- **Key Entries**:
  - Env: .env, .env.*, *.env
  - Python: __pycache__/, *.py[cod], venv/
  - Django: *.log, local_settings.py, db.sqlite3, media/, staticfiles/
  - Backup: backups/
  - Misc: .kilocodemodes, .readthedocs.yml, playwright.config.ts, .vscode/, .idea/, .kilocode/, .cursor/"venv/"
- **Usage**: Prevents committing secrets, builds, local DB.

## LICENSE
- **Description**: Apache License 2.0 for the project.
- **Key Terms**: Grants perpetual, non-exclusive license for use/mod/distribution; patent grant; no warranty; attribution required.
- **Usage**: Legal terms for open-source use; include in derivatives.
- **Location**: Root.

## README.md
- **Description**: Project setup guide.
- **Sections**:
  - Local Development: venv, pip install, env vars, migrate, runserver.
  - Docker Setup: docker-compose up/down.
  - Project Structure: Flexingg/, core/, requirements.txt, Dockerfile, docker-compose.yml.
  - Database: PostgreSQL with creds.
- **Usage**: Instructions for new developers; update for changes.

These files form the project foundation for development and deployment.