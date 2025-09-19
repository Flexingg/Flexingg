# Data Normalization and Synchronization Plan

This document outlines the plan to create a unified data normalization and synchronization system for integrating data from Garmin Connect, Health Connect, and Liftosaur.

## 1. Database Model Changes

The first step is to refactor the database models to support the new synchronization logic.

### 1.1. `ConnectedService` Model
Create a new model to store authentication tokens and other details for each service a user connects. This will centralize connection information.

-   `user`: ForeignKey to `UserProfile`
-   `service_name`: CharField (e.g., 'garmin', 'healthconnect', 'liftosaur')
-   `auth_data`: JSONField to store tokens and other auth-related data.

### 1.2. `DataPriority` Model
Create a model to store the user's preferred data source for each data type.

-   `user`: ForeignKey to `UserProfile`
-   `data_type`: CharField (e.g., 'workout', 'sleep', 'steps')
-   `source`: CharField (e.g., 'garmin', 'healthconnect', 'liftosaur')
-   `rank`: IntegerField for priority (1 is the highest).

### 1.3. Unified Data Models
Create new, simplified models for each data type. These will replace the service-specific models.

-   **`Workout` model:**
    -   `user`: ForeignKey to `UserProfile`
    -   `source`: CharField (e.g., 'garmin', 'liftosaur')
    -   `source_id`: CharField (unique ID from the source service)
    -   `start_time`: DateTimeField
    -   `end_time`: DateTimeField
    -   `data`: JSONField to store the normalized workout data.
-   **`Sleep` model:**
    -   `user`: ForeignKey to `UserProfile`
    -   `source`: CharField
    -   `source_id`: CharField
    -   `start_time`: DateTimeField
    -   `end_time`: DateTimeField
    -   `data`: JSONField
-   **`Steps` model:**
    -   `user`: ForeignKey to `UserProfile`
    -   `source`: CharField
    -   `source_id`: CharField
    -   `date`: DateField
    -   `steps`: IntegerField

These new models will likely be created in the `core` app (`Flexingg/core/models.py`). The old models in `garminconnect`, `healthconnect`, and `liftosaur` will be deprecated and eventually removed.

## 2. Manual Synchronization Logic

Implement the user-facing trigger for the data sync.

### 2.1. Sync Button and View
-   Add a "Sync My Data" button to the user settings page (`settings.html`).
-   Create a new Django view `sync_data_view` in `Flexingg/core/views.py`.
-   This view will trigger a Celery task to perform the sync in the background for the logged-in user.
-   Add a URL for this view in `Flexingg/core/urls.py`.

### 2.2. Celery Task
-   Create a new Celery task `sync_user_data(user_id)` in `Flexingg/core/tasks.py`.
-   This task will contain the core synchronization logic.

## 3. The "Overwrite" Synchronization Process

This is the core logic that will run inside the `sync_user_data` Celery task.

### 3.1. Get User Priorities
-   Fetch the user's data source priorities from the `DataPriority` model.

### 3.2. Delete Old Data
-   For each data type (workouts, sleep, etc.), delete all existing records for the user within the last 30 days from the new unified models.

### 3.3. Fetch Fresh Data
-   Fetch the last 30 days of data from all of the user's connected services using the credentials stored in the `ConnectedService` model.

### 3.4. Process and Save in Priority Order
-   Create an in-memory set, `filled_dates`, to track which dates have already been filled by a higher-priority source for a given data type.
-   Loop through the data sources in their priority order (rank 1, then rank 2, etc.).
-   For each data item (e.g., a workout):
    -   Normalize the data into the format for the unified models.
    -   Check if the date of the item is already in `filled_dates`.
    -   If the date is **not** in `filled_dates`:
        -   Save the normalized data to the appropriate unified model using `update_or_create` with `user`, `source`, and `source_id`.
        -   Add the date to `filled_dates`.
    -   If the date **is** in `filled_dates`, discard the item.

## 4. Testing

-   Create unit tests for the normalization functions.
-   Manually test the "Sync My Data" button and verify that the data is correctly fetched, prioritized, and saved in the new unified models.
-   Verify that old data is correctly deleted.

## 5. Code Cleanup

-   Once the new system is stable, the old data models in the service-specific apps (`garminconnect`, `healthconnect`, `liftosaur`) can be removed, along with their associated views and tasks that are no longer needed. This might be a separate follow-up task.
