from django_components import component

@component.register("integrations_section")
class IntegrationsSection(component.Component):
    template_name = "integrations_section/template.html"

    class Media:
        css = "integrations_section/style.css"
        js = "integrations_section/script.js"