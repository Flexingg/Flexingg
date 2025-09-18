FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=Flexingg.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Add entrypoint script to handle container startup and cleanup
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Copy and set up health check script
COPY docker-healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

# Create directories
RUN mkdir -p /app/staticfiles /app/media /app/celerybeat

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Create media directory and set permissions
RUN mkdir -p /app/media/images/foods/main /app/media/images/foods/nutrition \
    && chmod -R 777 /app/media

# Create directory for Celery beat
RUN mkdir -p /app/celerybeat && \
    chown -R appuser:appuser /app/celerybeat

# Set environment variables for Redis connection
ENV REDIS_URL=redis://redis:6379/0

# Set the health check command
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["docker-healthcheck.sh"]