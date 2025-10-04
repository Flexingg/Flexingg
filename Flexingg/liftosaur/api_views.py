from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *
from core.api_views import router


class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing the list of available exercises.
    """
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer
    permission_classes = [IsAuthenticated]

class UserExerciseStatViewSet(viewsets.ModelViewSet):
    queryset = UserExerciseStat.objects.all()
    serializer_class = UserExerciseStatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class WorkoutViewSet(viewsets.ModelViewSet):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class WorkoutExerciseViewSet(viewsets.ModelViewSet):
    queryset = WorkoutExercise.objects.all()
    serializer_class = WorkoutExerciseSerializer
    permission_classes = [IsAuthenticated]

class WorkoutSetViewSet(viewsets.ModelViewSet):
    queryset = WorkoutSet.objects.all()
    serializer_class = WorkoutSetSerializer
    permission_classes = [IsAuthenticated]

class BodyMeasurementViewSet(viewsets.ModelViewSet):
    queryset = BodyMeasurement.objects.all()
    serializer_class = BodyMeasurementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


router.register(r'liftosaur_exercises', ExerciseViewSet)
router.register(r'liftosaur_user-exercise-stats', UserExerciseStatViewSet)
router.register(r'liftosaur_workout', WorkoutViewSet, basename="liftosaur-workout")
router.register(r'liftosaur_workout-exercises', WorkoutExerciseViewSet)
router.register(r'liftosaur_workout-sets', WorkoutSetViewSet)
router.register(r'liftosaur_body-measurements', BodyMeasurementViewSet)
router.register(r'liftosaur_programs', ProgramViewSet)