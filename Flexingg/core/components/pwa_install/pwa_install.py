from django_components import component

@component.register("pwa_install")
class PwaInstall(component.Component):
    template_name = "pwa_install/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        context['show_pwa_install'] = True  # Let client-side JS handle the logic
        return context