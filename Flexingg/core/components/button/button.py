from django_components import component

@component.register("button")
class Button(component.Component):
    template_name = "button/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)