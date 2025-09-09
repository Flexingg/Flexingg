# Flexingg Django Project

## Partner Repo (Enables Health Connect Sync on Android Devices)
https://github.com/Flexingg/Flexingg-Sync

## Local Development Setup

1. Ensure Python 3.12 is installed.
2. Create and activate the virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate.bat  # On Windows
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set environment variables for PostgreSQL (or use a local DB):
   ```
   set DB_NAME=flexingg_db
   set DB_USER=flexingg_user
   set DB_PASSWORD=flexingg_pass
   set DB_HOST=localhost
   set DB_PORT=5432
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

## Docker Setup

1. Ensure Docker is installed and running.
2. Build and start the services:
   ```
   docker-compose up --build
   ```
   This will start PostgreSQL and the Django app, run migrations automatically, and serve on http://localhost:8000.

3. To stop:
   ```
   docker-compose down
   ```

## Project Structure

- `Flexingg/`: The Django project directory.
- `core/`: Initial Django app.
- `requirements.txt`: Python dependencies.
- `Dockerfile`: For building the Django container.
- `docker-compose.yml`: For orchestrating services.

## Database

Uses PostgreSQL 15. Credentials are set in docker-compose.yml for Docker, or via environment variables for local.

For production, update SECRET_KEY, ALLOWED_HOSTS, and use secure DB credentials.