from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
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
    liftosaur_user_id = models.CharField(max_length=255, blank=True, null=True, help_text="Liftosaur user ID for integration")
    liftosaur_session_token = models.CharField(max_length=255, blank=True, null=True, help_text="Liftosaur session token for API access")

    # Health Connect integration fields
    hc_username = models.CharField(max_length=255, blank=True, null=True, help_text="HCGateway username")
    hc_password = models.CharField(max_length=255, blank=True, null=True, help_text="HCGateway password (hashed)")
    hc_token = models.TextField(blank=True, null=True, help_text="HCGateway access token")
    hc_refresh_token = models.TextField(blank=True, null=True, help_text="HCGateway refresh token")
    hc_token_expiry = models.DateTimeField(null=True, blank=True, help_text="Token expiry time")
    hc_last_sync = models.DateTimeField(null=True, blank=True, help_text="Last Health Connect sync time")

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
        Transaction.objects.create(
            user=self,
            currency_type='gym_gems',
            amount=amount,
            garmin_activity=garmin_activity
        )
        self.gym_gems += amount
        self.save()

    def earn_cardio_coins(self, amount, garmin_activity=None) -> None:
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
        'garminconnect.GarminActivity',
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

@receiver(post_save, sender=UserProfile)
def create_default_data_priorities(sender, instance, created, **kwargs):
    if created:
        # Workout priorities: Garmin primary, Liftosaur secondary
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='workout',
            source='garmin',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='workout',
            source='liftosaur',
            defaults={'rank': 2}
        )
        # Sleep priorities: Health Connect primary
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='sleep',
            source='healthconnect',
            defaults={'rank': 1}
        )
        # Steps priorities: Garmin primary, Health Connect secondary
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='steps',
            source='garmin',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='steps',
            source='healthconnect',
            defaults={'rank': 2}
        )


class ConnectedService(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='connected_services')
    service_name = models.CharField(max_length=50, choices=[('garmin', 'Garmin'), ('healthconnect', 'Health Connect'), ('liftosaur', 'Liftosaur')])
    auth_data = models.JSONField(help_text="Stores authentication tokens and other service-specific data.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'service_name')
        verbose_name = "Connected Service"
        verbose_name_plural = "Connected Services"

    def __str__(self):
        return f"{self.user.username}'s {self.get_service_name_display()} Connection"

class DataPriority(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='data_priorities')
    data_type = models.CharField(max_length=50, choices=[('workout', 'Workout'), ('sleep', 'Sleep'), ('steps', 'Steps')])
    source = models.CharField(max_length=50, choices=[('garmin', 'Garmin'), ('healthconnect', 'Health Connect'), ('liftosaur', 'Liftosaur')])
    rank = models.IntegerField(help_text="Priority rank (1 is highest)")

    class Meta:
        unique_together = ('user', 'data_type', 'rank')
        ordering = ['user', 'data_type', 'rank']
        verbose_name = "Data Priority"
        verbose_name_plural = "Data Priorities"

    def __str__(self):
        return f"{self.user.username} - {self.get_data_type_display()}: Rank {self.rank} is {self.get_source_display()}"

class Workout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_workouts')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    data = models.JSONField(help_text="Normalized workout data")

    class Meta:
        unique_together = ('user', 'source', 'source_id')
        ordering = ['-start_time']
        verbose_name = "Workout"
        verbose_name_plural = "Workouts"

    def __str__(self):
        return f"Workout for {self.user.username} from {self.source} on {self.start_time.date()}"

class Sleep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_sleep')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    data = models.JSONField(help_text="Normalized sleep data")

    class Meta:
        unique_together = ('user', 'source', 'source_id')
        ordering = ['-start_time']
        verbose_name = "Sleep"
        verbose_name_plural = "Sleep Data"

    def __str__(self):
        return f"Sleep for {self.user.username} from {self.source} on {self.start_time.date()}"

class DailySteps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='unified_steps')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255, null=True, blank=True) # Steps data might not have a unique ID from source
    date = models.DateField()
    steps = models.PositiveIntegerField()
    data = models.JSONField(help_text="Normalized steps data", null=True, blank=True)


    class Meta:
        unique_together = ('user', 'source', 'date')
        ordering = ['-date']
        verbose_name = "Daily Steps"
        verbose_name_plural = "Daily Steps"

    def __str__(self):
        return f"Steps for {self.user.username} from {self.source} on {self.date}: {self.steps}"
