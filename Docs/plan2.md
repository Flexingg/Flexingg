I've analyzed the current Garmin Connect implementation and the Health Connect architecture. Now I'll create a comprehensive plan for implementing a similar 3-stage architecture for Garmin Connect data that feeds into the unified DailyHealthSummary table.

# Garmin Connect Data Pipeline Plan

## Overview
This plan outlines the creation of a new 3-stage data processing architecture for Garmin Connect data that mirrors the Health Connect implementation. The goal is to create a unified daily summary table that combines data from multiple sources (Garmin Connect, Health Connect, etc.) for fast dashboard queries and analytics.

## Current Analysis

### Existing Garmin Connect Structure
- **Framework**: Django with Celery for background tasks
- **Current Models**: 
  - `Garmin_Auth` - Authentication data
  - `GarminCredentials` - Alternative auth storage
  - `GarminDailySteps` - Daily step counts
  - `GarminActivity` - Individual activities with calories, distance, HR
  - `GarminBodyWeight` - Weight measurements
- **Current Processing**: Direct processing into specific models with immediate CardioCoin rewards
- **Data Flow**: Sync → Process → Store (2-stage process)

### Target Architecture (Health Connect Pattern)
- **Stage 1 - Ingestion**: Raw data into staging model (fast, non-blocking)
- **Stage 2 - Normalization**: Process into clean models and aggregate metrics
- **Stage 3 - Aggregation**: Update unified DailyHealthSummary for fast queries

### Unified DailyHealthSummary Model
The existing `DailyHealthSummary` model in `healthconnect/models.py` provides:
- `steps_total` - Daily step count
- `active_calories_total` - Exercise calories burned
- `calories_total` - Total calories (nutrition + active)
- `protein_grams_total` - Daily protein intake
- `carbs_grams_total` - Daily carbohydrate intake
- `fat_grams_total` - Daily fat intake
- `water_ounces_total` - Daily water consumption
- `sleep_minutes_total` - Daily sleep duration

## New Garmin Connect Architecture Design

### Data Flow Overview
Here's the step-by-step flow from sync initiation to unified data query:

**Trigger Sync**: User's mobile app sends request to `/api/v1/garminconnect/sync/`.

**Background Task**: View immediately dispatches Celery task with `user_id`, returns 202 Accepted response.

**Fetch & Stage**: Background task:
- Uses existing Garmin API client to fetch data since last sync
- Dumps raw JSON data into `GarminRawData` staging model (quick write-only operation)
- Updates user's `last_sync` timestamp

**Normalize & Aggregate**: Secondary background task:
- Queries unprocessed records from `GarminRawData`
- Maps each data type to specific processing function
- Updates both Garmin-specific normalized models AND unified `DailyHealthSummary`
- Marks records as processed

**Query**: Mobile app fetches unified data from `/api/v1/daily-health-summaries/` endpoint

### 1. Models (garminconnect/models.py)

#### New Staging Model
```python
class GarminRawData(models.Model):
    """
    STAGING MODEL: Stores raw, unmodified data from Garmin Connect API.
    This model acts as a temporary holding area before normalization.
    """
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='raw_garmin_data')
    data_type = models.CharField(max_length=50, db_index=True)  # 'steps', 'activities', 'weight', 'hydration'
    record_id = models.CharField(max_length=255, db_index=True)  # Activity ID, weight timestamp, etc.
    date = models.DateField(db_index=True)
    data = models.JSONField()  # Complete raw API response
    source = models.CharField(max_length=100, default='garmin_api')
    
    # Status tracking
    is_processed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'data_type', 'record_id')
        ordering = ['-date']
        verbose_name = "Raw Garmin Connect Data"
Enhanced Normalized Models
The existing models (GarminActivity, GarminBodyWeight, GarminDailySteps) will be enhanced with:

source_id field for tracking back to raw data
Better indexing for aggregation queries
Links to unified models where applicable
2. API Client Service (garminconnect/services.py)
class GarminAPIClient:
    """
    Enhanced client to interact with Garmin Connect API.
    Handles authentication, token refreshing, and data fetching with staging support.
    """
    def __init__(self, profile):
        self.profile = profile
        self.client = None  # Existing garth client
        
    def _ensure_authenticated(self):
        # Use existing configure_garmin_client logic
        pass
        
    def fetch_data_since(self, last_sync_time=None):
        """
        Fetch all relevant data types since last sync.
        Returns structured data ready for staging.
        """
        self._ensure_authenticated()
        
        # Default to last 7 days if no sync time
        if not last_sync_time:
            last_sync_time = timezone.now() - timedelta(days=7)
            
        data_types = {
            'activities': self._fetch_activities,
            'steps': self._fetch_daily_steps,
            'weight': self._fetch_weight_data,
            'hydration': self._fetch_hydration_data,
        }
        
        all_data = {}
        for data_type, fetch_func in data_types.items():
            try:
                all_data[data_type] = fetch_func(last_sync_time)
            except Exception as e:
                logger.error(f"Failed to fetch {data_type}: {e}")
                all_data[data_type] = []
                
        return all_data
3. Background Tasks (garminconnect/sync_tasks.py)
Enhanced Sync Task
@shared_task
def sync_garmin_data(profile_id):
    """
    Task 1: Fetches data from Garmin API and saves to staging model.
    """
    from core.models import UserProfile
    
    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found for Garmin sync")
        return

    client = GarminAPIClient(profile)
    last_sync = profile.garmin_last_sync  # Assume this field exists
    
    # Fetch all data types
    raw_data = client.fetch_data_since(last_sync)
    
    # Stage all data types
    staged_count = 0
    for data_type, records in raw_data.items():
        for record in records:
            GarminRawData.objects.update_or_create(
                profile=profile,
                data_type=data_type,
                record_id=self._extract_record_id(data_type, record),
                defaults={
                    'date': self._extract_date(data_type, record),
                    'data': record,
                    'is_processed': False,
                }
            )
            staged_count += 1

    # Update sync timestamp and trigger processing
    profile.garmin_last_sync = timezone.now()
    profile.save()
    
    # Trigger stage 2
    process_staged_garmin_data.delay(profile_id)
    
    logger.info(f"Staged {staged_count} Garmin records for user {profile_id}")
New Processing Task
@shared_task
def process_staged_garmin_data(profile_id):
    """
    Task 2: Processes staged records into normalized models and unified summary.
    """
    from .normalizers import normalize_and_aggregate_garmin_record
    
    unprocessed_records = GarminRawData.objects.filter(
        profile_id=profile_id, 
        is_processed=False
    )
    
    processed_count = 0
    for record in unprocessed_records:
        try:
            normalize_and_aggregate_garmin_record(record)
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to process Garmin record {record.id}: {e}")
    
    # Mark all as processed
    unprocessed_records.update(is_processed=True)
    
    logger.info(f"Processed {processed_count} Garmin records for user {profile_id}")
4. Normalization Logic (garminconnect/garmin_normalizers.py)
def normalize_and_aggregate_garmin_record(record: GarminRawData):
    """Routes a raw Garmin record to the correct handler based on data_type."""
    from django.db import transaction
    
    handler_map = {
        'activities': _handle_activities,
        'steps': _handle_steps,
        'weight': _handle_weight,
        'hydration': _handle_hydration,
    }
    
    with transaction.atomic():
        handler = handler_map.get(record.data_type)
        if handler:
            handler(record)

def _handle_activities(record):
    """Process activities into GarminActivity and update DailyHealthSummary."""
    from .models import GarminActivity
    from healthconnect.models import DailyHealthSummary
    from django.db.models import F
    
    activity_data = record.data
    activity_date = record.date
    
    # Create/update GarminActivity (existing logic)
    activity, created = GarminActivity.objects.update_or_create(
        user=record.profile,
        activity_id=activity_data.get('activityId'),
        defaults={
            'name': activity_data.get('activityName'),
            'calories': activity_data.get('calories'),
            'start_time_utc': activity_data.get('startTimeGMT'),
            # ... other fields
        }
    )
    
    # Update unified DailyHealthSummary
    if activity.calories and activity.calories > 0:
        summary, _ = DailyHealthSummary.objects.get_or_create(
            profile=record.profile,
            date=activity_date
        )
        summary.active_calories_total = F('active_calories_total') + activity.calories
        summary.save()

def _handle_steps(record):
    """Process daily steps and update DailyHealthSummary."""
    from healthconnect.models import DailyHealthSummary
    from django.db.models import F
    
    steps_data = record.data
    steps = steps_data.get('totalSteps', 0)
    
    if steps > 0:
        summary, _ = DailyHealthSummary.objects.get_or_create(
            profile=record.profile,
            date=record.date
        )
        summary.steps_total = F('steps_total') + steps
        summary.save()

def _handle_weight(record):
    """Process weight data into both GarminBodyWeight and unified BodyWeight."""
    from .models import GarminBodyWeight
    from healthconnect.models import BodyWeight
    from decimal import Decimal
    
    weight_data = record.data
    weight_kg = weight_data.get('weight')
    
    if weight_kg:
        # Create Garmin-specific record
        garmin_weight, _ = GarminBodyWeight.objects.update_or_create(
            user=record.profile,
            datetime=record.date,
            defaults={
                'weight_kg': weight_kg,
                'source_type': 'garmin_scale',
            }
        )
        
        # Create unified BodyWeight record
        weight_lbs = Decimal(str(weight_kg)) * Decimal('2.20462')
        BodyWeight.objects.update_or_create(
            user=record.profile,
            source='garmin',
            source_id=str(garmin_weight.id),
            defaults={
                'datetime': record.date,
                'weight_lbs': weight_lbs.quantize(Decimal('0.01')),
            }
        )

def _handle_hydration(record):
    """Process hydration data and update DailyHealthSummary."""
    from healthconnect.models import DailyHealthSummary
    from django.db.models import F
    
    hydration_data = record.data
    hydration_ml = hydration_data.get('valueInML') or hydration_data.get('goalInML')
    
    if hydration_ml and hydration_ml > 0:
        # Convert ml to ounces
        hydration_ounces = hydration_ml * 0.033814
        
        summary, _ = DailyHealthSummary.objects.get_or_create(
            profile=record.profile,
            date=record.date
        )
        summary.water_ounces_total = F('water_ounces_total') + hydration_ounces
        summary.save()
5. API Views (garminconnect/api_views.py)
Enhanced Sync Endpoint
class GarminConnectViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Triggers background sync task for authenticated user."""
        sync_garmin_data.delay(request.user.id)
        return Response(
            {"status": "Garmin sync process started"},
            status=status.HTTP_202_ACCEPTED
        )
Unified Daily Summary Access
The existing DailyHealthSummaryViewSet in healthconnect/api_views.py already provides access to the unified data and will automatically include Garmin Connect data once processed.

6. Migration Strategy
Phase 1: New Architecture Alongside Existing
Add new models and tasks without removing existing ones
Run both systems in parallel during transition
Verify data consistency between old and new approaches
Phase 2: Data Migration
Create script to backfill existing Garmin data into new staging model
Process historical data through new normalization pipeline
Verify unified DailyHealthSummary contains all historical data
Phase 3: Cleanup
Remove old direct-processing logic
Update any references to old data flow
Keep existing Garmin* models for backward compatibility
Implementation Steps
1. Database Changes
Add GarminRawData staging model
Add missing fields to existing Garmin models (source_id, better indexing)
Create migration script for historical data
2. Service Layer
Create GarminAPIClient with staging support
Update existing configure_garmin_client to work with new service
3. Background Processing
Create sync_garmin_data task for staging
Create process_staged_garmin_data task for normalization
Update existing sync tasks to use new pipeline
4. Normalization Logic
Create garmin_normalizers.py with handlers for each data type
Implement aggregation logic for DailyHealthSummary
Handle CardioCoin rewards in normalization phase
5. API Integration
Update sync endpoints to use new background tasks
Ensure unified daily summary API works with Garmin data
Add data validation and error handling
6. Testing
Test each data type processing pipeline
Verify unified DailyHealthSummary aggregation
Test background task reliability and error handling
Performance test with large datasets
Benefits of New Architecture
Unified Data Access: Single API endpoint for all health data regardless of source
Better Performance: Pre-aggregated daily summaries for fast dashboard queries
Improved Reliability: Staging model prevents data loss during processing failures
Enhanced Maintainability: Clear separation of concerns between ingestion, processing, and aggregation
Scalability: Background processing prevents blocking user requests
Data Consistency: All sources feed into same normalized models and summary tables
Success Criteria
 New staging model successfully stores raw Garmin data
 Normalization tasks correctly process staged data into unified models
 DailyHealthSummary contains accurate aggregated data from Garmin Connect
 Existing functionality (CardioCoin rewards, etc.) preserved
 API performance meets requirements for dashboard queries
 Background processing handles errors gracefully
 Historical data migration completed successfully
 Documentation updated to reflect new architecture
This architecture provides a solid foundation for scaling Garmin Connect integration while maintaining compatibility with the existing Health Connect system and enabling unified health data analytics across all sources.