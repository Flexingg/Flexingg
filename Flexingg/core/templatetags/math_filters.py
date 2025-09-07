from django import template
import math

register = template.Library()

@register.filter
def calculate_x(index, total):
    """Calculate x position on circle based on index and total items"""
    if total == 1:
        return 0
    angle = math.radians((index * 360 / total) - 90)
    return round(100 * math.cos(angle), 2)

@register.filter
def calculate_y(index, total):
    """Calculate y position on circle based on index and total items"""
    if total == 1:
        return -100
    angle = math.radians((index * 360 / total) - 90)
    return round(-200 + (100 * math.sin(angle)), 2) 