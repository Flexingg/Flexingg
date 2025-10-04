from rest_framework import viewsets, routers
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *

class ColorPreferencesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user color preferences.
    """
    queryset = ColorPreferences.objects.all()
    serializer_class = ColorPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only allow users to see their own color preferences."""
        return self.queryset.filter(user=self.request.user)

class FriendshipViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing friendships.
    """
    queryset = Friendship.objects.all()
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

class GearViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view available gear. Assumes gear is managed by admins.
    """
    queryset = Gear.objects.all()
    serializer_class = GearSerializer
    permission_classes = [IsAuthenticated]

class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user transactions.
    """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only allow users to see their own transactions."""
        return self.queryset.filter(user=self.request.user)

class SweatScoreWeightsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view sweat score weights. Assumes these are system-defined.
    """
    queryset = SweatScoreWeights.objects.all()
    serializer_class = SweatScoreWeightsSerializer
    permission_classes = [IsAuthenticated]

class ConnectedServiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user-connected services.
    """
    queryset = ConnectedService.objects.all()
    serializer_class = ConnectedServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only allow users to see their own connected services."""
        return self.queryset.filter(user=self.request.user)

class DataPriorityViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user data source priorities.
    """
    queryset = DataPriority.objects.all()
    serializer_class = DataPrioritySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only allow users to see their own data priorities."""
        return self.queryset.filter(user=self.request.user)

class WorkoutViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user workouts.
    """
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only allow users to see their own workouts."""
        return self.queryset.filter(user=self.request.user)

class UnifiedWorkoutExerciseViewSet(viewsets.ModelViewSet):
    queryset = UnifiedWorkoutExercise.objects.all()
    serializer_class = UnifiedWorkoutExerciseSerializer
    permission_classes = [IsAuthenticated]

class UnifiedWorkoutSetViewSet(viewsets.ModelViewSet):
    queryset = UnifiedWorkoutSet.objects.all()
    serializer_class = UnifiedWorkoutSetSerializer
    permission_classes = [IsAuthenticated]

class SleepViewSet(viewsets.ModelViewSet):
    queryset = Sleep.objects.all()
    serializer_class = SleepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class DailyStepsViewSet(viewsets.ModelViewSet):
    queryset = DailySteps.objects.all()
    serializer_class = DailyStepsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class DailyWaterViewSet(viewsets.ModelViewSet):
    queryset = DailyWater.objects.all()
    serializer_class = DailyWaterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class NutritionEntryViewSet(viewsets.ModelViewSet):
    queryset = NutritionEntry.objects.all()
    serializer_class = NutritionEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class BodyWeightViewSet(viewsets.ModelViewSet):
    queryset = BodyWeight.objects.all()
    serializer_class = BodyWeightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class ArchivedWorkoutViewSet(viewsets.ModelViewSet):
    queryset = ArchivedWorkout.objects.all()
    serializer_class = ArchivedWorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class WorkoutConflictViewSet(viewsets.ModelViewSet):
    queryset = WorkoutConflict.objects.all()
    serializer_class = WorkoutConflictSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class LevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view level progression. Assumes levels are system-defined.
    """
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [IsAuthenticated]

class IntegrationIdeaViewSet(viewsets.ModelViewSet):
    queryset = IntegrationIdea.objects.all()
    serializer_class = IntegrationIdeaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Automatically associate the idea with the logged-in user."""
        serializer.save(user=self.request.user)




# Router Setup
router = routers.DefaultRouter()
router.register(r'color-preferences', ColorPreferencesViewSet)
router.register(r'friendships', FriendshipViewSet)
router.register(r'gear', GearViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'sweat-score-weights', SweatScoreWeightsViewSet)
router.register(r'connected-services', ConnectedServiceViewSet)
router.register(r'data-priorities', DataPriorityViewSet)
router.register(r'workouts', WorkoutViewSet)
router.register(r'workout-exercises', UnifiedWorkoutExerciseViewSet)
router.register(r'workout-sets', UnifiedWorkoutSetViewSet)
router.register(r'sleep', SleepViewSet)
router.register(r'daily-steps', DailyStepsViewSet)
router.register(r'daily-water', DailyWaterViewSet)
router.register(r'nutrition', NutritionEntryViewSet)
router.register(r'body-weight', BodyWeightViewSet)
router.register(r'archived-workouts', ArchivedWorkoutViewSet)
router.register(r'workout-conflicts', WorkoutConflictViewSet)
router.register(r'levels', LevelViewSet)
router.register(r'integration-ideas', IntegrationIdeaViewSet)