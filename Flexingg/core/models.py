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
    # Currency multipliers and fallback bodyweight (Phase 1.1)
    cardio_coins_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Personal multiplier for CardioCoins earnings"
    )
    gym_gems_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Personal multiplier for GymGems earnings"
    )
    bodyweight_lbs = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=200.00,
        help_text="Fallback bodyweight in lbs when synced weight is unavailable"
    )
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
    sync_debounce_minutes = models.IntegerField(default=60, null=True, blank=True, help_text="Minutes between automatic general syncs (default: 60)")
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last general sync")

    stat_card_config = models.JSONField(
        default=list,
        blank=True,
        help_text="Configuration for stat card order and visibility."
    )

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
        def _get_activity_time(obj):
            if obj is None:
                return None
            try:
                # model-like objects: common datetime fields
                for attr in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                    val = getattr(obj, attr, None)
                    if val:
                        return val
                # dict-like objects
                if isinstance(obj, dict):
                    for key in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                        if obj.get(key):
                            return obj.get(key)
            except Exception:
                return None
            return None

        activity_time = _get_activity_time(garmin_activity)
        if activity_time and getattr(self, 'date_joined', None) and activity_time < self.date_joined:
            # Do not award currency for activities that occurred before the user joined
            return
        Transaction.objects.create(
            user=self,
            currency_type='gym_gems',
            amount=amount,
            garmin_activity=garmin_activity
        )
        self.gym_gems += amount
        self.save()

    def earn_cardio_coins(self, amount, garmin_activity=None) -> None:
        def _get_activity_time(obj):
            if obj is None:
                return None
            try:
                for attr in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                    val = getattr(obj, attr, None)
                    if val:
                        return val
                if isinstance(obj, dict):
                    for key in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                        if obj.get(key):
                            return obj.get(key)
            except Exception:
                return None
            return None

        activity_time = _get_activity_time(garmin_activity)
        if activity_time and getattr(self, 'date_joined', None) and activity_time < self.date_joined:
            # Do not award currency for activities that occurred before the user joined
            return
        Transaction.objects.create(
            user=self,
            currency_type='cardio_coins',
            amount=amount,
            garmin_activity=garmin_activity
        )
        self.cardio_coins += amount
        self.save()

    def earn_xp(self, xp_points: int, garmin_activity=None) -> None:
        def _get_activity_time(obj):
            if obj is None:
                return None
            try:
                for attr in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                    val = getattr(obj, attr, None)
                    if val:
                        return val
                if isinstance(obj, dict):
                    for key in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                        if obj.get(key):
                            return obj.get(key)
            except Exception:
                return None
            return None

        activity_time = _get_activity_time(garmin_activity)
        if activity_time and getattr(self, 'date_joined', None) and activity_time < self.date_joined:
            # Do not award XP for activities that occurred before the user joined
            return
        Transaction.objects.create(
            user=self,
            currency_type='xp',
            amount=0,
            xp_awarded=int(xp_points),
            garmin_activity=garmin_activity
        )
        # store XP on user profile
        try:
            self.xp = int(self.xp) + int(xp_points)
        except Exception:
            self.xp = int(xp_points)
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
        ('xp', 'Experience Points'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='transactions')
    currency_type = models.CharField(max_length=20, choices=CURRENCY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # XP awarded associated with this transaction (if any). Stored as integer XP points.
    xp_awarded = models.IntegerField(default=0)
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
        # Workout priorities: Liftosaur primary
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='workout',
            source='liftosaur',
            defaults={'rank': 1}
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

        # Water priorities: Health Connect primary, Garmin secondary
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='water',
            source='healthconnect',
            defaults={'rank': 1}
        )
        DataPriority.objects.get_or_create(
            user=instance,
            data_type='water',
            source='garmin',
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
    data_type = models.CharField(max_length=50, choices=[('workout', 'Workout'), ('sleep', 'Sleep'), ('steps', 'Steps'), ('water', 'Water')])
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
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Duration in seconds.")
    data = models.JSONField(help_text="Normalized workout data")

    class Meta:
        unique_together = ('user', 'source', 'source_id')
        ordering = ['-start_time']
        verbose_name = "Workout"
        verbose_name_plural = "Workouts"

    def __str__(self):
        return f"Workout for {self.user.username} from {self.source} on {self.start_time.date()}"
    
    def get_total_volume(self, unit='lb'):
        """
        Robustly compute total lifting volume for this workout.
        For Liftosaur-source workouts this parses self.data (entries -> sets/warmupSets)
        and sums (completedWeight.value * completedReps) across all completed sets.
        Accepts both camelCase and snake_case keys and converts kg -> lb as needed.
        """
        total = 0.0
        try:
            if self.source == 'liftosaur' and isinstance(self.data, dict):
                entries = self.data.get('entries') or self.data.get('exercises') or []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    # handle working sets and warmup sets
                    for set_key in ('sets', 'warmupSets', 'warmup_sets', 'warmups'):
                        for s in entry.get(set_key, []) or []:
                            # reps: support camelCase and snake_case
                            reps = s.get('completedReps') or s.get('completed_reps') or s.get('reps') or 0
                            if reps is None:
                                reps = 0
                            # prefer completedWeight, fall back to weight
                            weight_obj = s.get('completedWeight') or s.get('completed_weight') or s.get('weight') or {}
                            weight_value = 0
                            weight_unit = s.get('weightUnit') or s.get('completedWeight', {}).get('unit') if isinstance(s.get('completedWeight'), dict) else (s.get('weightUnit') or 'lb')
                            if isinstance(weight_obj, dict):
                                weight_value = weight_obj.get('value') or weight_obj.get('weight') or 0
                                weight_unit = weight_obj.get('unit') or weight_unit or 'lb'
                            else:
                                try:
                                    weight_value = float(weight_obj)
                                except Exception:
                                    weight_value = 0
                            # skip sets without meaningful values
                            try:
                                w = float(weight_value)
                                r = float(reps)
                            except Exception:
                                continue
                            if w <= 0 or r <= 0:
                                continue
                            if str(weight_unit).lower().startswith('kg'):
                                w *= 2.20462
                            total += w * r
            # Fallback: if no liftosaur data parsed, try unified_exercises relation
            if total == 0.0:
                ex_qs = getattr(self, 'unified_exercises', None)
                if ex_qs is not None and hasattr(ex_qs, 'all'):
                    for ex in ex_qs.all():
                        if hasattr(ex, 'get_volume'):
                            total += float(ex.get_volume('lb') or 0)
        except Exception:
            # On any parsing error, do not raise — return 0.0 (safe fallback for analytics)
            total = 0.0

        if unit == 'kg':
            total /= 2.20462
        return total


class UnifiedWorkoutExercise(models.Model):
    """
    An exercise performed during a unified workout session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout = models.ForeignKey('core.Workout', on_delete=models.CASCADE, related_name='unified_exercises', null=True, blank=True)
    exercise_name = models.CharField(max_length=255, default='Unknown Exercise')
    note = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    successes = models.IntegerField(default=0)
    failures = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.exercise_name}"


class UnifiedWorkoutSet(models.Model):
    """
    A single set in a unified workout exercise.
    Captures planned and completed reps/weight from sources like Liftosaur.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout_exercise = models.ForeignKey('core.UnifiedWorkoutExercise', on_delete=models.CASCADE, related_name='sets')
    set_order = models.IntegerField()  # Positive for working sets, negative for warmups
    reps = models.FloatField(null=True, blank=True)  # Planned reps
    weight_value = models.FloatField(null=True, blank=True)
    weight_unit = models.CharField(max_length=10, default='lb', blank=True)
    completed_reps = models.IntegerField(default=0)
    completed_weight_value = models.FloatField(null=True, blank=True)
    completed_weight_unit = models.CharField(max_length=10, null=True, blank=True)
    rpe = models.IntegerField(null=True, blank=True)  # Planned RPE
    completed_rpe = models.IntegerField(null=True, blank=True)
    is_amrap = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(null=True, blank=True)  # Completion time
    is_warmup = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['set_order']

    def __str__(self):
        return f"Set {self.set_order} for {self.workout_exercise.exercise_name}: {self.completed_reps} reps @ {self.completed_weight_value}{self.completed_weight_unit or self.weight_unit}"


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
        verbose_name = "Daily Water"
        verbose_name_plural = "Daily Water Intake"

    def __str__(self):
        return f"Water for {self.user.username} from {self.source} on {self.date}: {self.amount_ounces}oz"


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
        verbose_name = "Nutrition Entry"
        verbose_name_plural = "Nutrition Entries"

    def __str__(self):
        return f"Nutrition for {self.user.username} from {self.source}: {self.food_name} ({self.calories} kcal)"


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
        verbose_name = "Body Weight"
        verbose_name_plural = "Body Weight Entries"

    def __str__(self):
        return f"Weight for {self.user.username} from {self.source}: {self.weight_lbs} lbs"


class ArchivedWorkout(models.Model):
    """Preserves workout data that was excluded due to conflicts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='archived_workouts')
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_seconds = models.FloatField(null=True, blank=True)
    data = models.JSONField(help_text="Original workout data before archiving")
    archived_reason = models.CharField(max_length=100, choices=[
        ('lower_priority', 'Lower Priority Source'),
        ('time_conflict', 'Time Conflict'),
        ('data_conflict', 'Data Conflict')
    ])
    archived_at = models.DateTimeField(auto_now_add=True)
    linked_primary_workout = models.ForeignKey('core.Workout', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_archived_workouts')

    class Meta:
        ordering = ['-archived_at']
        verbose_name = "Archived Workout"
        verbose_name_plural = "Archived Workouts"

    def __str__(self):
        return f"Archived {self.source} workout for {self.user.username} on {self.start_time.date()}"


class WorkoutConflict(models.Model):
    """Tracks conflicts between workout data from different sources"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='workout_conflicts')
    primary_workout = models.ForeignKey('core.Workout', on_delete=models.CASCADE, related_name='primary_conflicts')
    archived_workout = models.ForeignKey('core.ArchivedWorkout', on_delete=models.CASCADE, related_name='archived_conflicts')
    conflict_type = models.CharField(max_length=50, choices=[
        ('time_overlap', 'Time Overlap'),
        ('data_mismatch', 'Data Mismatch'),
        ('duplicate_activity', 'Duplicate Activity')
    ])
    conflict_score = models.FloatField(help_text="Confidence score of the conflict (0-1)")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_method = models.CharField(max_length=50, choices=[
        ('auto_priority', 'Automatic Priority'),
        ('manual_review', 'Manual Review'),
        ('data_merge', 'Data Merge')
    ], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Workout Conflict"
        verbose_name_plural = "Workout Conflicts"

    def __str__(self):
        return f"Conflict: {self.primary_workout.source} vs {self.archived_workout.source} for {self.user.username}"


# Level model for XP progression (Phase 3.1)
class Level(models.Model):
    """
    Represents a level and the cumulative XP required to reach it.
    level_number is unique and xp_required is the cumulative XP threshold.
    """
    level_number = models.IntegerField(unique=True)
    xp_required = models.BigIntegerField(help_text="Cumulative XP required to reach this level")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['level_number']
        verbose_name = "Level"
        verbose_name_plural = "Levels"

    def __str__(self):
        return f"Level {self.level_number} ({self.xp_required} XP)"