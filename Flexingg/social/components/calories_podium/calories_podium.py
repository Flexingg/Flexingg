from django_components import component
from core.models import UserProfile
from garminconnect.models import GarminActivity
from django.db.models import Sum, Q, FloatField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta


@component.register("calories_podium")
class CaloriesPodium(component.Component):
    template_name = "calories_podium/template.html"

    def get_context_data(self, **kwargs):
        today = timezone.now().date()
        cutoff = today.replace(day=1)
        users = UserProfile.objects.all()
        annotated_users = users.annotate(
            metric_value=Coalesce(
                Sum('garmin_activities__calories', filter=Q(garmin_activities__start_time_utc__date__gte=cutoff)),
                Value(0),
                output_field=FloatField()
            )
        ).order_by('-metric_value')[:3]

        users_list = [
            {
                'rank': i + 1,
                'name': u.username,
                'metric_value': float(u.metric_value) if u.metric_value is not None else 0.0,
                'avatar': u.avatar.url if u.avatar else None
            }
            for i, u in enumerate(annotated_users)
        ]

        return {
            'users': users_list,
            'metric': 'Calories Burned'
        }