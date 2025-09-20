# Data Normalization and Aggregation Plan

## Overview
This plan outlines the implementation of normalized data methods for fitness data sources (Garmin, HealthConnect, Liftosaur) to feed into the core app, along with aggregation methods for useful data retrieval.

## Current State Analysis

### Existing Core Models
- ✅ `Workout` - unified workout data
- ✅ `UnifiedWorkoutExercise` - exercises within workouts
- ✅ `UnifiedWorkoutSet` - sets within exercises
- ✅ `Sleep` - unified sleep data
- ✅ `DailySteps` - unified steps data
- ✅ `DataPriority` - system for choosing data sources

### Existing Integration Status

#### Garmin Connect
- ✅ Steps sync task (`garmin_sync_steps_task`)
- ✅ Activities sync task (`garmin_sync_activities_task`)
- ✅ Models: `GarminDailySteps`, `GarminActivity`
- ❌ Missing: Sleep, Water, Weight sync methods
- ❌ Missing: Normalization to unified models

#### Health Connect
- ✅ Generic sync task (`healthconnect_sync_task`)
- ✅ Model: `HealthConnectData` (stores all data in JSONField)
- ❌ Missing: Specific data type extraction
- ❌ Missing: Normalization to unified models

#### Liftosaur
- ✅ Workout sync task (`sync_liftosaur_data`)
- ✅ Already normalizes to unified `Workout`/`UnifiedWorkoutExercise`/`UnifiedWorkoutSet`
- ✅ Model: `BodyMeasurement` for weight data
- ❌ Missing: Sleep, Steps, Activities sync methods

## Implementation Plan

### Phase 1: Missing Data Models

#### 1.1 Water Intake Model
```python
class DailyWater(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_water')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField()
    amount_ounces = models.DecimalField(max_digits=6, decimal_places=2)
    data = models.JSONField(help_text="Normalized water data", null=True, blank=True)

    class Meta:
        unique_together = ('user', 'source', 'date')
        ordering = ['-date']
```

#### 1.2 Nutrition Model
```python
class NutritionEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_nutrition')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255)
    datetime = models.DateTimeField()
    food_name = models.CharField(max_length=255)
    quantity_description = models.CharField(max_length=100, null=True, blank=True)  # e.g., "5 oz"
    quantity_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    calories = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    protein_grams = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fat_grams = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    carbs_grams = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    data = models.JSONField(help_text="Normalized nutrition data", null=True, blank=True)

    class Meta:
        unique_together = ('user', 'source', 'source_id')
        ordering = ['-datetime']
```

#### 1.3 Body Weight Model
```python
class BodyWeight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_weights')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255, null=True, blank=True)
    datetime = models.DateTimeField()
    weight_lbs = models.DecimalField(max_digits=6, decimal_places=2)
    data = models.JSONField(help_text="Normalized weight data", null=True, blank=True)

    class Meta:
        unique_together = ('user', 'source', 'source_id')
        ordering = ['-datetime']
```

### Phase 2: Data Normalization Methods

#### 2.1 Garmin Connect Normalization
- **Steps**: Already exists → `DailySteps`
- **Activities**: Create normalization method → `Workout` (for cardio activities)
- **Sleep**: Create sync task and normalization → `Sleep`
- **Water**: Create sync task and normalization → `DailyWater`
- **Weight**: Create sync task and normalization → `BodyWeight`

#### 2.2 Health Connect Normalization
- **Steps**: Extract from `HealthConnectData` → `DailySteps`
- **Activities**: Extract from `HealthConnectData` → `Workout`
- **Sleep**: Extract from `HealthConnectData` → `Sleep`
- **Weight**: Extract from `HealthConnectData` → `BodyWeight`
- **Nutrition**: Extract from `HealthConnectData` → `NutritionEntry`
- **Water**: Extract from `HealthConnectData` → `DailyWater`

#### 2.3 Liftosaur Normalization
- **Workout**: Already exists → unified models
- **Weight**: Extract from `BodyMeasurement` → `BodyWeight`
- **Steps**: Create sync task and normalization → `DailySteps`
- **Activities**: Create sync task and normalization → `Workout`
- **Sleep**: Create sync task and normalization → `Sleep`

### Phase 3: Core App Aggregation Methods

#### 3.1 Date Range Aggregation
```python
# Core aggregation methods to be created
def get_aggregated_steps(user, start_date, end_date):
    """Get total steps from prioritized sources"""

def get_aggregated_workouts(user, start_date, end_date):
    """Get workouts from all sources"""

def get_aggregated_sleep(user, start_date, end_date):
    """Get sleep data from prioritized sources"""

def get_aggregated_water(user, start_date, end_date):
    """Get water intake from all sources"""

def get_aggregated_nutrition(user, start_date, end_date):
    """Get nutrition data from all sources"""

def get_aggregated_weight(user, start_date, end_date):
    """Get weight measurements from all sources"""
```

#### 3.2 Data Prioritization Integration
- Use existing `DataPriority` model to determine which source to use for each data type
- Implement fallback logic when primary source unavailable
- Create methods to resolve conflicts when multiple sources have data for same time period

### Phase 4: Sync Task Enhancements

#### 4.1 Garmin Connect Tasks
- Create `garmin_sync_sleep_task()`
- Create `garmin_sync_water_task()`
- Create `garmin_sync_weight_task()`
- Enhance `garmin_sync_activities_task()` to normalize to unified models

#### 4.2 Health Connect Tasks
- Create `healthconnect_normalize_data_task()` to extract specific data types
- Enhance existing sync to call normalization after fetching raw data

#### 4.3 Liftosaur Tasks
- Create `liftosaur_sync_steps_task()`
- Create `liftosaur_sync_activities_task()`
- Create `liftosaur_sync_sleep_task()`
- Enhance existing sync to normalize weight data

## Implementation Priority

### High Priority (Core Functionality)
1. **Weight normalization** - All sources have this data
2. **Sleep normalization** - Critical for health tracking
3. **Activity normalization** - Core fitness metric
4. **Steps normalization** - Already partially implemented

### Medium Priority (Quality of Life)
5. **Water intake normalization** - Important for health tracking
6. **Nutrition normalization** - Important for diet tracking

### Low Priority (Advanced Features)
7. **Enhanced aggregation methods** - Date range filtering, advanced analytics
8. **Conflict resolution** - When multiple sources have conflicting data

## Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Garmin API    │    │ Health Connect   │    │  Liftosaur API  │
│                 │    │ Gateway          │    │                 │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Garmin Models   │    │ HealthConnectData│    │ Liftosaur Models│
│ (Raw Data)      │    │ (JSON Storage)   │    │ (Structured)    │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Normalization   │    │ Data Extraction  │    │ Normalization   │
│ Methods         │    │ & Normalization  │    │ Methods         │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Unified Core    │    │ Unified Core     │    │ Unified Core    │
│ Models          │    │ Models           │    │ Models          │
│                 │    │                  │    │                 │
│ • DailySteps    │    │ • DailySteps     │    │ • DailySteps    │
│ • Workout       │    │ • Workout        │    │ • Workout       │
│ • Sleep         │    │ • Sleep          │    │ • Sleep         │
│ • BodyWeight    │    │ • BodyWeight     │    │ • BodyWeight    │
│ • DailyWater    │    │ • DailyWater     │    │ • DailyWater    │
│ • NutritionEntry│    │ • NutritionEntry │    │ • NutritionEntry│
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Data Priority   │    │ Data Priority    │    │ Data Priority   │
│ Resolution      │    │ Resolution       │    │ Resolution      │
└─────────┬───────┘    └────────┬─────────┘    └───────┬─────────┘
          │                     │                      │
          ▼                     ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Core App Views  │    │ Core App Views   │    │ Core App Views  │
│ & Analytics     │    │ & Analytics      │    │ & Analytics     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Next Steps

1. **Create unified data models** for missing data types (Water, Nutrition, BodyWeight)
2. **Implement normalization methods** for each source to populate unified models
3. **Create aggregation methods** in core app for date range queries
4. **Integrate with existing data priority system** for source selection
5. **Test the complete data flow** from sources to core app views

This plan provides a comprehensive approach to normalizing fitness data from multiple sources while maintaining data integrity and providing flexible aggregation capabilities.

# Usage Examples
## Get user's fitness summary for last 7 days
from datetime import date, timedelta
from Flexingg.core.utils import get_user_fitness_summary

end_date = date.today()
start_date = end_date - timedelta(days=7)
summary = get_user_fitness_summary(user, start_date, end_date)

## Access specific data
total_steps = summary['steps']['total_steps']
weight_entries = summary['weight']['weights']
sleep_data = summary['sleep']['sleep_entries'