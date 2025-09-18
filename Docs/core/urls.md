# Core URLs Documentation

## Overview
The `Flexingg/core/urls.py` file defines the URL configuration for the `core` app. It uses the `app_name` `fitness` for namespacing. The `urlpatterns` list maps URL paths to their corresponding class-based views.

## URL Patterns

- **Path**: `''`
  - **Name**: `home`
  - **View**: `HomeView`
  - **Description**: The main dashboard/home page of the application.

- **Path**: `'sign-up/'`
  - **Name**: `sign_up`
  - **View**: `SignUpView`
  - **Description**: The user registration page.

- **Path**: `'sign-in/'`
  - **Name**: `sign_in`
  - **View**: `SignInView`
  - **Description**: The user login page.

- **Path**: `'sign-out/'`
  - **Name**: `sign_out`
  - **View**: `SignOutView`
  - **Description**: The user logout endpoint.

- **Path**: `'settings/'`
  - **Name**: `settings`
  - **View**: `SettingsView`
  - **Description**: The user profile settings page.

- **Path**: `'connect-liftosaur/'`
  - **Name**: `connect_liftosaur`
  - **View**: `LiftosaurConnectView`
  - **Description**: Endpoint for connecting a Liftosaur account.

- **Path**: `'disconnect-liftosaur/'`
  - **Name**: `disconnect_liftosaur`
  - **View**: `LiftosaurDisconnectView`
  - **Description**: Endpoint for disconnecting a Liftosaur account.

- **Path**: `'comingsoon/'`
  - **Name**: `comingsoon`
  - **View**: `ComingSoonView`
  - **Description**: A placeholder page for features not yet implemented.

- **Path**: `'offline/'`
  - **Name**: `offline`
  - **View**: `OfflineView`
  - **Description**: The page displayed when the user is offline (for PWA functionality).

- **Path**: `'sw.js'`
  - **Name**: `service_worker`
  - **View**: `ServiceWorkerView`
  - **Description**: Serves the service worker file for the PWA.

- **Path**: `'profile/'`
  - **Name**: `profile`
  - **View**: `ProfileView`
  - **Description**: The user's profile page.

- **Path**: `'gym/'`
  - **Name**: `gym`
  - **View**: `GymView`
  - **Description**: The "Gym" page.

- **Path**: `'locker_room/'`
  - **Name**: `locker_room`
  - **View**: `LockerRoomView`
  - **Description**: The "Locker Room" page for managing gear.

- **Path**: `'shop/'`
  - **Name**: `shop`
  - **View**: `ShopView`
  - **Description**: The in-game shop page.
