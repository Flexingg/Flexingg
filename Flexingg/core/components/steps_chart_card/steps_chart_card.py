from django_components import component

@component.register("steps_chart_card")
class StepsChartCard(component.Component):
    template_name = "steps_chart_card/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)