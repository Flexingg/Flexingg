from django import template
import math

register = template.Library()

# Math-related filters
@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return int(float(value)) * int(float(arg))
    except (ValueError, TypeError):
        return 0

@register.filter(name='divide')
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        if isinstance(arg, (list, tuple)):
            arg = len(arg)
        return int(float(value)) / int(float(arg))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter(name='intdiv')
def intdiv(value, arg):
    """Integer division of value by argument"""
    try:
        if isinstance(arg, (list, tuple)):
            arg = len(arg)
        return int(float(value)) // int(float(arg))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter(name='modulo')
def modulo(value, arg):
    """Get the remainder of value divided by argument"""
    try:
        if isinstance(arg, (list, tuple)):
            arg = len(arg)
        return int(float(value)) % int(float(arg))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        if isinstance(arg, (list, tuple)):
            arg = len(arg)
        return int(float(value)) - int(float(arg))
    except (ValueError, TypeError):
        return 0

@register.filter(name='length')
def length(value):
    """Get the length of a list, tuple, or string"""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0

# Time-related filters
@register.filter(name='duration2time')
def duration2time(value):
    """Convert duration in seconds to HH:MM:SS format"""
    try:
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = int((value % 3600) % 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}'
    except (ValueError, ZeroDivisionError):
        return None

# Form-related filters
@register.filter(name='addclass')
def addclass(field, css):
    """Add CSS class to a form field"""
    return field.as_widget(attrs={'class': css})

@register.filter(name='attr')
def set_attr(field, attr_args):
    """
    Set HTML attributes for a form field
    Usage: {{ field|attr:"name:value" }}
    """
    if ':' not in attr_args:
        return field
    
    attr, value = attr_args.split(':', 1)
    attrs = field.field.widget.attrs
    attrs[attr.strip()] = value.strip()
    return field

# Utility filters
@register.filter
def range_filter(start, end):
    """Create a range from start to end"""
    try:
        return range(int(start), int(end))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def sin(value):
    """Returns the sine of a radian angle."""
    return math.sin(float(value))

@register.filter
def cos(value):
    """Returns the cosine of a radian angle."""
    return math.cos(float(value))

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary safely.
    Returns None if the key doesn't exist.
    
    Usage:
    {{ my_dict|get_item:key_name }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)