from django_components import component

@component.register("top_navigation")
class TopNavigation(component.Component):
    template_name = "top_navigation/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)