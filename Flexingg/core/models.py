from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(AbstractUser):
    avatar = models.CharField(max_length=255, blank=True)      # Binary upload later
    gym_gems = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Currency used in store
    cardio_coins = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Currency used for skill upgrades and premium content
    str_stat = models.IntegerField(default=0)
    end_stat = models.IntegerField(default=0)
    fcs_stat = models.IntegerField(default=0)
    rcv_stat = models.IntegerField(default=0)
    lck_stat = models.IntegerField(default=0)
    level = models.IntegerField(default=1)    # Token tree experience and level system
    xp = models.IntegerField(default=0)
    height_ft = models.IntegerField(null=True, blank=True, help_text="Height in feet")
    height_in = models.IntegerField(null=True, blank=True, help_text="Height in inches")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in lbs.") #DecimalField is more precise than IntegerField for weight measurements
    sex = models.CharField(
        max_length=20,
        choices=[('male', 'Male'),('female', 'Female')],
        null=True, blank=True, help_text='Gender'
    )
    sync_debounce_minutes = models.IntegerField(default=60, null=True, blank=True, help_text="Minutes between automatic Garmin syncs (default: 60)")

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='profile_groups', blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
        related_query_name='profile',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='profile_users', blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
        related_query_name='profile',
    )

    following = models.ManyToManyField(
        'self', symmetrical=False, related_name='followers', blank=True,
    )

    blocking = models.ManyToManyField(
        'self', symmetrical=False, related_name='blockers', blank=True
    )


    def earn_gym_gems(self, amount, garmin_activity=None) -> None:
        from .models import Transaction
        Transaction.objects.create(
            user=self,
            currency_type='gym_gems',
            amount=amount,
            garmin_activity=garmin_activity
        )
        self.gym_gems += amount
        self.save()

    def earn_cardio_coins(self, amount, garmin_activity=None) -> None: 
        from .models import Transaction
        Transaction.objects.create(
            user=self,
            currency_type='cardio_coins',
            amount=amount,
            garmin_activity=garmin_activity
        )
        self.cardio_coins += amount
        self.save()


class ColorPreferences(models.Model):    
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='theme_colors')
    surface = models.CharField(max_length=7, default='#121212', help_text='Surface color')
    on_surface = models.CharField(max_length=7, default='#FFFFFF', help_text='On surface color')
    primary = models.CharField(max_length=7, default='#00f5d4', help_text='Primary color')
    on_primary = models.CharField(max_length=7, default='#000000', help_text='On primary color')
    secondary = models.CharField(max_length=7, default='#2a2a2a', help_text='Secondary color')
    on_secondary = models.CharField(max_length=7, default='#FFFFFF', help_text='On secondary color')
    tertiary = models.CharField(max_length=7, default='#333333', help_text='Tertiary color')
    on_tertiary = models.CharField(max_length=7, default='#FFFFFF', help_text='On tertiary color')
    surface_variant = models.CharField(max_length=7, default='#1f1f1f', help_text='Surface variant color')  
    on_surface_variant = models.CharField(max_length=7, default='#BDBDBD', help_text='On surface variant color')
    outline = models.CharField(max_length=7, default='#424242', help_text='Outline color')
    error = models.CharField(max_length=7, default='#F44336', help_text='Error color')

    def get_surface_color(self):  
        return self.surface

    def get_on_surface_color(self):  
        return self.on_surface

    def get_primary_color(self):  
        return self.primary

    def get_on_primary_color(self):  
        return self.on_primary

    def get_secondary_color(self):  
        return self.secondary
    
    def get_on_secondary_color(self):  
        return self.on_secondary

    def get_tertiary_color(self):  
        return self.tertiary

    def get_on_tertiary_color(self):  
        return self.on_tertiary

    def get_surface_variant_color(self):  
        return self.surface_variant

    def get_on_surface_variant_color(self):  
        return self.on_surface_variant

    def get_outline_color(self):  
        return self.outline
        
    def get_error_color(self): 
        return self.error
              
    def __str__(self):  
        return f"Color Preferences for {self.user.username}"


class Friendship(models.Model):         
    """Model to represent friendships between users."""         
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('blocked', 'Blocked') # Optional: if blocking should also reflect here
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique ID for this friendship.")  
    # The user who initiated the request    
    from_user = models.ForeignKey(UserProfile, related_name='friendship_requests_sent', on_delete=models.CASCADE)  
    # The user who received the request.
    to_user = models.ForeignKey(UserProfile, related_name='friendship_requests_received', on_delete=models.CASCADE)       
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', help_text="Status of this friendship request.")    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the friendship request was created.")    
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of when the friendship status was last updated.")    
    
    class Meta: 
        unique_together = ('from_user', 'to_user') # Ensure only one request between two users in one direction
        ordering = ['-created_at']

    def __str__(self):  
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"


class Gear(models.Model):    
    RARITY_CHOICES = [
        ('worn_out', 'Worn-Out'),
        ('standard_issue', 'Standard Issue'),
        ('pro_grade', 'Pro-Grade'),
        ('signature_series', 'Signature Series'),
        ('mythic_flex', 'Mythic Flex'),
    ]    
    SLOTS = (
        ('head', 'Head'),
        ('torso', 'Torso'),
        ('arms', 'Arms'),
        ('legs', 'Legs'),
        ('feet', 'Feet'),
    )

    name = models.CharField(max_length=100) 
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES) 
    slot = models.CharField(max_length=10, choices=SLOTS)    
    str_bonus = models.IntegerField(default=0)    
    end_bonus = models.IntegerField(default=0)    

    fcs_bonus = models.IntegerField(default=0)   
    rcv_bonus = models.IntegerField(default=0)    
    lck_bonus = models.IntegerField(default=0)    
    description = models.TextField(blank=True)

    def __str__(self):  
        return f"{self.name} ({self.rarity})"


class DailySteps(models.Model):    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='daily_steps')  
    calendar_date = models.DateField(default=timezone.now)    
    total_steps = models.IntegerField(default=0)  
    total_distance = models.FloatField(default=0) #Total distance (in miles) based on step count using 2.2 ft per step conversion. Updates each sync.    
    step_goal = models.IntegerField(default=10000)


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


class Transaction(models.Model):
    """Tracks currency transactions for users."""
    CURRENCY_CHOICES = [
        ('cardio_coins', 'Cardio Coins'),
        ('gym_gems', 'Gym Gems'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='transactions')
    currency_type = models.CharField(max_length=20, choices=CURRENCY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    garmin_activity = models.ForeignKey(
        'GarminActivity', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.user.username} earned {self.amount} {self.currency_type} on {self.created_at.date()}"


class SweatScoreWeights(models.Model):    
    """Stores configurable weights for sweat score calculation."""    
    ZONE_CHOICES = (
        (0, 'Zone 0 - Below Zone 1'),   
        (1, 'Zone 1 - Very Light'),
        (2, 'Zone 2 - Light'),
        (3, 'Zone 3 - Moderate'),
        (4, 'Zone 4 - Hard'),
        (5, 'Zone 5 - Maximum')                                  # LEVEL UP ARCHETYPE EMPHASIS: LEVEL 5 SIGNATURE SERIES TREES
    )    
    
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


@receiver(post_save, sender=UserProfile)
def create_color_preferences(sender, instance, created, **kwargs):  
    if created:  
        ColorPreferences.objects.create(user=instance)
