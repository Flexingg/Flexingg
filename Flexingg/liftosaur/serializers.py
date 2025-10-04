from rest_framework import serializers
from .models import (
    Exercise, UserExerciseStat, Workout, WorkoutExercise,
    WorkoutSet, BodyMeasurement, Program
)

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ['id', 'name']

class UserExerciseStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserExerciseStat
        fields = ['user', 'exercise', 'rm1_value', 'rm1_unit']

class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = ['id', 'user', 'timestamp', 'name', 'gym_id', 'program_id']

class WorkoutExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutExercise
        fields = [
            'id', 'workout', 'exercise', 'exercise_name', 'note',
            'timestamp', 'successes', 'failures'
        ]

class WorkoutSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutSet
        fields = [
            'id', 'workout_exercise', 'set_order', 'reps', 'weight_value',
            'weight_unit', 'completed_reps', 'completed_weight_value',
            'completed_weight_unit', 'rpe', 'completed_rpe', 'is_amrap',
            'is_completed', 'timestamp', 'is_warmup', 'notes'
        ]

class BodyMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyMeasurement
        fields = ['user', 'measurement_type', 'value', 'unit', 'timestamp']

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ['user', 'external_id', 'name', 'data', 'created_at', 'updated_at']