from django import template
import base64
import requests

register = template.Library()


@register.filter
def to_base64(url):
    # return "data:image/png;base64, " + str(base64.b64encode(requests.get(url).content))
    with open(url, "rb") as img_file:
        my_string = base64.b64encode(img_file.read())
    return "data:image/png;base64," + my_string.decode("utf-8")
