from rest_framework import serializers
from .models import (
    ColorPreferences, Friendship, Gear, Transaction, SweatScoreWeights,
    ConnectedService, DataPriority, Workout, UnifiedWorkoutExercise,
    UnifiedWorkoutSet, Sleep, DailySteps, DailyWater, NutritionEntry,
    BodyWeight, ArchivedWorkout, WorkoutConflict, Level, IntegrationIdea
)

class ColorPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorPreferences
        fields = [
            'user', 'surface', 'on_surface', 'primary', 'on_primary',
            'secondary', 'on_secondary', 'tertiary', 'on_tertiary',
            'surface_variant', 'on_surface_variant', 'outline', 'error'
        ]

class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friendship
        fields = [
            'uuid', 'from_user', 'to_user', 'status', 'created_at', 'updated_at'
        ]

class GearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gear
        fields = [
            'name', 'rarity', 'slot', 'str_bonus', 'end_bonus', 'fcs_bonus',
            'rcv_bonus', 'lck_bonus', 'description'
        ]

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'currency_type', 'amount', 'xp_awarded',
            'created_at', 'garmin_activity'
        ]

class SweatScoreWeightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SweatScoreWeights
        fields = ['zone', 'name', 'perceived_effort', 'weight']

class ConnectedServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedService
        fields = ['user', 'service_name', 'auth_data', 'created_at', 'updated_at']

class DataPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPriority
        fields = ['user', 'data_type', 'source', 'rank']

class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'source', 'source_id', 'start_time',
            'end_time', 'duration_seconds', 'data'
        ]

class UnifiedWorkoutExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnifiedWorkoutExercise
        fields = [
            'id', 'workout', 'exercise_name', 'note', 'timestamp',
            'successes', 'failures'
        ]

class UnifiedWorkoutSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnifiedWorkoutSet
        fields = [
            'id', 'workout_exercise', 'set_order', 'reps', 'weight_value',
            'weight_unit', 'completed_reps', 'completed_weight_value',
            'completed_weight_unit', 'rpe', 'completed_rpe', 'is_amrap',
            'is_completed', 'timestamp', 'is_warmup', 'notes'
        ]

class SleepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sleep
        fields = ['id', 'user', 'source', 'source_id', 'start_time', 'end_time', 'data']

class DailyStepsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySteps
        fields = ['id', 'user', 'source', 'source_id', 'date', 'steps', 'data']

class DailyWaterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyWater
        fields = ['id', 'user', 'source', 'source_id', 'date', 'amount_ounces', 'data']

class NutritionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionEntry
        fields = [
            'id', 'user', 'source', 'source_id', 'datetime', 'food_name',
            'quantity_description', 'quantity_grams', 'calories',
            'protein_grams', 'fat_grams', 'carbs_grams', 'data'
        ]

class BodyWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyWeight
        fields = ['id', 'user', 'source', 'source_id', 'datetime', 'weight_lbs', 'data']

class ArchivedWorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedWorkout
        fields = [
            'id', 'user', 'source', 'source_id', 'start_time', 'end_time',
            'duration_seconds', 'data', 'archived_reason', 'archived_at',
            'linked_primary_workout'
        ]

class WorkoutConflictSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutConflict
        fields = [
            'id', 'user', 'primary_workout', 'archived_workout', 'conflict_type',
            'conflict_score', 'resolved_at', 'resolution_method', 'created_at'
        ]

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['level_number', 'xp_required', 'created_at']

class IntegrationIdeaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationIdea
        fields = ['id', 'user', 'idea_text', 'created_at', 'metadata']