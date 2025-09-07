from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from common.models import WeightUnit
from django.utils import timezone

User = get_user_model()

class WeightUnit(models.Model):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=10)
    conversion_rate_to_kg = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        help_text="Multiply by this rate to convert to kg"
    )

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    def convert_to(self, value: Decimal, target_unit: 'WeightUnit') -> Decimal:
        """Convert a value from this unit to another unit"""
        # First convert to kg, then to target unit
        kg_value = value * self.conversion_rate_to_kg
        return kg_value / target_unit.conversion_rate_to_kg

    @classmethod
    def get_default_unit(cls):
        """Get the default weight unit (pounds)"""
        try:
            return cls.objects.get(symbol='lbs')
        except cls.DoesNotExist:
            # If pounds doesn't exist, create it
            return cls.objects.create(
                name='Pounds',
                symbol='lbs',
                conversion_rate_to_kg=Decimal('0.453592')
            )

    class Meta:
        ordering = ['name']

class WeightRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_records')
    weight = models.FloatField()
    unit = models.ForeignKey(WeightUnit, on_delete=models.PROTECT, default=WeightUnit.get_default_unit)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    @property
    def weight_in_kg(self) -> Decimal:
        """Get the weight in kilograms"""
        # Ensure weight is treated as Decimal for calculation
        return Decimal(str(self.weight)) * self.unit.conversion_rate_to_kg
    
    @property
    def weight_in_lbs(self) -> Decimal:
        """Get the weight in pounds"""
        # Ensure weight is treated as Decimal for calculation
        return Decimal(str(self.weight))

    def get_weight_in(self, target_unit: WeightUnit) -> Decimal:
        """Get the weight in a specific unit"""
        # Ensure weight is treated as Decimal for calculation
        return self.unit.convert_to(Decimal(str(self.weight)), target_unit)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username}'s weight: {self.weight}{self.unit.symbol} on {self.date}"


class WeightGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_goals')
    start_weight = models.FloatField()
    start_unit = models.ForeignKey(WeightUnit, on_delete=models.PROTECT, related_name='+', default=WeightUnit.get_default_unit)
    target_weight = models.FloatField()
    target_unit = models.ForeignKey(WeightUnit, on_delete=models.PROTECT, related_name='+', default=WeightUnit.get_default_unit)
    target_date = models.DateField()
    start_date = models.DateField(default=timezone.now) # Added start date

    @property
    def start_weight_in_kg(self) -> Decimal:
        """Get the start weight in kilograms"""
        return Decimal(str(self.start_weight)) * self.start_unit.conversion_rate_to_kg

    @property
    def target_weight_in_kg(self) -> Decimal:
        """Get the target weight in kilograms"""
        return Decimal(str(self.target_weight)) * self.target_unit.conversion_rate_to_kg

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_weight_goal')
        ]
    def __str__(self):
        return f"{self.user.username}'s goal: {self.target_weight}{self.target_unit.symbol} by {self.target_date}"

# --- Garmin Connect Integration Models ---

class GarminCredentials(models.Model):
    """Stores Garmin Connect authentication details for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='garmin_credentials')
    garmin_email = models.EmailField(unique=True, help_text="User's Garmin Connect email address.")
    # Store session/token data securely. JSONField is flexible.
    # DO NOT store the password here.
    session_data = models.JSONField(null=True, blank=True, help_text="Garmin Connect session/token data.")
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last successful data sync.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Garmin Credentials for {self.user.username}"

    class Meta:
        verbose_name_plural = "Garmin Credentials"


class GarminDailySteps(models.Model):
    """Stores daily step count data synced from Garmin Connect."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='garmin_daily_steps')
    date = models.DateField(help_text="The date for which the steps were recorded.")
    steps = models.PositiveIntegerField(help_text="Total steps recorded for the day.")
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.steps} steps"

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date') # Ensure only one record per user per day
        verbose_name_plural = "Garmin Daily Steps"


class GarminActivity(models.Model):
    """Stores activity data synced from Garmin Connect."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='garmin_activities')
    activity_id = models.BigIntegerField(unique=True, help_text="Unique Garmin activity ID.")
    name = models.CharField(max_length=255, help_text="Name of the activity.")
    activity_type = models.CharField(max_length=100, help_text="Type of activity (e.g., running, cycling).")
    start_time_utc = models.DateTimeField(help_text="Start time of the activity in UTC.")
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Duration in seconds.")
    distance_meters = models.FloatField(null=True, blank=True, help_text="Distance in meters.")
    calories = models.FloatField(null=True, blank=True, help_text="Calories burned.")
    average_hr = models.FloatField(null=True, blank=True, help_text="Average heart rate.")
    max_hr = models.FloatField(null=True, blank=True, help_text="Maximum heart rate.")
    # Store the full raw data from Garmin API for future use or debugging
    raw_data = models.JSONField(null=True, blank=True, help_text="Raw JSON data from Garmin API.")
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.activity_id}) on {self.start_time_utc.date()}"

    class Meta:
        ordering = ['-start_time_utc']
        verbose_name_plural = "Garmin Activities"


class SweatScoreWeights(models.Model):
    """Stores configurable weights for sweat score calculation."""
    ZONE_CHOICES = [
        (0, 'Zone 0 - Below Zone 1'),
        (1, 'Zone 1 - Very Light'),
        (2, 'Zone 2 - Light'),
        (3, 'Zone 3 - Moderate'),
        (4, 'Zone 4 - Hard'),
        (5, 'Zone 5 - Maximum'),
    ]

    zone = models.IntegerField(choices=ZONE_CHOICES, unique=True, help_text="Heart rate zone number")
    name = models.CharField(max_length=100, help_text="Descriptive name for the zone")
    perceived_effort = models.CharField(max_length=100, help_text="Perceived effort description")
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Points per minute for this zone"
    )

    def __str__(self):
        return f"Zone {self.zone}: {self.name} ({self.weight} pts/min)"

    class Meta:
        ordering = ['zone']
        verbose_name = "Sweat Score Weight"
        verbose_name_plural = "Sweat Score Weights"
