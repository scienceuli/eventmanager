from django import template

register = template.Library()

@register.simple_tag
def class_name(event):
    return event.__class__.__name__