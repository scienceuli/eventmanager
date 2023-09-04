from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from shop.models import Order


# @shared_task
def order_created(order_id):
    """
    Task to send an e-mail notification when an order is
    successfully created.
    """
    order = Order.objects.get(id=order_id)
    subject = f"Bestellung Nr. {order.get_order_number}"
    message = (
        f"Liebe/r {order.firstname},\n\n"
        f"Sie haben sich für kostenpflichtige VFLL-Veranstaltungen angemeldet. "
        f"Ihre Bestellnummer ist {order.get_order_number}.\n\n"
        f"In einer weiteren Mail wird Ihnen die Rechnung zugestellt."
    )
    if order.payment_type == "p":
        message += f"Da Sie Paypal als Zahlungsweise gewählt haben, gibt es nichts weiter zu tun.\n\n Vielen Dank!"
    elif order.payment_type == "r" or order.payment_type == "n":
        message += f"Bitte überweisen Sie den Betrag auf das in der Rechnung angegebene Konto.\n\n Vielen Dank!"

    if settings.SEND_EMAIL_AFTER_ORDER_CREATION:
        mail_sent = send_mail(
            subject, message, "geschaeftsstelle@vfll.de", [order.email]
        )
        return mail_sent
    return False
