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
from events.utils import get_email_template, validate_email_template, send_email


@shared_task
def payment_completed(order_id):
    """
    Task to send an e-mail notification when an order is
    successfully paid.
    """
    order = Order.objects.get(id=order_id)
    context = {}

    print("payment_type", order.payment_type)

    if order.payment_type == "r":
        template_name = "invoice"
    elif order.payment_type == "p":
        template_name = "paypal"

    event_string = ", ".join([item.event.name for item in order.items.all()])

    formatting_dict = {
        "academic": order.academic,
        "firstname": order.firstname,
        "lastname": order.lastname,
        "event_string": event_string,
        "costs": order.get_total_cost(),
    }

    addresses = {"to": [order.email]}

    from_email = (settings.DEFAULT_FROM_EMAIL,)
    reply_to = [settings.REPLY_TO_EMAIL]

    # create invoice e-mail
    subject = f"VFLL - Rechnung Nr. {order.get_order_number}"

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
    context["contains_action_price"] = any(
        [item.is_action_price for item in order.items.all()]
    )
    pdf = render_to_pdf_directly(template, context)
    if pdf:
        filename_prefix = "rechnung_%s" % (order.get_order_number)
        # pdf_file = ContentFile(pdf)

        temp = NamedTemporaryFile(suffix=".pdf", prefix=filename_prefix)
        temp.write(pdf)
        temp.seek(0)

        # send e-mail with pdf attachment
        send_email(
            addresses,
            subject,
            from_email,
            reply_to,
            template_name,
            formatting_dict=formatting_dict,
            invoice_name="invoice.pdf",
            pdf=pdf,
            mime="application/pdf",
        )
