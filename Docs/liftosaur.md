# Liftosaur App Documentation

## Overview
The `liftosaur` app is responsible for integrating with Liftosaur, a workout tracking application. It allows users to import their workout data from a JSON file and sync it with their Flexingg profile.

## Models

### `Exercise`
- **Description**: Represents a specific type of exercise (e.g., 'Squat (Barbell)').

### `UserExerciseStat`
- **Description**: Stores user-specific stats for an exercise, such as their 1-rep max.

### `Workout`
- **Description**: Represents a single workout session.

### `WorkoutExercise`
- **Description**: An exercise performed during a workout session.

### `WorkoutSet`
- **Description**: A single set within a `WorkoutExercise`.

### `BodyMeasurement`
- **Description**: Stores user body measurements over time.

### `Program`
- **Description**: Stores a user's Liftosaur program data.

## Views

### `sync_workout_data`
- **Purpose**: Triggers an asynchronous sync of Liftosaur data for the logged-in user.
- **Methods**:
  - `POST`: Initiates a Celery task to fetch and process the user's Liftosaur data.

### `import_data`
- **Purpose**: Allows users to upload and import their Liftosaur data from a JSON file.
- **Methods**:
  - `POST`: Takes a JSON file, and if it's valid, it initiates a Celery task to process the data.

### `SaveLiftosaurTokenView`
- **Purpose**: Saves a user's Liftosaur session token to their profile.
- **Methods**:
  - `POST`: Takes a session token, saves it to the user's profile, and attempts to fetch the user's Liftosaur ID.

## URLs
- **`/sync/`**: `sync_workout_data`
- **`/import/`**: `import_data`
- **`/save-token/`**: `SaveLiftosaurTokenView`
