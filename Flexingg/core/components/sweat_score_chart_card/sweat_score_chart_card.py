from django_components import component

@component.register("sweat_score_chart_card")
class SweatScoreChartCard(component.Component):
    template_name = "sweat_score_chart_card/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)