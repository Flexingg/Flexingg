# Garmin Connect App Documentation

## Overview
The `garminconnect` app handles all interactions with the Garmin Connect API. This includes user authentication, data synchronization for steps and activities, and managing Garmin-specific data models.

## Models

### `Garmin_Auth`
- **Description**: Stores the OAuth tokens and other authentication data required to make requests to the Garmin Connect API.
- **Fields**:
  - `user`: A `OneToOneField` to the `UserProfile` model.
  - `oauth_token`, `oauth_token_secret`, `access_token`, `refresh_token`, etc.: Fields to store the various tokens and metadata associated with the OAuth process.
  - `last_sync`, `last_sync_attempt`: Timestamps to track the status of data synchronization.

### `GarminCredentials`
- **Description**: An alternative model for storing Garmin Connect authentication details.
- **Fields**:
  - `user`: A `OneToOneField` to the `UserProfile` model.
  - `garmin_email`: The user's Garmin Connect email address.
  - `session_data`: A `JSONField` to store session data.

### `GarminDailySteps`
- **Description**: Stores the daily step count for a user, synced from Garmin Connect.
- **Fields**:
  - `user`: A `ForeignKey` to the `UserProfile` model.
  - `date`: The date for which the steps were recorded.
  - `steps`: The total number of steps for that day.

### `GarminActivity`
- **Description**: Stores detailed information about a specific activity (e.g., a run, a bike ride) synced from Garmin Connect.
- **Fields**:
  - `user`: A `ForeignKey` to the `UserProfile` model.
  - `activity_id`: The unique ID for the activity from Garmin.
  - `name`, `activity_type`, `start_time_utc`, `duration_seconds`, `distance_meters`, `calories`, `average_hr`, `max_hr`: Fields that store the details of the activity.
  - `raw_data`: A `JSONField` containing the complete raw data from the Garmin API.

## Views

### `ConnectGarminView`
- **Purpose**: Handles the process of linking a user's Garmin Connect account.
- **Methods**:
  - `get`: Renders the settings page with the Garmin connection form.
  - `post`: Processes the submitted form, attempts to authenticate with the Garmin API using the provided credentials, and if successful, creates a `Garmin_Auth` record for the user.

### `DisconnectGarminView`
- **Purpose**: Disconnects a user's Garmin Connect account.
- **Methods**:
  - `post`: Deletes the `Garmin_Auth` record for the current user.

### `SyncGarminView`
- **Purpose**: Triggers a manual synchronization of Garmin data.
- **Methods**:
  - `post`: Initiates the `perform_garmin_sync_steps` and `perform_garmin_sync_activities` functions to sync the user's data.

### `BackgroundGarminSyncView`
- **Purpose**: An API endpoint for triggering a background synchronization of Garmin data.
- **Methods**:
  - `post`: Checks for a cooldown period to prevent frequent syncs, and if the cooldown has passed, it initiates the sync tasks.

## URLs
- **`/sync/`**: `SyncGarminView`
- **`/background-sync/`**: `BackgroundGarminSyncView`
- **`/connect/`**: `ConnectGarminView`
- **`/disconnect/`**: `DisconnectGarminView`
