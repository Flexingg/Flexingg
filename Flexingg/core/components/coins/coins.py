from django_components import component

@component.register("coins")
class Coins(component.Component):
    template_name = "coins/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)