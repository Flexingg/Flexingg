# Health Connect App Documentation

## Overview
The `healthconnect` app is responsible for integrating with the Health Connect Gateway, which allows the application to sync health data from a user's Android device.

## Models

### `HealthConnectData`
- **Description**: Stores the raw data synced from the Health Connect Gateway.
- **Fields**:
  - `profile`: A `ForeignKey` to the `UserProfile` model.
  - `method`: The type of data being stored (e.g., 'steps', 'heartRate').
  - `record_id`: The unique ID for the record from the Health Connect API.
  - `start_time`, `end_time`: Timestamps for the data record.
  - `data`: A `JSONField` containing the raw data from the API.
  - `app_source`: The source application for the data.

## Views

### `connect_healthconnect`
- **Purpose**: Connects a user's account to the Health Connect Gateway.
- **Methods**:
  - `POST`: Takes the user's `hc_username` and `hc_password`, logs in to the gateway, and saves the authentication tokens to the user's profile.

### `sync_healthconnect`
- **Purpose**: Triggers a synchronization of data from the Health Connect Gateway.
- **Methods**:
  - `GET`/`POST`: Ensures the user is authenticated with the gateway, fetches recent data, and saves it to the `HealthConnectData` model.

### `disconnect_healthconnect`
- **Purpose**: Disconnects a user's account from the Health Connect Gateway.
- **Methods**:
  - Clears the Health Connect-related fields from the user's profile.

## URLs
- **`/connect/`**: `connect_healthconnect`
- **`/sync/`**: `sync_healthconnect`
- **`/disconnect/`**: `disconnect_healthconnect`
