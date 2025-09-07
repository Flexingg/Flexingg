from django_components import component

@component.register("level_card")
class LevelCard(component.Component):
    template_name = "level_card/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context is None:
            context = {}
        context['is_authenticated'] = self.request.user.is_authenticated
        return context