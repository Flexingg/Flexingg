from django_components import component

@component.register("sidebar_bottom_nav")
class SidebarBottomNav(component.Component):
    template_name = "sidebar_bottom_nav/template.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)