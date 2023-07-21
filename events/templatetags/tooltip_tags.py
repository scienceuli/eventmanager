from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def tooltip(key):
    try:
        tooltip = settings.TOOLTIPS[key]
        return tooltip
    except KeyError:
        return ""  # or return a message stating that the key does not exist.
