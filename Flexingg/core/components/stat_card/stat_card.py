from django_components import component

@component.register("stat_card")
class StatCard(component.Component):
    template_name = "stat_card/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)