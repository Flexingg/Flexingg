from django import template

register = template.Library()

@register.filter
def format_duration_seconds(value):
    if value is None:
        return '00:00:00'
    hours = value // 3600
    minutes = (value % 3600) // 60
    seconds = value % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"