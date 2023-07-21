from io import BytesIO
import qrcode

from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.files.base import ContentFile

from tempfile import NamedTemporaryFile

from shop.models import Order

from payment.utils import render_to_pdf_directly
from events.utils import validate_email_template


@shared_task
def payment_completed(order_id):
    """
    Task to send an e-mail notification when an order is
    successfully paid.
    """
    order = Order.objects.get(id=order_id)
    context = {}

    # create invoice e-mail
    subject = f"VFLL - Rechnung Nr. {order.get_order_number}"
    message_dict = {
        "p": "Du hast den Betrag bereits per PayPal beglichen. Danke!\n Anbei findest du die Rechnung zu den von dir gebuchten VFLL-Fortbildungen.",
        "r": "Du zahlst auf Rechnung. Anbei findest du die Rechnung zu den von dir gebuchten VFLL-Fortbildungen. Bitte überweise den Betrag auf folgendes Konto:\n Kontodaten:",
    }

    email = EmailMessage(
        subject,
        message_dict[order.payment_type],
        "geschaeftsstelle@vfll.de",
        [order.email],
    )

    # generate QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data("Some data")
    qr.make(fit=True)
    # todo: how to get this to pdf?

    img = qr.make_image(fill_color="black", back_color="white")

    # generate PDF
    template = "shop/pdf_invoice.html"
    context["order"] = order
    pdf = render_to_pdf_directly(template, context)
    if pdf:
        filename_prefix = "rechnung_%s" % (order.get_order_number)
        # pdf_file = ContentFile(pdf)

        temp = NamedTemporaryFile(suffix=".pdf", prefix=filename_prefix)
        temp.write(pdf)
        temp.seek(0)

        # attach PDF file
        email.attach("invoice.pdf", pdf, "application/pdf")

        # email.attach_file(temp, "application/pdf")

        # send e-mail
        email.send()
