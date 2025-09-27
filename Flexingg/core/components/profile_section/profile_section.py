from django_components import component
from django.utils import timezone
from core.models import Workout, UserProfile, BodyWeight

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
        # If a form was provided, prefer showing the latest BodyWeight entry as the weight initial value
        form = kwargs.get('form')
        if form and user and getattr(user, 'is_authenticated', True):
            try:
                bw = BodyWeight.objects.filter(user=user).order_by('-datetime').first()
                if bw and getattr(bw, 'weight_lbs', None) is not None:
                    form.initial = getattr(form, 'initial', {})
                    try:
                        form.initial['weight'] = float(bw.weight_lbs)
                    except Exception:
                        form.initial['weight'] = bw.weight_lbs
                else:
                    # Fallback to profile.bodyweight_lbs if available
                    fb = getattr(user, 'bodyweight_lbs', None)
                    if fb is not None:
                        form.initial = getattr(form, 'initial', {})
                        try:
                            form.initial['weight'] = float(fb)
                        except Exception:
                            form.initial['weight'] = fb
            except Exception:
                # Ignore and continue; leave form as-is if any DB error occurs
                pass
        # Ensure the template receives the form instance
        if form:
            context['form'] = form

        stat_card_config = []
        if user and getattr(user, 'is_authenticated', True):
            # Ensure user is a UserProfile instance if possible
            if isinstance(user, UserProfile):
                stat_card_config = getattr(user, 'stat_card_config', [])
            elif hasattr(user, 'stat_card_config'):
                stat_card_config = getattr(user, 'stat_card_config', [])
            
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
        context['stat_card_config'] = stat_card_config
        return context