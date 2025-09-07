# Core Models Documentation

## Overview
The `Flexingg/core/models.py` file defines the database models for the fitness app. It extends Django's AbstractUser for custom user profiles and includes models for themes, social features, gear, steps tracking, Garmin integration, and sweat score calculations. Relationships use ForeignKey, OneToOneField, and ManyToManyField. UUIDs for primaries in some models. A post_save signal auto-creates ColorPreferences for new users. All models support the gamified fitness theme with stats, currencies, and integrations.

## UserProfile (extends AbstractUser)
- **Description**: Custom user model for profiles with fitness stats, currencies, level/XP system, physical attributes, and social relations.
- **Fields**:
  - `avatar`: CharField(max_length=255, blank=True) – For user avatar (binary upload planned).
  - `gym_gems`: DecimalField(max_digits=10, decimal_places=2, default=0.00) – Currency for store.
  - `cardio_coins`: DecimalField(max_digits=10, decimal_places=2, default=0.00) – Currency for upgrades/premium.
  - `str_stat`, `end_stat`, `fcs_stat`, `rcv_stat`, `lck_stat`: IntegerField(default=0) – Stat bonuses (strength, endurance, etc.).
  - `level`: IntegerField(default=1) – User level from XP.
  - `xp`: IntegerField(default=0) – Experience points.
  - `height_ft`, `height_in`: IntegerField(null=True, blank=True, help_text="Height in feet/inches").
  - `weight`: DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in lbs.").
  - `sex`: CharField(max_length=20, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say')], null=True, blank=True, help_text='Gender').
- **Relationships**:
  - `groups`: ManyToManyField to auth.Group (related_name='profile_groups').
  - `user_permissions`: ManyToManyField to auth.Permission (related_name='profile_users').
  - `following`: ManyToManyField to self (symmetrical=False, related_name='followers', blank=True) – For following users.
  - `blocking`: ManyToManyField to self (symmetrical=False, related_name='blockers', blank=True) – For blocking users.
  - Related: OneToOne to ColorPreferences (theme_colors), ForeignKey from DailySteps, Garmin_Auth, etc.
- **Methods**:
  - `earn_gym_gems(self, amount)`: Adds amount to gym_gems and saves.
  - `earn_cardio_coins(self, amount)`: Adds amount to cardio_coins and saves.
- **Usage**: AUTH_USER_MODEL = 'core.UserProfile'; used in forms/views for auth and profiles.

## ColorPreferences
- **Description**: Per-user theme colors for UI customization (Material Design-like).
- **Fields**:
  - `user`: OneToOneField to UserProfile (on_delete=CASCADE, related_name='theme_colors').
  - `surface`, `on_surface`, `primary`, `on_primary`, `secondary`, `on_secondary`, `tertiary`, `on_tertiary`, `surface_variant`, `on_surface_variant`, `outline`, `error`: CharField(max_length=7, default=hex color, help_text='Color description').
- **Relationships**: OneToOne with UserProfile.
- **Methods**:
  - Getters like `get_surface_color(self)`: Returns self.surface (similar for others).
  - `__str__`: f"Color Preferences for {self.user.username}".
- **Usage**: Auto-created on user save; used in templates for dynamic theming.

## Friendship
- **Description**: Manages friend requests and status between users.
- **Fields**:
  - `uuid`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique ID").
  - `from_user`, `to_user`: ForeignKey to UserProfile (related_name='friendship_requests_sent/received', on_delete=CASCADE).
  - `status`: CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('blocked', 'Blocked')], default='pending').
  - `created_at`, `updated_at`: DateTimeField(auto_now_add=True/auto_now=True).
- **Relationships**: ForeignKeys to UserProfile.
- **Meta**: unique_together=('from_user', 'to_user'); ordering=['-created_at'].
- **Methods**: `__str__`: f"{from_user.username} -> {to_user.username} ({status})".
- **Usage**: Queried in views for social features, e.g., get friends for chart comparisons.

## Gear
- **Description**: Equipable items with rarity and stat bonuses.
- **Fields**:
  - `name`: CharField(max_length=100).
  - `rarity`: CharField(max_length=20, choices=[('worn_out', 'Worn-Out'), ('standard_issue', 'Standard Issue'), ('pro_grade', 'Pro-Grade'), ('signature_series', 'Signature Series'), ('mythic_flex', 'Mythic Flex')]).
  - `slot`: CharField(max_length=10, choices=[('head', 'Head'), ('torso', 'Torso'), ('arms', 'Arms'), ('legs', 'Legs'), ('feet', 'Feet')]).
  - `str_bonus`, `end_bonus`, `fcs_bonus`, `rcv_bonus`, `lck_bonus`: IntegerField(default=0).
  - `description`: TextField(blank=True).
- **Relationships**: None direct (likely ManyToMany with UserProfile for equipped gear, not defined here).
- **Methods**: `__str__`: f"{name} ({rarity})".
- **Usage**: For item shop/equipment slots; bonuses apply to user stats.

## DailySteps
- **Description**: Tracks daily step goals and totals (non-Garmin).
- **Fields**:
  - `user`: ForeignKey to UserProfile (on_delete=CASCADE, related_name='daily_steps').
  - `calendar_date`: DateField(default=timezone.now).
  - `total_steps`: IntegerField(default=0).
  - `total_distance`: FloatField(default=0) – In miles (2.2 ft/step).
  - `step_goal`: IntegerField(default=10000).
- **Relationships**: ForeignKey to UserProfile.
- **Methods**: None.
- **Usage**: For manual or calculated step tracking.

## Garmin_Auth
- **Description**: Stores Garmin OAuth tokens and sync metadata.
- **Fields**:
  - `user`: OneToOneField to UserProfile (on_delete=CASCADE).
  - `oauth_token`, `oauth_token_secret`, `mfa_token`, `domain`, `scope`, `jti`, `token_type`, `access_token`, `refresh_token`: CharField(max_length=10000, various blank/null).
  - `expires_in`, `expires_at`, `refresh_token_expires_in` (default=10000), `refresh_token_expires_at`: IntegerField(null=True, blank=True).
  - `last_sync`, `last_sync_attempt`: DateTimeField(null=True, blank=True, help_text="Sync timestamps").
  - `garmin_email`: EmailField(blank=True, null=True).
- **Relationships**: OneToOne with UserProfile.
- **Methods**:
  - `expired(self)`: Returns True if expires_at < now (or None).
  - `refresh_expired(self)`: True if refresh_token_expires_at < now.
  - `__str__`: f"{token_type.title()} {access_token[:20]}...".
- **Usage**: For Garmin auth and token management in sync views.

## GarminCredentials
- **Description**: Alternative Garmin auth storage (possibly legacy/backup).
- **Fields**:
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4).
  - `user`: OneToOneField to UserProfile (related_name='garmin_credentials', on_delete=CASCADE).
  - `garmin_email`: EmailField(unique=True, help_text="Garmin email").
  - `session_data`: JSONField(null=True, blank=True).
  - `last_sync`: DateTimeField(null=True, blank=True).
  - `created_at`, `updated_at`: DateTimeField(auto_now_add=True/auto_now=True).
- **Relationships**: OneToOne with UserProfile.
- **Methods**: `__str__`: f"Garmin Credentials for {user.username}".
- **Meta**: verbose_name_plural = "Garmin Credentials".
- **Usage**: For session-based Garmin linking.

## GarminDailySteps
- **Description**: Synced daily steps from Garmin.
- **Fields**:
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4).
  - `user`: ForeignKey to UserProfile (related_name='garmin_daily_steps', on_delete=CASCADE).
  - `date`: DateField(help_text="Date of steps").
  - `steps`: PositiveIntegerField(help_text="Total steps").
- **Relationships**: ForeignKey to UserProfile.
- **Methods**: `__str__`: f"{user.username} - {date}: {steps} steps".
- **Meta**: ordering=['-date']; unique_together=('user', 'date'); verbose_name_plural = "Garmin Daily Steps".
- **Usage**: Queried for steps chart data.

## GarminActivity
- **Description**: Synced activities from Garmin (e.g., runs, with HR/calories).
- **Fields**:
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4).
  - `user`: ForeignKey to UserProfile (related_name='garmin_activities', on_delete=CASCADE).
  - `activity_id`: BigIntegerField(unique=True).
  - `name`: CharField(max_length=255).
  - `activity_type`: CharField(max_length=100).
  - `start_time_utc`: DateTimeField.
  - `duration_seconds`, `distance_meters`, `calories`, `average_hr`, `max_hr`: FloatField(null=True, blank=True).
  - `raw_data`: JSONField(null=True, blank=True) – Full Garmin API JSON.
  - `synced_at`: DateTimeField(auto_now=True).
- **Relationships**: ForeignKey to UserProfile.
- **Methods**: `__str__`: f"{user.username} - {name} ({activity_id}) on {start_time_utc.date()}".
- **Usage**: For calories/sweat score calculations in chart views.

## SweatScoreWeights
- **Description**: Configurable weights for sweat score by HR zone.
- **Fields**:
  - `zone`: IntegerField(choices=[(0, 'Zone 0 - Below Zone 1'), (1, 'Zone 1 - Very Light'), ..., (5, 'Zone 5 - Maximum')], unique=True).
  - `name`: CharField(max_length=100).
  - `perceived_effort`: CharField(max_length=100).
  - `weight`: DecimalField(max_digits=5, decimal_places=2, default=1.00).
- **Relationships**: None.
- **Methods**: `__str__`: f"Zone {zone}: {name} ({weight} pts/min)".
- **Meta**: ordering=['zone']; verbose_name = "Sweat Score Weight"; verbose_name_plural = "Sweat Score Weights".
- **Usage**: Queried in calculate_sweat_score for scoring activities.

## Signals
- `@receiver(post_save, sender=UserProfile)`: `create_color_preferences` – If created, creates ColorPreferences for the user.
- **Usage**: Ensures new users get default theme colors.

## Model Relationships Diagram (Mermaid)
```mermaid
erDiagram
    USERPROFILE ||--o{ DAILYSTEPS : has
    USERPROFILE ||--o{ GARMIN_DAILYSTEPS : has
    USERPROFILE ||--o{ GARMIN_ACTIVITY : has
    USERPROFILE ||--|| GARMIN_AUTH : has
    USERPROFILE ||--|| GARMIN_CREDENTIALS : has
    USERPROFILE ||--|| COLOR_PREFERENCES : has
    USERPROFILE }o--o{ FRIENDSHIP : participates
    USERPROFILE ||--o{ FRIENDSHIP : from/to
    FRIENDSHIP }o--|| USERPROFILE : from_user
    FRIENDSHIP }o--|| USERPROFILE : to_user
```
This diagram shows key relationships; Gear is standalone for now.