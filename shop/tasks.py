from celery import shared_task
from django.core.mail import send_mail
from shop.models import Order


@shared_task
def order_created(order_id):
    """
    Task to send an e-mail notification when an order is
    successfully created.
    """
    order = Order.objects.get(id=order_id)
    subject = f"Bestellung Nr. {order.get_order_number}"
    message = (
        f"Liebe/r {order.firstname},\n\n"
        f"Du hast dich für kostenpflichtige VFLL-Veranstaltungen angemeldet. "
        f"Deine Bestellnummer ist {order.get_order_number}.\n\n"
        f"In einer weiteren Mail wird dir die Rechnung zugestellt."
    )
    if order.payment_type == "p":
        message += f"Da du Paypal als Zahlungsweise gewählt hast, gibt es nichts weiter zu tun.\n\n Vielen Dank!"
    elif order.payment_type == "r":
        message += f"Bitte überweise den Betrag auf das in der Rechnung angegebene Konto.\n\n Vielen Dank!"

    mail_sent = send_mail(subject, message, "geschaeftsstelle@vfll.de", [order.email])
    return mail_sent
