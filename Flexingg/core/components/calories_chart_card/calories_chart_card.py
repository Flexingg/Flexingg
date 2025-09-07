from django_components import component

@component.register("calories_chart_card")
class CaloriesChartCard(component.Component):
    template_name = "calories_chart_card/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)