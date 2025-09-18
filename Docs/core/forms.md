# Core Forms Documentation

## Overview
The `Flexingg/core/forms.py` file defines custom Django forms for authentication, user signup, and profile updates. All forms use pixel-art styled widgets with CSS for a retro gaming aesthetic.

## LoginForm (extends AuthenticationForm)
- **Purpose**: Handles user login with custom styling for "Gamertag" (username).
- **Fields**:
  - `username`: `CharField` with a label of 'Gamertag'.
  - `password`: `CharField` with a `PasswordInput` widget.
- **Styling**: Both fields are styled with the `pixel-input` class, which gives them a distinctive pixel-art look.

## ProfileForm (extends ModelForm)
- **Purpose**: Allows users to update their profile information.
- **Model**: `UserProfile`
- **Fields**:
  - `username`: `CharField`
  - `avatar`: `ImageField` with a `FileInput` widget.
  - `email`: `EmailField`
  - `height_ft`, `height_in`: `NumberInput` for height in feet and inches.
  - `weight`: `NumberInput` for weight in pounds.
  - `sex`: `Select` field for the user's sex.
  - `sync_debounce_minutes`: `NumberInput` to set the debounce time for Garmin sync.
- **Styling**: All fields are styled with either the `pixel-input` or `pixel-select` class.

## SignUpForm (extends UserCreationForm)
- **Purpose**: Handles new user registration.
- **Model**: `UserProfile`
- **Fields**:
  - `username`: `CharField`
  - `password1`: `CharField` for the user's password.
  - `password2`: `CharField` for password confirmation.
- **Styling**: All fields are styled with the `pixel-input` class.
