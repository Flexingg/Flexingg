# Flexingg - A Gamified Fitness PWA

Flexingg is a Progressive Web App (PWA) built with Django, designed as a gamified fitness tracking platform. It integrates with Garmin Connect for syncing activity data (steps, calories, heart rate zones) and calculates custom metrics like "Sweat Score" based on configurable weights. Users can track progress, earn virtual currencies (Gym Gems, Cardio Coins), level up, equip gear for stat bonuses, form friendships for social features, and compete on leaderboards. The app emphasizes pixel-art aesthetics with retro gaming elements, including stats like strength (str_stat), endurance (end_stat), etc.

## Documentation

For a complete and detailed documentation of the entire codebase, including models, views, components, and more, please see the **[Flexingg Documentation](Docs/index.md)**.

## Self-Hosting with Docker

You can easily self-host Flexingg using the provided Docker Compose setup.

### Prerequisites
- Docker and Docker Compose installed on your machine.

### Setup Instructions

1.  **Create an environment file:**
    Create a file named `stack.env` in the root of the project. This file will hold all the necessary environment variables.

2.  **Populate `stack.env`:**
    Add the following variables to your `stack.env` file. Replace the placeholder values with your own secure values.

    ```bash
    # PostgreSQL settings
    POSTGRES_DB=flexingg_db
    POSTGRES_USER=flexingg_user
    POSTGRES_PASSWORD=your_super_secure_password

    # Django database settings (must match PostgreSQL settings)
    DB_NAME=flexingg_db
    DB_USER=flexingg_user
    DB_PW=your_super_secure_password
    DB_HOST=db
    DB_PORT=5432

    # Django settings
    SECRET_KEY=your_django_secret_key_here
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your_domain.com
    ```

3.  **Build and run the containers:**
    Open a terminal in the project root and run:
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker images for the web application and start all the services (web, database, redis, celery, celery-beat). The application will be accessible at `http://localhost:1234`.

4.  **Stopping the application:**
    To stop the running containers, press `Ctrl+C` in the terminal where `docker-compose` is running, or run the following command from the project root in another terminal:
    ```bash
    docker-compose down
    ```

## Local Development Setup

For those who prefer to run the application locally without Docker.

1. Ensure Python 3.12 is installed.
2. Create and activate the virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate.bat  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set environment variables for PostgreSQL (or use a local DB):
   ```
   export DB_NAME=flexingg_db
   export DB_USER=flexingg_user
   export DB_PASSWORD=flexingg_pass
   export DB_HOST=localhost
   export DB_PORT=5432
   ```
5. Run migrations (assuming local PostgreSQL is running):
   ```
   cd Flexingg
   python manage.py migrate
   ```
6. Start the development server:
   ```
   python manage.py runserver
   ```
   Access the app at http://localhost:8000.
