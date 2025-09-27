from django_components import component

@component.register("top_navigation")
class TopNavigation(component.Component):
    template_name = "top_navigation/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context is None:
            context = {}
        user = kwargs.get('user')

        def _to_int(val):
            try:
                return int(round(val))
            except Exception:
                try:
                    return int(val)
                except Exception:
                    return 0

        if user:
            cardio = _to_int(getattr(user, 'cardio_coins', 0))
            gems = _to_int(getattr(user, 'gym_gems', 0))
        else:
            cardio = _to_int(kwargs.get('cardio_coins', 0))
            gems = _to_int(kwargs.get('gym_gems', 0))

        context['rounded_cardio_coins'] = cardio
        context['rounded_gym_gems'] = gems
        return context