from django_components import component
from garminconnect.models import Garmin_Auth

@component.register("integrations_section")
class IntegrationsSection(component.Component):
    template_name = "integrations_section/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        profile = kwargs.get('profile')
        if profile:
            garmin_connected = Garmin_Auth.objects.filter(user=profile).exists()
            context['garmin_connected'] = garmin_connected
        return context

    class Media:
        css = "integrations_section/style.css"
        js = "integrations_section/script.js"
