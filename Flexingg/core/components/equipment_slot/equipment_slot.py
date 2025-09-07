from django_components import component

@component.register("equipment_slot")
class EquipmentSlot(component.Component):
    template_name = "equipment_slot/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)