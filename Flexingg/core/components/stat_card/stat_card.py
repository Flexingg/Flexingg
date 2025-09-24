from django_components import component
from django.utils import timezone
from core.models import Workout

@component.register("stat_card")
class StatCard(component.Component):
    template_name = "stat_card/template.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        context['todays_total_calories'] = kwargs.get('todays_total_calories', 0)
        context['todays_steps'] = kwargs.get('todays_steps', 0)
        context['todays_consumed_calories'] = kwargs.get('todays_consumed_calories', 0)
        # Compute today's lifting volume (in thousands of lbs, "k") if not supplied by caller.
        if 'todays_lifting_volume_k' in kwargs:
            context['todays_lifting_volume_k'] = kwargs.get('todays_lifting_volume_k', 0)
        else:
            user = kwargs.get('user') or getattr(kwargs.get('request'), 'user', None)
            target_date = kwargs.get('date') or timezone.now().date()
            vol_k = 0.0
            if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                try:
                    workouts = Workout.objects.filter(user=user, start_time__date=target_date)
                    total_lbs = 0.0
                    for w in workouts:
                        try:
                            total_lbs += float(w.get_total_volume(unit='lb') or 0)
                        except Exception:
                            # ignore single-workout parse errors
                            pass
                    vol_k = total_lbs / 1000.0
                except Exception:
                    vol_k = 0.0
            context['todays_lifting_volume_k'] = vol_k
        context['todays_water_ounces'] = kwargs.get('todays_water_ounces', 0)
        context['fitness_summary'] = kwargs.get('fitness_summary', {})
        return context
