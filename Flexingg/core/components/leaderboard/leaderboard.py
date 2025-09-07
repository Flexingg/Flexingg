from django_components import component

@component.register("leaderboard")
class Leaderboard(component.Component):
    template_name = "leaderboard/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)