from django_components import component

@component.register("save_logout_buttons")
class SaveLogoutButtons(component.Component):
    template_name = "save_logout_buttons/template.html"

    class Media:
        css = "save_logout_buttons/style.css"
        js = "save_logout_buttons/script.js"