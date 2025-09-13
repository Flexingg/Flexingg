from django_components import component

@component.register("level_card")
class LevelCard(component.Component):
    template_name = "level_card/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context is None:
            context = {}
        context['is_authenticated'] = self.request.user.is_authenticated
        if context['is_authenticated']:
            user = self.request.user
            avatar_url = user.avatar.url if user.avatar else "https://placehold.co/64x64/222/00f5d4?text=AV"
            context['user_avatar'] = avatar_url
        return context