from django_components import component

@component.register("gym_locker")
class GymLocker(component.Component):
    template_name = "gym_locker/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)