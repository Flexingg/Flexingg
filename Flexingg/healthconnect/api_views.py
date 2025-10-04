from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from . import models
from . import serializers
from core.api_views import router


class HealthConnectDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.HealthConnectData.objects.all()
    serializer_class = serializers.HealthConnectDataSerializer
    permission_classes = [IsAuthenticated]


class HealthConnectRawDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.HealthConnectRawData.objects.all()
    serializer_class = serializers.HealthConnectRawDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user)


class BodyWeightViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.BodyWeight.objects.all()
    serializer_class = serializers.BodyWeightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class SleepSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.SleepSession.objects.all()
    serializer_class = serializers.SleepSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class NutritionEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.NutritionEntry.objects.all()
    serializer_class = serializers.NutritionEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class StepRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.StepRecord.objects.all()
    serializer_class = serializers.StepRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class ExerciseSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ExerciseSession.objects.all()
    serializer_class = serializers.ExerciseSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class BloodPressureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.BloodPressure.objects.all()
    serializer_class = serializers.BloodPressureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class MetricSampleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.MetricSample.objects.all()
    serializer_class = serializers.MetricSampleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class HydrationEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.HydrationEntry.objects.all()
    serializer_class = serializers.HydrationEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class BodyCompositionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.BodyComposition.objects.all()
    serializer_class = serializers.BodyCompositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class MenstruationPeriodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.MenstruationPeriod.objects.all()
    serializer_class = serializers.MenstruationPeriodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class DailyHealthSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.DailyHealthSummary.objects.all()
    serializer_class = serializers.DailyHealthSummarySerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = {
        'date': ['exact', 'gte', 'lte', 'gt', 'lt']
    }

    def get_queryset(self):
        # DailyHealthSummary uses 'profile' FK
        return self.queryset.filter(profile=self.request.user)


# Register routes
router.register(r'health-connect-data', HealthConnectDataViewSet)
router.register(r'health-connect-raw', HealthConnectRawDataViewSet)
router.register(r'body-weight', BodyWeightViewSet, basename="hc-body-weight")
router.register(r'sleep-sessions', SleepSessionViewSet)
router.register(r'nutrition-entries', NutritionEntryViewSet, basename="hc-nutrition-entries")
router.register(r'step-records', StepRecordViewSet)
router.register(r'exercise-sessions', ExerciseSessionViewSet)
router.register(r'blood-pressure', BloodPressureViewSet)
router.register(r'metric-samples', MetricSampleViewSet)
router.register(r'hydration-entries', HydrationEntryViewSet)
router.register(r'body-composition', BodyCompositionViewSet)
router.register(r'menstruation-periods', MenstruationPeriodViewSet)
router.register(r'daily-health-summaries', DailyHealthSummaryViewSet)
