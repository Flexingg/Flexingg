from django_components import component


@component.register("coins")
class Coins(component.Component):
    template_name = "coins/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context is None:
            context = {}
        currency_type = kwargs.get('currency_type', 'cardio_coins')
        user = kwargs.get('user')
        if user:
            coins = getattr(user, currency_type, 0)
        else:
            coins = kwargs.get('coins', 0)
        context['coins'] = coins
        context['currency_type'] = currency_type
        return context