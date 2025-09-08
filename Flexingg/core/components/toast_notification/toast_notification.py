from django_components import component

@component.register("toast_notification")
class ToastNotification(component.Component):
    template_name = "toast_notification/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        context['messages'] = kwargs.get('messages', [])
        return context