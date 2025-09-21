# Future Roadmap

Here is a list of features and fixes planned for the future development of Flexingg.

## Tasks

*   **Fix profile activities to be Garmin or Liftosaur or Health Connect**
    *   **Description:** Currently, profile activities seem to only show Garmin activities. This should be updated to pull from `core/models.py` and display a unified view of workouts, sleep, eating, and water intake. Steps should be excluded.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: Contains the data models for all user activities.
        *   `Flexingg/core/views.py`: Specifically the profile view function.
        *   `Flexingg/core/templates/profile.html`: The template for the user profile page.
        *   `Docs/core/models.md`: Documentation for the core models.

*   **Fix homepage date display**
    *   **Description:** The homepage appears to be showing the current date in UTC. Investigate if it should be the user's local device date or EST. This might be a minor issue or nothing at all.
    *   **AI Code Assistant Context:**
        *   Search the codebase for `UTC` to identify where it's being used.
        *   `Flexingg/core/views.py`: Specifically the home view function.
        *   `Flexingg/core/templates/home.html`: The template for the homepage.

*   **Update social/main with actual stats**
    *   **Description:** The social/main section seems to be pulling from old or incorrect data sources. All data should come from `core/models.py`.
    *   **AI Code Assistant Context:**
        *   `Flexingg/social/views.py`: The views for the social section.
        *   `Flexingg/social/main.py`: If it exists, or relevant files in the `social` app.
        *   `Flexingg/core/models.py`: The source of truth for user data.
        *   `Docs/social.md`: Documentation for the social app.

*   **Add user multiplier for CardioCoins and GymGems**
    *   **Description:** Implement a multiplier for CardioCoins and GymGems that can be affected by gear. For example, equipping certain gear could allow a user to gain 1.2 CardioCoins per calorie burned.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: To add the multiplier fields to the `UserProfile` or a new model for gear.
        *   `Flexingg/core/tasks.py`: Where the coin calculation logic likely resides.

*   **Ensure 1 CardioCoin per calorie burned (base)**
    *   **Description:** The base rate for earning CardioCoins should be 1 coin per 1 calorie burned. This should be adjustable by multipliers from gear, buffs, and debuffs.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/tasks.py`: Where the coin calculation logic likely resides.
        *   `Flexingg/core/models.py`: To check for existing multipliers.

*   **Add bodyweight to core/models**
    *   **Description:** Add a `bodyweight` field to the user's profile in `core/models.py`. Implement an import task to get this data from Health Connect, Garmin Connect, and Liftosaur.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: To add the `bodyweight` field to `UserProfile`.
        *   `Flexingg/healthconnect/tasks.py`: To add bodyweight import from Health Connect.
        *   `Flexingg/garminconnect/tasks.py`: To add bodyweight import from Garmin Connect.
        *   `Flexingg/liftosaur/tasks.py`: To add bodyweight import from Liftosaur.

*   **Prompt for manual bodyweight entry**
    *   **Description:** If a user's bodyweight cannot be synced from any of the connected services and is not already stored, prompt them to enter it manually.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/views.py`: In a relevant view like profile or settings.
        *   `Flexingg/core/templates/`: Create a template for the prompt.

*   **Ensure 1 GymGem per bodyweight lifted (base)**
    *   **Description:** The base rate for earning GymGems should be 1 gem per unit of bodyweight lifted. If bodyweight is not available, use a default of 200lbs. This should be adjustable by multipliers from gear, buffs, and debuffs.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/tasks.py`: Where the gem calculation logic resides.
        *   `Flexingg/core/models.py`: To access the user's bodyweight.

*   **Add XP system**
    *   **Description:** Implement an experience point (XP) system where users earn 1 XP per CardioCoin and 2 XP per GymGem.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: Add `xp` field to `UserProfile`.
        *   `Flexingg/core/tasks.py`: Update the coin and gem calculation to also award XP.

*   **Create a Levels model**
    *   **Description:** Create a `Level` model based on total XP. The XP required for each level should increase exponentially, but slowly. For example: Level 1 to 2 requires 100 XP, level 10 to 11 requires ~1000 XP, and level 100 to 101 requires ~10,000 XP.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: Create the `Level` model.
        *   A script or management command to populate the level progression.

*   **Display levels on profile and dashboard**
    *   **Description:** The user's current level should be displayed on their profile and the main dashboard.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/views.py`: Update profile and dashboard views to include the level.
        *   `Flexingg/core/templates/profile.html`: Add level display.
        *   `Flexingg/core/templates/home.html`: Add level display.

*   **Fix Gyms UI**
    *   **Description:** The Gyms UI should be updated to be better aligned with the rest of the app's design. It should also clearly indicate that the feature is "coming soon" and not yet enabled.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/templates/gym.html`: The template for the Gyms page.
        *   `Flexingg/core/static/`: Any relevant CSS or JS files.

*   **Add user stats to profile view**
    *   **Description:** Display user stats like strength, speed, etc. on the profile page. This data should be pulled from `core/models.py`.
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: The `UserProfile` model.
        *   `Flexingg/core/views.py`: The profile view.
        *   `Flexingg/core/templates/profile.html`: The profile template.

*   **Setup admin-only Gear Creator view**
    *   **Description:** Create a view accessible only by admins to create and manage gear. The view should allow setting the following properties:
        *   Gear Image
        *   Slot (e.g., helmet, shoes)
        *   Rarity (e.g., common, rare, epic)
        *   Name
        *   Description
        *   Stats (e.g., multipliers)
        *   Cost value
        *   Cost currency (CardioCoins or GymGems)
    *   **AI Code Assistant Context:**
        *   `Flexingg/core/models.py`: Create a `Gear` model.
        *   `Flexingg/core/admin.py`: To register the `Gear` model with the Django admin site.
        *   `Flexingg/core/views.py`: Create a new view for the gear creator.
        *   `Flexingg/core/templates/`: Create a new template for the gear creator form.
        *   Django's admin interface documentation.
