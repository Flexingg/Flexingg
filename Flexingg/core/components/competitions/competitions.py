from django_components import component

@component.register("competitions")
class Competitions(component.Component):
    template_name = "competitions/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        # Add fitness data for competitions
        if 'fitness_summary' in kwargs:
            context['fitness_summary'] = kwargs.get('fitness_summary', {})
            # Add weekly/monthly aggregations for competitions
            from datetime import date, timedelta
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)

            # Get weekly and monthly summaries
            from core.aggregation_service import get_user_fitness_summary
            context['weekly_summary'] = get_user_fitness_summary(
                self.request.user if hasattr(self, 'request') else None,
                week_start, today
            )
            context['monthly_summary'] = get_user_fitness_summary(
                self.request.user if hasattr(self, 'request') else None,
                month_start, today
            )
        return context