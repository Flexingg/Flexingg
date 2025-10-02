from django_components import component
from garminconnect.models import Garmin_Auth

@component.register("connections")
class Connections(component.Component):
    template_name = "connections/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        profile = kwargs.get('profile')
        if profile:
            garmin_connected = Garmin_Auth.objects.filter(user=profile).exists()
            liftosaur_connected = bool(profile.liftosaur_user_id)
            has_liftosaur_token = bool(profile.liftosaur_session_token)
            from django.utils import timezone
            hc_connected = bool(profile.hc_token and profile.hc_token_expiry and profile.hc_token_expiry > timezone.now())
            context['garmin_connected'] = garmin_connected
            context['liftosaur_connected'] = liftosaur_connected
            context['has_liftosaur_token'] = has_liftosaur_token
            context['hc_connected'] = hc_connected
        return context

    class Media:
        css = "connections/style.css"
        js = ("connections/script.js",)