from django import template

register = template.Library()


@register.filter
def has_show_true(payment_cart):
    return any(item["action_price"] for item in payment_cart)
