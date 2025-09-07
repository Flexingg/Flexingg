from django import template

register = template.Library()

@register.filter(name='get_width')
def get_width(size_class):
    """
    Extract the width from the size_class string.
    """
    if not isinstance(size_class, str):
        return ''
    parts = size_class.split()
    if not parts:
        return ''
    width_str = parts[0]
    if width_str.startswith('w-'):
        return width_str[2:]
    return ''