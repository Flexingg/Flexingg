from django_components import component
from django.utils import timezone
from core.models import Workout

@component.register("profile_section")
class ProfileSection(component.Component):
    template_name = "profile_section/template.html"

    class Media:
        css = "profile_section/style.css"
        js = "profile_section/script.js"

    def get_context_data(self, **kwargs):
        """
        Provide todays_lifting_volume_k to the template by summing Workout.get_total_volume
        for the current profile (or request.user) on the target date.
        """
        context = super().get_context_data(**kwargs) or {}
        user = kwargs.get('profile') or kwargs.get('user') or getattr(kwargs.get('request'), 'user', None)
        target_date = kwargs.get('date') or timezone.now().date()
        vol_k = 0.0
        if user and getattr(user, 'is_authenticated', True):
            try:
                workouts = Workout.objects.filter(user=user, start_time__date=target_date)
                total_lbs = 0.0
                for w in workouts:
                    try:
                        total_lbs += float(w.get_total_volume(unit='lb') or 0)
                    except Exception:
                        pass
                vol_k = total_lbs / 1000.0
            except Exception:
                vol_k = 0.0
        context['todays_lifting_volume_k'] = vol_k
        return context