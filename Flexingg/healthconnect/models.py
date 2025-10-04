from django.db import models
from core.models import UserProfile


class HealthConnectData(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='health_data')
    method = models.CharField(max_length=50)  # e.g., 'steps', 'heartRate'
    record_id = models.CharField(max_length=255, db_index=True)  # from _id in API response
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data = models.JSONField()  # Raw data object from Health Connect
    app_source = models.CharField(max_length=255)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'method', 'record_id')
        ordering = ['-start_time']
        verbose_name = "Health Connect Data"
        verbose_name_plural = "Health Connect Data"

    def __str__(self):
        return f"{self.method} - {self.start_time} ({self.profile.username})"



class HealthConnectRawData(models.Model):
    """
    STAGING MODEL: Quick write-only store of raw JSON from the HC Gateway.
    Kept separate from the normalized models so ingestion is fast and non-blocking.
    """
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='raw_health_data')
    method = models.CharField(max_length=50, db_index=True)
    record_id = models.CharField(max_length=255, db_index=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data = models.JSONField()
    app_source = models.CharField(max_length=255, blank=True)
    is_processed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'method', 'record_id')
        ordering = ['-start_time']
        verbose_name = "Raw Health Connect Data"

    def __str__(self):
        return f"raw:{self.method} {self.start_time} ({self.profile.username})"


class BodyWeight(models.Model):
    """Normalized model for individual weight entries."""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='body_weights')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    datetime = models.DateTimeField(db_index=True)
    weight_lbs = models.DecimalField(max_digits=7, decimal_places=2)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Body Weight"

    def __str__(self):
        return f"{self.user.username} - {self.weight_lbs} lbs @ {self.datetime}"


class SleepSession(models.Model):
    """Normalized model for individual sleep sessions."""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sleep_sessions')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = "Sleep Session"

    def __str__(self):
        return f"{self.user.username} Sleep {self.start_time} -> {self.end_time}"


# --- Additional normalized models for Health Connect types ---
class NutritionEntry(models.Model):
    """Normalized nutrition entry (one record may contain multiple nutrients)."""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='nutrition_entries')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    datetime = models.DateTimeField(db_index=True)
    calories = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    carbs_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fat_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Nutrition Entry"

    def __str__(self):
        return f"{self.user.username} Nutrition @{self.datetime} ({self.calories or 0} kcal)"


class StepRecord(models.Model):
    """
    Normalized steps record. Use this for discrete step records coming from Health Connect.
    For aggregated daily totals prefer DailyHealthSummary.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='step_records')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    steps = models.PositiveIntegerField(default=0)
    cadence = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # steps cadence
    distance_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = "Step Record"

    def __str__(self):
        return f"{self.user.username} Steps {self.steps} @ {self.start_time}"


class ExerciseSession(models.Model):
    """
    Represents an exercise / activity session (exerciseSession from HC).
    Stores high-level activity metadata for normalization and analytics.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='exercise_sessions')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    activity_type = models.CharField(max_length=100, db_index=True)  # e.g., 'running', 'cycling'
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    calories_burned = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    average_heart_rate = models.PositiveIntegerField(null=True, blank=True)
    total_power = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = "Exercise Session"

    def __str__(self):
        return f"{self.user.username} {self.activity_type} {self.start_time}"


class BloodPressure(models.Model):
    """Stores discrete blood pressure measurements."""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='blood_pressure_readings')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    datetime = models.DateTimeField(db_index=True)
    systolic = models.PositiveIntegerField()
    diastolic = models.PositiveIntegerField()
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Blood Pressure"

    def __str__(self):
        return f"{self.user.username} BP {self.systolic}/{self.diastolic} @ {self.datetime}"


class MetricSample(models.Model):
    """
    Generic time-series metric for values like heartRate, oxygenSaturation, respiratoryRate, vo2Max, etc.
    Use metric field to identify the measurement type.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='metric_samples')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, blank=True, null=True)
    datetime = models.DateTimeField(db_index=True)
    metric = models.CharField(max_length=100, db_index=True)  # e.g., 'heartRate'
    value = models.DecimalField(max_digits=9, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Metric Sample"

    def __str__(self):
        return f"{self.user.username} {self.metric}={self.value}{(' ' + self.unit) if self.unit else ''} @ {self.datetime}"


# Hydration, body composition and menstruation (specialized models)
class HydrationEntry(models.Model):
    """Normalized hydration records (e.g., water intake)."""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='hydration_entries')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    datetime = models.DateTimeField(db_index=True)
    volume_ml = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # convenience field in ounces for some UIs (optional)
    volume_ounces = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Hydration Entry"

    def __str__(self):
        vol = self.volume_ml or self.volume_ounces or 0
        return f"{self.user.username} Hydration {vol} @ {self.datetime}"


class BodyComposition(models.Model):
    """
    Stores body composition snapshots: body fat, lean mass, bone mass, etc.
    This complements the BodyWeight model for richer user profiling.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='body_composition')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    datetime = models.DateTimeField(db_index=True)
    body_fat_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lean_mass_kg = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    bone_mass_kg = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    visceral_fat_index = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime']
        verbose_name = "Body Composition"

    def __str__(self):
        return f"{self.user.username} BodyComp {self.body_fat_percent or 'N/A'}% @ {self.datetime}"


class MenstruationPeriod(models.Model):
    """
    Records a menstruation period / cycle window. Health Connect may report start/end and flow metadata.
    """
    FLOW_CHOICES = [
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy'),
        ('spotting', 'Spotting'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='menstruation_periods')
    source = models.CharField(max_length=50, default='healthconnect')
    source_id = models.CharField(max_length=255, unique=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True)
    average_flow = models.CharField(max_length=16, choices=FLOW_CHOICES, blank=True, null=True)
    symptoms = models.JSONField(blank=True, null=True)  # e.g., cramps, mood, etc.
    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Menstruation Period"

    def __str__(self):
        return f"{self.user.username} Period {self.start_date}{(' -> ' + str(self.end_date)) if self.end_date else ''}"


class DailyHealthSummary(models.Model):
    """
    AGGREGATION MODEL: One row per user per date with pre-computed daily totals
    for fast dashboard queries and analytics.
    """
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='daily_health_summaries')
    date = models.DateField(db_index=True)

    # Aggregated metrics
    steps_total = models.PositiveIntegerField(default=0)
    # Active (burned) calories recorded from exercise/activities (kcal)
    active_calories_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    calories_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    protein_grams_total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    carbs_grams_total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    fat_grams_total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    water_ounces_total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    # Sleep total in minutes (allows fractional minutes)
    sleep_minutes_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('profile', 'date')
        ordering = ['-date']
        verbose_name = "Daily Health Summary"

    def __str__(self):
        return f"{self.profile.username} - {self.date}"