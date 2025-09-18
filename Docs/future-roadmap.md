# Flexingg Future Roadmap

This document outlines the future development plans for the Flexingg application. It details upcoming features and gameplay mechanics designed to enhance the user experience and create a more engaging and rewarding gamified fitness journey.

## Core Gameplay Loop: The Gym System

The main progression of the app will be centered around a new **Gym feature**. This system is inspired by the progression in games like Pokémon, where players challenge a series of gyms to prove their skills and advance.

-   **Gyms and Rivals**: Players will face a series of "Gyms," each with a unique theme and a "Gym Rival."
-   **Challenges**: To defeat a gym, players must complete a series of fitness challenges. These challenges will be varied and will test different aspects of a user's fitness. Examples include:
    -   "Burn 1000 calories in a single day."
    -   "Lift 100,000 lbs in a single week."
    -   "Accumulate 500 Sweat Score points in a single activity."
-   **Progression and Rewards**: Progressing through the gyms will be the primary way for players to gain experience points (XP) and level up. This will require the implementation of a new **Experience and Leveling System**. Each gym victory will also provide unique rewards, such as rare gear or large sums of in-game currency.

## Player Progression: Gear and Economy

To complement the gym system, we will introduce a robust **Gear System** that will allow players to customize their abilities and playstyle.

-   **Gear Cards**: Gear will be represented as "cards" that can be equipped in the "Locker Room."
-   **Buffs and Effects**: Each piece of gear will provide a unique buff to the player. Examples include:
    -   "Gain an extra 2% CardioCoins from all activities."
    -   "Gym challenges are 4% easier to complete."
    -   "Increase your Strength stat by 5."
-   **Rarity and Levels**: Gear will have different rarities (e.g., Common, Rare, Epic, Legendary), with rarer gear providing more powerful buffs. Some gear will also have level requirements, ensuring that players are rewarded for their progression.
-   **Acquisition**: Gear can be acquired in two ways:
    -   **Purchasing from the Shop**: Players can use their `CardioCoins` and `GymGems` to purchase gear from the in-game shop.
    -   **Earning from Challenges**: Rare and powerful gear can be earned as rewards for completing difficult challenges or defeating gyms.

## Advanced Gameplay: Optional Difficulties

For players who want an extra challenge, we will introduce a set of **Optional Difficulties** that can be enabled or disabled at will in the settings. These difficulties will provide both rewards and penalties, creating a risk-reward dynamic.

-   **SleepSalary**:
    -   **Goal**: Get at least 7 hours of sleep.
    -   **Reward**: A 10% buff to all `CardioCoins` and `GymGems` earned the next day.
    -   **Penalty**: A debuff of up to 12% for sleeping less than 7 hours (1% for every 10 minutes short).
-   **FoodFuel**:
    -   **Goal**: Log an adequate number of calories (within a certain percentage of the user's goal).
    -   **Reward**: A 10% buff to all `CardioCoins` and `GymGems` earned the next day.
    -   **Penalty**: A 10% debuff for being significantly under or over the calorie goal.
-   **HydrationHydrangea**:
    -   **Goal**: Log at least 32oz of water per day.
    -   **Mechanic**: Logging water will cause a virtual plant to grow. The larger the plant, the larger the player's daily login bonus.
    -   **Penalty**: Failing to log water will cause the plant to decay. If the plant dies (after 7 consecutive days of no water), the player will lose their login bonus and have to start over.

## Future Ideas

This section is for brainstorming additional features and ideas that the development team can consider for the future of Flexingg.

### Social Features
-   **Group Challenges**: Introduce challenges that require a group of friends to work together to complete.
-   **Gear Trading**: Allow players to trade gear with their friends.
-   **Fitness Duels**: A feature where players can challenge their friends to one-on-one fitness competitions.
-   **Shared Gym**: A virtual gym where friends can see each other's progress and cheer each other on.

### New Integrations
-   **Fitbit and Apple Health**: Expand the app's integration capabilities to include other popular fitness trackers.
-   **MyFitnessPal**: Integrate with MyFitnessPal for more detailed nutrition tracking, which would enhance the `FoodFuel` difficulty.
-   **Spotify/Apple Music**: Allow users to link their music streaming accounts to create workout playlists within the app.

### New Gameplay Mechanics
-   **Skill Tree**: A branching skill tree where players can spend `CardioCoins` or `GymGems` to unlock permanent buffs, new abilities, or passive bonuses.
-   **World Bosses**: Global, server-wide events where all players contribute to defeating a massive fitness challenge (e.g., " collectively run the distance to the moon").
-   **Dungeons**: A series of themed fitness challenges that must be completed in a specific order, with a big reward at the end.
-   **Crafting System**: Allow players to use resources earned from activities to craft their own gear or consumables (e.g., "potions" that provide temporary buffs).

### Customization
-   **Avatar Customization**: More options for customizing the player's avatar, including different outfits, hairstyles, and accessories.
-   **Dashboard Customization**: Allow players to customize the layout of their home dashboard to show the stats and information that are most important to them.
-   **App Themes**: Introduce different "skins" or themes for the app that can be unlocked or purchased.

## Implementation Plan

Here is a detailed plan for implementing the features described above.

### 1. Backend: Models

This section provides a detailed breakdown of the Django models required for the new features.

#### Gym and Challenge Models

These models form the core of the Gym progression system.

*   **`Gym`**
    *   **Description**: Represents a single gym that a player can challenge.
    *   **Fields**:
        *   `name`: `CharField` - The name of the gym (e.g., "The Cardio Core").
        *   `description`: `TextField` - A brief description of the gym's theme and challenges.
        *   `theme_icon`: `CharField` - A reference to an icon representing the gym's theme (e.g., a Font Awesome class or an emoji).
        *   `order`: `IntegerField` - A unique integer that determines the progression order of the gyms.
        *   `is_unlocked_by_default`: `BooleanField` - True for the first gym, False for subsequent gyms.
    *   **Methods**:
        *   `unlock_next_gym(user)`: A method that unlocks the next gym in the sequence for a specific user when this gym is defeated.

*   **`Rival`**
    *   **Description**: Represents the main opponent of a gym.
    *   **Fields**:
        *   `gym`: `OneToOneField` to `Gym` - The gym this rival belongs to.
        *   `name`: `CharField` - The rival's name (e.g., "Captain Cardio").
        *   `backstory`: `TextField` - A short backstory for the rival to add flavor.
        *   `avatar`: `ImageField` - An image of the rival.

*   **`Challenge`**
    *   **Description**: Represents a single fitness challenge within a gym.
    *   **Fields**:
        *   `gym`: `ForeignKey` to `Gym` - The gym this challenge is part of.
        *   `name`: `CharField` - A short name for the challenge (e.g., "Marathon Starter").
        *   `description`: `TextField` - A detailed description of the challenge requirements.
        *   `challenge_type`: `CharField` with choices (e.g., `CALORIES_BURNED`, `LIFTING_VOLUME`, `DISTANCE_RAN`, `SWEAT_SCORE`).
        *   `target_value`: `DecimalField` - The numerical target for the challenge (e.g., 1000 for calories).
        *   `xp_reward`: `IntegerField` - The amount of XP awarded upon completion.
        *   `coin_reward`: `DecimalField` - The amount of `CardioCoins` awarded upon completion.

*   **`UserChallenge`**
    *   **Description**: Tracks a user's progress on a specific challenge. This is a through model.
    *   **Fields**:
        *   `user`: `ForeignKey` to `UserProfile` - The user undertaking the challenge.
        *   `challenge`: `ForeignKey` to `Challenge` - The challenge being undertaken.
        *   `status`: `CharField` with choices (`IN_PROGRESS`, `COMPLETED`).
        *   `current_progress`: `DecimalField` - The user's current progress towards the `target_value`.
        *   `start_date`: `DateTimeField` - When the user started the challenge.
        *   `completion_date`: `DateTimeField` (nullable) - When the user completed the challenge.
    *   **Methods**:
        *   `update_progress(value)`: A method to update the `current_progress` and check for completion. If completed, it should update the status and award the user.

#### Experience and Leveling Models

These models handle player progression.

*   **`Level`**
    *   **Description**: Defines the XP thresholds for each level. This makes the leveling curve easy to configure.
    *   **Fields**:
        *   `level_number`: `IntegerField` (Primary Key) - The level number.
        *   `xp_required`: `IntegerField` - The total XP required to reach this level from level 1.
    *   **Methods**:
        *   `get_xp_for_next_level()`: A static method that returns the XP needed to get from the current level to the next.

*   **`UserProfile` (updates)**
    *   **Description**: We will add a method to the existing `UserProfile` model.
    *   **Methods**:
        *   `add_xp(amount)`: A method to add XP to the user's profile and trigger a check for leveling up. It will call `check_for_level_up`.
        *   `check_for_level_up()`: A method that checks the user's current XP against the `Level` table and updates the user's level if a threshold is met.

#### Gear and Economy Models

These models manage the items and currency in the game.

*   **`Gear` (updates)**
    *   **Description**: We will add a few fields to the existing `Gear` model.
    *   **Fields (new)**:
        *   `level_requirement`: `IntegerField` - The player level required to equip this gear.
        *   `price_cardio_coins`: `DecimalField` - The cost of the gear in `CardioCoins`.
        *   `price_gym_gems`: `DecimalField` - The cost of the gear in `GymGems`.
        *   `icon`: `ImageField` - An icon for the gear.

*   **`UserGear`**
    *   **Description**: Represents an instance of gear owned by a user.
    *   **Fields**:
        *   `user`: `ForeignKey` to `UserProfile` - The owner of the gear.
        *   `gear`: `ForeignKey` to `Gear` - The piece of gear that is owned.
        *   `is_equipped`: `BooleanField` - True if the user is currently wearing this gear.
        *   `date_acquired`: `DateTimeField` - When the user obtained the gear.
    *   **Methods**:
        *   `equip()`: A method that sets `is_equipped` to True, but first checks for level requirements and ensures no other gear is equipped in the same slot.
        *   `unequip()`: A method that sets `is_equipped` to False.

#### Optional Difficulty Models

These models handle the opt-in challenge modifiers.

*   **`OptionalDifficulty`**
    *   **Description**: Stores the definition of an optional difficulty setting.
    *   **Fields**:
        *   `name`: `CharField` (unique) - The name of the difficulty (e.g., "SleepSalary").
        *   `description`: `TextField` - A detailed explanation of the buffs and debuffs.
    *   **Methods**:
        *   `apply_modifier(user)`: A method that contains the logic to apply the daily buff or debuff to a user. This would be called by a Celery task.

*   **`UserOptionalDifficulty`**
    *   **Description**: A through model that links a user to an optional difficulty they have toggled.
    *   **Fields**:
        *   `user`: `ForeignKey` to `UserProfile` - The user.
        *   `difficulty`: `ForeignKey` to `OptionalDifficulty` - The difficulty setting.
        *   `is_active`: `BooleanField` - True if the user currently has this difficulty enabled.

### 2. Backend: Views

*   **Gym Views**:
    *   `GymListView`: A view to list all available gyms.
    *   `GymDetailView`: A view to show the details of a specific gym, including its rival and the challenges it offers. This view will also handle the logic for a user to accept challenges.
*   **Challenge Views**:
    *   `ChallengeProgressView`: A view to show a user's progress on their active challenges. This could be part of the `HomeView` or a separate page.
*   **Gear Views**:
    *   `LockerRoomView`: This view will be updated to show the user's owned gear (`UserGear`) and allow them to equip/unequip items.
    *   `ShopView`: This view will be updated to list `Gear` available for purchase. It will handle the logic for buying gear with `cardio_coins` or `gym_gems`.
*   **Settings View**:
    *   The `SettingsView` will be updated to allow users to enable/disable the `OptionalDifficulties`.

### 3. Backend: URLs

*   We will add new URL patterns for the new views:
    *   `/gyms/`: For the `GymListView`.
    *   `/gyms/<int:gym_id>/`: For the `GymDetailView`.
    *   `/challenges/`: For the `ChallengeProgressView`.
    *   The existing `/locker_room/` and `/shop/` URLs will be used for the updated `LockerRoomView` and `ShopView`.

### 4. Backend: Logic

*   **Challenge Completion**: We will implement logic to check for challenge completion. This could be done in a Celery task that runs periodically or triggered by certain events (e.g., after a Garmin sync). When a challenge is completed, the user should be rewarded with XP and the `UserChallenge` status should be updated.
*   **Leveling Up**: When a user gains XP, we will check if they have enough XP to level up. If so, we will update their level in the `UserProfile` model.
*   **Gear Buffs**: We will implement logic to apply gear buffs. This could be done by creating a method on the `UserProfile` model that calculates the total buffs from all equipped gear.
*   **Optional Difficulties**: We will implement the logic for the optional difficulties. This will involve checking the user's sleep, nutrition, and hydration data (from Garmin, Health Connect, etc.) and applying buffs or debuffs accordingly. This logic will likely run in a daily Celery task.

### 5. Frontend: Templates (General Guidance)

*   **`gyms.html`**: A template to display the list of gyms. It should show the gym's name, theme, and an indicator of whether it's locked or unlocked.
*   **`gym_detail.html`**: A template to display the details of a single gym. It should show the gym rival, the list of challenges, and a button to "Challenge this Gym".
*   **`challenges.html`**: A template to display the user's active challenges and their progress.
*   **`locker_room.html`**: The existing template will be updated to show a grid of the user's gear. Each gear item should be displayed as a card with its stats and an "Equip"/"Unequip" button.
*   **`shop.html`**: The existing template will be updated to show a list of gear available for purchase. Each item should have a "Buy" button with the price in `CardioCoins` or `GymGems`.
*   **`settings.html`**: The existing template will be updated with a new section for "Optional Difficulties", with toggles to enable/disable each one.
