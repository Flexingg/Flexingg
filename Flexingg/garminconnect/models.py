
from django.db import models
import uuid
from django.utils import timezone
from core.models import UserProfile


class Garmin_Auth(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    oauth_token = models.CharField(primary_key=True, max_length=10000) # Store session/token data securely. JSONField is flexible.
    oauth_token_secret = models.CharField(max_length=10000) # DO NOT store the password here.    
    mfa_token = models.CharField(max_length=10000, blank=True, null=True) # Prompt for MFA using your app's adaptive user flow once per device/session.    
    mfa_expiration_timestamp = models.DateTimeField(blank=True, null=True)  
    domain = models.CharField(max_length=10000)
    scope = models.CharField(max_length=10000)
    jti = models.CharField(max_length=10000)
    token_type = models.CharField(max_length=10000)
    access_token = models.CharField(max_length=10000)
    refresh_token = models.CharField(max_length=10000)
    expires_in = models.IntegerField(null=True, blank=True)    
    expires_at = models.IntegerField(null=True, blank=True)    #pk a/very long character field
    refresh_token_expires_in = models.IntegerField(null=True, blank=True, default=10000)    
    refresh_token_expires_at = models.IntegerField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last successful data sync.")    # Formats automatically. Essential to monitor sync frequency!
    last_sync_attempt = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last sync attempt (successful or failed).") # Initial sync flow + error handling
    garmin_email = models.EmailField(blank=True, null=True, help_text="Garmin Connect email address used for linking.")


    def expired(self):        
        if self.expires_at is None:    
            return True
            
        return self.expires_at < timezone.now().timestamp()    

    def refresh_expired(self):    
        return self.refresh_token_expires_at < timezone.now().timestamp()

    def __str__(self):  
        return f"{self.token_type.title()} {self.access_token[:20]}..."


class GarminCredentials(models.Model):    
    """Stores Garmin Connect authentication details for a user."""    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)    
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='garmin_credentials')    
    garmin_email = models.EmailField(unique=True, help_text="User's Garmin Connect email address.")    
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
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='garmin_daily_steps')    
    date = models.DateField(help_text="The date for which the steps were recorded.")

    steps = models.PositiveIntegerField(help_text="Total steps recorded for the day.")

    def __str__(self):    
        return f"{self.user.username} - {self.date}: {self.steps} steps"

    class Meta:  
        ordering = ['-date']  
        unique_together = ('user', 'date') # Ensure only one record per user per day
        verbose_name_plural = "Garmin Daily Steps"

class GarminActivity(models.Model):  
    """Stores activity data synced from Garmin Connect."""  
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='garmin_activities')
    activity_id = models.BigIntegerField(unique=True, help_text="Unique Garmin activity ID.")    
    name = models.CharField(max_length=255, help_text="Name of the activity.")   
    activity_type = models.CharField(max_length=100, help_text="Type of activity (e.g., running, cycling).")      
    start_time_utc = models.DateTimeField(help_text="Start time of the activity in UTC.")    
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Duration in seconds.")
    distance_meters = models.FloatField(null=True, blank=True, help_text="Distance in meters.")    
    calories = models.FloatField(null=True, blank=True, help_text="Calories burned.")  
    average_hr = models.FloatField(null=True, blank=True, help_text="Average heart rate.")  
    max_hr = models.FloatField(null=True, blank=True, help_text="Maximum heart rate.")  
    # Store the full raw data from Garmin API for future use or debugging.
    raw_data = models.JSONField(null=True, blank=True, help_text="Raw JSON data from Garmin API.")  
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):  
        return f"{self.user.username} - {self.name} ({self.activity_id}) on {self.start_time_utc.date()}"