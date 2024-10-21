from django import forms
from paypal.standard.forms import PayPalPaymentsForm

from django.utils.html import format_html


class CustomPayPalPaymentsForm(PayPalPaymentsForm):
    def get_html_submit_element(self):
        print("custom form called")
        return format_html("""<button type="submit">Jetzt bezahlen</button>""")

    def get_html(self):
        return ""
