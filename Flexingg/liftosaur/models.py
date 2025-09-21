
import uuid
from django.db import models
from core.models import UserProfile


class Exercise(models.Model):
    """
    Represents a specific type of exercise.
    e.g., 'Squat (Barbell)', 'Face Pull (Cable)'
    """
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class UserExerciseStat(models.Model):
    """
    Stores user-specific stats for an exercise, like their 1-rep max.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='exercise_stats')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    rm1_value = models.FloatField(blank=True, null=True)
    rm1_unit = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'exercise')

    def __str__(self):
        return f"{self.user.username}'s 1RM for {self.exercise.name}: {self.rm1_value}{self.rm1_unit}"


class Workout(models.Model):
    """
    Represents a single workout session.
    """
    id = models.CharField(max_length=255, primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='workouts')
    timestamp = models.DateTimeField()
    name = models.CharField(max_length=255, blank=True, null=True)
    # Storing these as CharFields for simplicity, could be ForeignKeys to Gym/Program models
    gym_id = models.CharField(max_length=255, blank=True, null=True)
    program_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Workout by {self.user.username} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class WorkoutExercise(models.Model):
    """
    An exercise performed during a workout session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, null=True, blank=True)
    # Using a text field for the exercise name as it appears in the log
    exercise_name = models.CharField(max_length=255)
    note = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField()
    successes = models.IntegerField(default=0)
    failures = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.exercise_name}"

    def get_volume(self, unit='lb'):
        """
        Calculate total volume for this exercise: sum(completed_weight * completed_reps)
        Converts all to specified unit if needed (assumes kg to lb conversion).
        """
        total = 0
        for set_instance in self.sets.all():
            if set_instance.completed_weight_value and set_instance.completed_reps > 0:
                weight = set_instance.completed_weight_value
                if set_instance.completed_weight_unit == 'kg':
                    weight *= 2.20462  # Convert to lb
                total += weight * set_instance.completed_reps
        if unit == 'kg':
            total /= 2.20462
        return total
class WorkoutSet(models.Model):
    """
    A single set (working or warmup) in a workout exercise.
    Captures planned and completed reps/weight from Liftosaur JSON.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout_exercise = models.ForeignKey(WorkoutExercise, on_delete=models.CASCADE, related_name='sets')
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

    def get_set_volume(self, unit='lb'):
        """
        Volume for this single set: completed_weight * completed_reps
        """
        if not self.completed_weight_value or self.completed_reps <= 0:
            return 0
        weight = self.completed_weight_value
        if self.completed_weight_unit == 'kg':
            weight *= 2.20462  # to lb
        elif self.weight_unit == 'kg' and not self.completed_weight_unit:
            weight *= 2.20462
        total = weight * self.completed_reps
        if unit == 'kg':
            total /= 2.20462
        return total


class BodyMeasurement(models.Model):
    """
    Stores user body measurements, such as bodyweight, over time.
    Data sourced from Liftosaur JSON exports.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='body_measurements')
    measurement_type = models.CharField(max_length=50, default='bodyweight')
    value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = ('user', 'measurement_type', 'timestamp')

    def __str__(self):
        return f"{self.user.username} - {self.measurement_type}: {self.value} {self.unit} on {self.timestamp.date()}"


class Program(models.Model):
    """
    Stores a user's Liftosaur program data from JSON export.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='liftosaur_programs')
    external_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'external_id')

    def __str__(self):
        return f"{self.user.username} - {self.name}"