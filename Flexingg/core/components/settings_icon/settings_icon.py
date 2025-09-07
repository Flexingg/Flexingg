from django_components import component

@component.register("settings_icon")
class SettingsIcon(component.Component):
    template_name = "settings_icon/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)