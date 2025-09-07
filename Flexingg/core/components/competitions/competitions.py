from django_components import component

@component.register("competitions")
class Competitions(component.Component):
    template_name = "competitions/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)