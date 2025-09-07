# Core Forms Documentation

## Overview
The `Flexingg/core/forms.py` file defines custom Django forms for authentication, user signup, and profile updates. All forms use pixel-art styled widgets with CSS for a retro gaming aesthetic (e.g., "Press Start 2P" font, dark backgrounds, inset shadows). They extend Django's built-in forms for validation. The custom user model `UserProfile` (from `get_user_model()`) is used where applicable. No explicit Garmin-related forms; profile form includes fitness fields like height and weight.

## LoginForm (extends AuthenticationForm)
- **Purpose**: Handles user login with custom labeling and styling for "Gamertag" (username).
- **Fields**:
  - `username`: CharField, label='Gamertag', widget=TextInput with class 'pixel-input', placeholder='Gamertag', and inline styles (dark bg #1c1c1c, border #444, shadows, font "Press Start 2P", color #E0E0E0, padding 0.5rem, font-size 12px).
  - `password`: CharField (strip=False), widget=PasswordInput with class 'pixel-input', placeholder='Enter your password', same pixel styles.
- **Custom Methods**:
  - `__init__`: Sets label for 'username' to 'Gamertag'.
- **Validation**: Inherits from AuthenticationForm (checks credentials against AUTH_USER_MODEL).
- **Usage**: In SignInView for GET/POST rendering.

## ProfileForm (extends ModelForm)
- **Purpose**: Updates user profile fields, including fitness metrics (height, weight, sex).
- **Meta**:
  - `model`: User (UserProfile).
  - `fields`: ['username', 'email', 'height_ft', 'height_in', 'weight', 'sex'].
  - `widgets`: All with 'pixel-input' or 'pixel-select' classes and consistent pixel styles (dark bg, shadows, font, etc.).
    - `username`: TextInput, placeholder='Update your username'.
    - `email`: EmailInput, placeholder='Update your email'.
    - `height_ft`: NumberInput, placeholder='ft'.
    - `height_in`: NumberInput, placeholder='in'.
    - `weight`: NumberInput, placeholder='lbs'.
    - `sex`: Select with choices from model (male, female, other, prefer_not_to_say), placeholder none.
- **Validation**: ModelForm validation (e.g., email format, numeric constraints); inherits model validators.
- **Usage**: In SettingsView for GET (instance=user) and POST (save updates).

## SignUpForm (extends UserCreationForm)
- **Purpose**: User registration with gamertag (username) and password confirmation.
- **Fields**:
  - `username`: Inherited CharField, widget=TextInput with 'pixel-input', placeholder='Choose your gamer tag', pixel styles.
  - `password1`: CharField (label='Password', strip=False, help_text=None), widget=PasswordInput 'pixel-input', placeholder='Create a secure password', pixel styles.
  - `password2`: CharField (label='Password confirmation', strip=False, help_text=None), widget=PasswordInput 'pixel-input', placeholder='Confirm your password', pixel styles.
- **Meta**:
  - `model`: User (UserProfile).
  - `fields`: ('username', 'password1', 'password2').
- **Validation**: Inherits UserCreationForm (password matching, strength via AUTH_PASSWORD_VALIDATORS); saves new UserProfile.
- **Usage**: In SignUpView for GET/POST; redirects to sign_in on success.

## Common Styling
All widgets share inline CSS for consistency:
- Background: #1c1c1c
- Border: 2px solid #444
- Box-shadow: inset -2px -2px 0 #000, inset 2px 2px 0 #555
- Font: "Press Start 2P", cursive; color #E0E0E0; font-size 12px
- Padding: 0.5rem; width: 100%
- Outline: none; no browser appearances

These forms integrate with views for auth flows and profile management, ensuring pixel-themed UI.