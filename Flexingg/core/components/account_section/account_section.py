from django_components import component

@component.register("account_section")
class AccountSection(component.Component):
    template_name = "account_section/template.html"

    class Media:
        css = "account_section/style.css"
        js = "account_section/script.js"