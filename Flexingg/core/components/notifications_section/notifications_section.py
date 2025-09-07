from django_components import component

@component.register("notifications_section")
class NotificationsSection(component.Component):
    template_name = "notifications_section/template.html"

    class Media:
        css = "notifications_section/style.css"
        js = "notifications_section/script.js"