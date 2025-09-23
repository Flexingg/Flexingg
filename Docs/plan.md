# Flexin.gg Feature Implementation Plan

## Overview
This plan outlines the implementation of currency multipliers, base earning rates, XP system, and level progression for the Flexin.gg fitness app. The plan is divided into phases to ensure smooth progression with testing opportunities.

## Current State Analysis
- **Models**: UserProfile already has `xp` and `level` fields, Gear model exists with stat bonuses
- **Views**: Level display already implemented in home.html and profile.html templates
- **Currency**: gym_gems and cardio_coins fields exist, Transaction model for tracking
- **Data Processing**: sync_service.py and data_processor.py handle data syncing but lack currency calculation logic

## Phase 1: Foundation - Currency Multipliers & Base Rates

### 1.1 Add User Multiplier Fields to UserProfile Model
**Files to modify**: `Flexingg/core/models.py`
- Add `cardio_coins_multiplier` (DecimalField, default=1.0)
- Add `gym_gems_multiplier` (DecimalField, default=1.0)
- Add `bodyweight_lbs` (DecimalField, default=200.0) for fallback when not synced

### 1.2 Create Currency Calculation Service
**Files to create**: `Flexingg/core/currency_service.py`
- `calculate_cardio_coins(calories, multiplier)` - returns calories * 1.0 * multiplier
- `calculate_gym_gems(volume_lbs, bodyweight_lbs, multiplier)` - returns volume_lbs * (1.0/bodyweight_lbs) * multiplier
- `calculate_xp_from_currencies(cardio_coins, gym_gems)` - returns (cardio_coins * 1) + (gym_gems * 2)

### 1.3 Integrate Currency Calculations into Data Processing
**Files to modify**: `Flexingg/core/data_processor.py`
- Import currency_service
- After processing workouts, calculate and award currencies
- Handle bodyweight fallback logic (use synced weight or default 200lbs)
- Award XP based on earned currencies

### 1.4 Add Bodyweight Sync Prompt System
**Files to modify**: `Flexingg/core/views.py`
- Add view logic to check if user has bodyweight data
- Create template for manual bodyweight entry prompt
**Files to create**: `Flexingg/core/templates/bodyweight_prompt.html`

## Phase 2: XP System Implementation

### 2.1 Update Transaction Model for XP Tracking
**Files to modify**: `Flexingg/core/models.py`
- Add `xp_awarded` field to Transaction model (IntegerField, default=0)
- Update Transaction.CURRENCY_CHOICES to include 'xp'

### 2.2 Enhance Currency Service with XP Calculation
**Files to modify**: `Flexingg/core/currency_service.py`
- Update calculation functions to return both currency amounts and XP
- Add `award_currencies_and_xp(user, cardio_coins, gym_gems, garmin_activity=None)` function

### 2.3 Update Data Processing Integration
**Files to modify**: `Flexingg/core/data_processor.py`
- Use enhanced currency service functions
- Ensure XP is calculated and stored with transactions
- Update user.xp field when currencies are awarded

## Phase 3: Level System Creation

### 3.1 Create Level Model and Management Command
**Files to create**: `Flexingg/core/models.py`
- Add Level model with `level_number`, `xp_required`, `created_at` fields
**Files to create**: `Flexingg/core/management/commands/populate_levels.py`
- Create command to populate exponential XP requirements
- Formula: `xp_required = base_xp * (growth_factor ^ (level_number - 1))`
- Example: Level 1→2: 100 XP, Level 10→11: ~1000 XP, Level 100→101: ~10,000 XP

### 3.2 Add Level Calculation Logic
**Files to modify**: `Flexingg/core/currency_service.py`
- Add `calculate_user_level(total_xp)` function
- Add `get_next_level_xp(current_level)` function
- Add `get_level_progress_percentage(current_xp, current_level)` function

### 3.3 Update User Profile Updates
**Files to modify**: `Flexingg/core/data_processor.py`
- After awarding XP, check if user leveled up
- Update user.level field when XP threshold is reached

## Phase 4: UI Updates & Display

### 4.1 Update Home Dashboard
**Files to modify**: `Flexingg/core/templates/home.html`
- Replace hardcoded level_card values with dynamic data from context
- Add level progress display
**Files to modify**: `Flexingg/core/views.py`
- Update HomeView to pass level, xp, and next_level_xp to context

### 4.2 Update Profile Page
**Files to modify**: `Flexingg/core/templates/profile.html`
- Ensure level display uses dynamic data (already partially implemented)
- Add level progress bar improvements
**Files to modify**: `Flexingg/core/views.py`
- Update ProfileView to pass accurate level data

### 4.3 Add Bodyweight Prompt Integration
**Files to modify**: `Flexingg/core/templates/base.html`
- Add bodyweight prompt modal for users without bodyweight data
**Files to modify**: `Flexingg/core/views.py`
- Add context to show/hide bodyweight prompt

## Phase 5: Testing & Validation

### 5.1 Database Migration Testing
- Test all new model fields and relationships
- Verify data integrity during migrations
- Test level population command

### 5.2 Currency Calculation Testing
- Test base rates (1 CardioCoin per calorie, 1 GymGem per bodyweight unit)
- Test multiplier effects from gear
- Test XP calculation (1 XP per CardioCoin, 2 XP per GymGem)

### 5.3 Level Progression Testing
- Test XP requirements increase exponentially
- Test level up functionality
- Test level display accuracy

### 5.4 Integration Testing
- Test complete flow from workout sync to currency/XP award to level up
- Test bodyweight fallback scenarios
- Test UI updates and displays

## Implementation Notes

### Gear Integration
- Existing Gear model already has stat bonuses (str_bonus, end_bonus, etc.)
- These can be used to modify multipliers: `total_multiplier = base_multiplier * (1 + gear_stat_bonus/100)`

### Data Sources
- **CardioCoins**: Calculated from calories burned in cardio activities
- **GymGems**: Calculated from weight lifted volume normalized by bodyweight
- **XP**: Derived from currencies earned (1:1 for CardioCoins, 2:1 for GymGems)

### Error Handling
- Graceful fallback to default bodyweight (200lbs) when not available
- Validation for currency calculations to prevent negative values
- Logging for debugging currency and XP calculations

## Questions & Considerations

1. **Gear Multiplier Application**: Should gear multipliers be additive or multiplicative? (Current plan: multiplicative)
2. **XP from Other Sources**: Should sleep, water intake, or nutrition also award XP, or only currencies?
3. **Level Cap**: Should there be a maximum level, or infinite progression?
4. **Retroactive XP**: Should existing users get XP for past activities, or start fresh?
5. **Testing Environment**: What testing framework/environment should be used for validation?

## Risk Mitigation

- **Database Rollback Plan**: All changes include migration files that can be reversed
- **Feature Flags**: Consider implementing feature flags for gradual rollout
- **Performance**: Currency calculations happen during sync - monitor for performance impact
- **Data Integrity**: Add validation to prevent invalid currency/XP values

## Success Metrics

- Currency earning feels fair and rewarding
- Level progression provides meaningful goals
- UI clearly displays progress and achievements
- System handles edge cases (missing bodyweight, no gear, etc.) gracefully