from django_components import component

@component.register("weight_chart_card")
class WeightChartCard(component.Component):
    template_name = "weight_chart_card/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) 