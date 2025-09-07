from django_components import component

@component.register("item_shop")
class ItemShop(component.Component):
    template_name = "item_shop/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)