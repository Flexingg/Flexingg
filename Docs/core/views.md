# Core Views Documentation

## Overview
The `Flexingg/core/views.py` file contains the central views for the Flexingg application. It uses a mix of Django's class-based views to render templates and handle form submissions.

## Class-Based Views

### HomeView (extends TemplateView)
- **Purpose**: Renders the main dashboard page for authenticated users.
- **Template**: `home.html`.
- **Methods**:
  - `get_context_data(self, **kwargs)`: This method enriches the context with a large amount of user-specific data:
    - **User Profile**: Basic profile information, including `gym_gems`, `cardio_coins`, and `level`.
    - **Garmin & Health Connect Sync**: Initiates asynchronous data sync tasks for Garmin and Health Connect based on a debounce timer.
    - **Today's Stats**: Calculates and adds today's total calories burned, steps taken, lifting volume (in thousands), and consumed calories (from Health Connect) to the context.

### SignUpView (extends View)
- **Purpose**: Handles user registration.
- **Template**: `sign_up.html`.
- **Form**: `SignUpForm`.
- **Methods**:
  - `get`: Renders the registration form. Redirects to the home page if the user is already authenticated.
  - `post`: Processes the submitted registration form. On success, it saves the new user and redirects to the sign-in page.

### SignInView (extends View)
- **Purpose**: Handles user authentication.
- **Template**: `sign_in.html`.
- **Form**: `LoginForm`.
- **Methods**:
  - `get`: Renders the login form. Redirects to the home page if the user is already authenticated.
  - `post`: Authenticates the user's credentials. On success, it logs the user in and redirects to the home page.

### SignOutView (extends View)
- **Purpose**: Logs the current user out.
- **Methods**:
  - `get`: Logs the user out and redirects to the sign-in page.

### SettingsView (extends View)
- **Purpose**: Allows users to update their profile information.
- **Template**: `settings.html`.
- **Form**: `ProfileForm`.
- **Methods**:
  - `get`: Renders the profile form, pre-filled with the current user's data.
  - `post`: Processes the submitted profile form, including the optional avatar image upload. On success, it saves the changes and reloads the page with a success message.

### LiftosaurConnectView (extends View)
- **Purpose**: Connects a user's Liftosaur account by saving their Liftosaur User ID.
- **Methods**:
  - `post`: Retrieves the `liftosaur_user_id` from the POST request, saves it to the user's profile, and redirects back to the settings page.

### LiftosaurDisconnectView (extends View)
- **Purpose**: Disconnects a user's Liftosaur account.
- **Methods**:
  - `post`: Removes the `liftosaur_user_id` from the user's profile and redirects back to the settings page.

### ComingSoonView (extends TemplateView)
- **Purpose**: Renders a "coming soon" page for features that are not yet implemented.
- **Template**: `comingsoon.html`.

### OfflineView (extends TemplateView)
- **Purpose**: Renders a page to be displayed when the user is offline (for PWA functionality).
- **Template**: `offline.html`.

### ProfileView (extends LoginRequiredMixin, TemplateView)
- **Purpose**: Renders the user's profile page.
- **Template**: `profile.html`.

### ServiceWorkerView (extends View)
- **Purpose**: Serves the `sw.js` service worker file for the PWA.
- **Methods**:
  - `get`: Reads the service worker file from the static files and returns it with the correct content type and headers.

### GymView (extends TemplateView)
- **Purpose**: Renders the "Gym" page.
- **Template**: `gym.html`.

### LockerRoomView (extends TemplateView)
- **Purpose**: Renders the "Locker Room" page where users can manage their gear.
- **Template**: `locker_room.html`.

### ShopView (extends TemplateView)
- **Purpose**: Renders the in-game shop page.
- **Template**: `shop.html`.
