from rest_framework import serializers
from . import models


class HealthConnectDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HealthConnectData
        fields = '__all__'
        read_only_fields = ('is_processed', 'created_at')

class HealthConnectRawDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HealthConnectRawData
        fields = '__all__'
        read_only_fields = ('is_processed', 'created_at')


class BodyWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BodyWeight
        fields = '__all__'


class SleepSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SleepSession
        fields = '__all__'


class NutritionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NutritionEntry
        fields = '__all__'


class StepRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StepRecord
        fields = '__all__'


class ExerciseSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExerciseSession
        fields = '__all__'


class BloodPressureSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BloodPressure
        fields = '__all__'


class MetricSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MetricSample
        fields = '__all__'


class HydrationEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HydrationEntry
        fields = '__all__'


class BodyCompositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BodyComposition
        fields = '__all__'


class MenstruationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenstruationPeriod
        fields = '__all__'


class DailyHealthSummarySerializer(serializers.ModelSerializer):
    # Expose profile id and optional read-only aggregates
    profile = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.DailyHealthSummary
        fields = '__all__'
        read_only_fields = ('updated_at',)