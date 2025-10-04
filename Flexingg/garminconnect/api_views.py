from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *
from core.api_views import router

class Garmin_AuthViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Garmin_Auth.objects.all()
    serializer_class = Garmin_AuthSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class GarminCredentialsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GarminCredentials.objects.all()
    serializer_class = GarminCredentialsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class GarminDailyStepsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GarminDailySteps.objects.all()
    serializer_class = GarminDailyStepsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class GarminActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GarminActivity.objects.all()
    serializer_class = GarminActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class GarminBodyWeightViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GarminBodyWeight.objects.all()
    serializer_class = GarminBodyWeightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    


router.register(r'garmin-auth', Garmin_AuthViewSet)
router.register(r'garmin-credentials', GarminCredentialsViewSet)
router.register(r'garmin-daily-steps', GarminDailyStepsViewSet)
router.register(r'garmin-activities', GarminActivityViewSet)
router.register(r'garmin-body-weight', GarminBodyWeightViewSet)