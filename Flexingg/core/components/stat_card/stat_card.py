from django_components import component

@component.register("stat_card")
class StatCard(component.Component):
    template_name = "stat_card/template.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        context['todays_total_calories'] = kwargs.get('todays_total_calories', 0)
        context['todays_steps'] = kwargs.get('todays_steps', 0)
        context['todays_lifting_calories'] = kwargs.get('todays_lifting_calories', 0)
        return context
