from django_components import component

@component.register("profile_section")
class ProfileSection(component.Component):
    template_name = "profile_section/template.html"

    class Media:
        css = "profile_section/style.css"
        js = "profile_section/script.js"