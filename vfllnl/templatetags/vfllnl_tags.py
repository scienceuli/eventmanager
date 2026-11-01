import time

from django import template
from django.core import signing

register = template.Library()

FORM_TOKEN_SALT = "vfllnl.subscribe"


@register.simple_tag
def nl_form_token():
    """Signed timestamp of when the signup form was rendered."""
    return signing.dumps(int(time.time()), salt=FORM_TOKEN_SALT)
