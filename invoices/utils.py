from io import BytesIO
from xhtml2pdf import pisa
from datetime import datetime, timedelta
import re
import logging
from smtplib import SMTPException
import pandas as pd
import plotly.express as px
from plotly.offline import plot

from django.core.mail import EmailMessage, BadHeaderError
from django.conf import settings
from django.db.models import Min
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.template.loader import get_template
from django.core.files.storage import default_storage



from tempfile import NamedTemporaryFile

from events.email_template import EmailTemplate
from events.utils import EmailTemplateError
from events.parameters import ws_limits

from mailings.models import InvoiceMessage
from shop.models import OrderItem
from utilities.pdf import render_to_pdf_directly

logger = logging.getLogger(__name__)


def get_email_template(template_name):
    try:
        template = EmailTemplate.objects.get(name=template_name)
        return template
    except EmailTemplate.DoesNotExist:
        raise EmailTemplateError("No such template: {}".format(template_name))


def validate_email_template(raw_template, formatting_dict, required=True):
    required_keys = set(re.findall("{(.+?)}", raw_template))
    if not required_keys.issubset(set(formatting_dict.keys())):
        if required:
            logger.critical(
                "Not all required fields of the template were found in formatting dictionary.\n"
                "required:{} !~ formatting:{}".format(
                    required_keys, set(formatting_dict)
                )
            )
            raise EmailTemplateError(
                "Not all required fields of the template were found in formatting dictionary.\n"
                "required:{} !~ formatting:{}".format(
                    required_keys, set(formatting_dict)
                )
            )
        else:
            logger.warning(
                "Not all required fields of the template were found in formatting dictionary."
            )
            return raw_template

    return raw_template.format(**formatting_dict)


def get_invoice_date(order):
    if not settings.ORDER_DATE_DELAYED:
        return order.date_created
    if order.payment_type == "p":
        return order.date_created
    else:
        if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
            return order.date_created
        else:
            earliest_event_date = order.items.aggregate(
                earliest_event=Min("event__first_day")
            )["earliest_event"]
            if (
                earliest_event_date < datetime.now().date()
            ):  # earliest_event_date is date object
                return datetime.now()
            calculated_date = earliest_event_date - timedelta(
                days=settings.ORDER_DATE_TIMEDELTA
            )
            if calculated_date < datetime.now().date():
                return datetime.now()
            return calculated_date


class EmailTemplateError(Exception):
    pass

def get_invoice_type(invoice):
    if invoice.__class__.__name__ == "StandardInvoice":
        return 'i'
    elif invoice.__class__.__name__ == "StornoInvoice":
        return 's'

def create_mail(invoice):
    #invoice_type = get_invoice_type(invoice)
    invoice_type = invoice.invoice_type
    invoice_dict = {
        "i": {
            "subject": "Rechnung", 
            "name": "Rechnung",
            "template": "invoice"
        },
        "s": {
            "subject": "Storno-Rechnung",  
            "name": "Storno-Rechnung",
            "template": "storno"
        }      
    }
    # if invoice_type == 'i':
    #     order = invoice.order
    # elif invoice_type == 's':
    #     order = invoice.original_invoice.order
    order = invoice.order
    invoice_email = InvoiceMessage()
    invoice_email.subject = f"VFLL - {invoice_dict[invoice_type]['subject']} Nr. {invoice.invoice_number}" if invoice_type in invoice_dict else f"VFLL - {invoice_dict[invoice_type]} zu Nr. {invoice.invoice_number}"
    invoice_email.from_address = settings.DEFAULT_FROM_EMAIL
    invoice_email.to_address = order.email
    invoice_email.reply_to = settings.REPLY_TO_EMAIL
    if len(settings.EMAIL_NOTIFY_BCC) > 0:
        invoice_email.bcc_address = settings.EMAIL_NOTIFY_BCC

    invoice_email.mail_type = invoice_type

    # create mail content
    event_string = ", ".join(
        [item.event.name for item in order.items.all()]
    )
    formatting_dict = {
        "academic": order.academic if order.academic else "",
        "firstname": order.firstname,
        "lastname": order.lastname,
        "event_string": event_string,
        "costs": invoice.amount,
    }
    template_name = invoice_dict[invoice_type]["template"]
    template = get_email_template(template_name)
    text_template = getattr(template, "text_template", "")
    if not text_template:
        logger.critical(
            "Missing text template (required) for the input {}.".format(
                text_template
            )
        )
        raise EmailTemplateError("Email template is not valid for the input.")

    invoice_email.content = validate_email_template(text_template, formatting_dict)

    # if invoice_type == 'i':
    #     pdf_created = invoice.create_invoice_pdf()
    # elif invoice_type == 's':
    #     pdf_created = invoice.create_storno_invoice_pdf()
    pdf_created = invoice.create_invoice_pdf()

    if pdf_created:
        # with invoice.pdf.open("rb") as pdf_file:
        # invoice_email.add_attachment(pdf_file)
        invoice_email.add_attachment(invoice.pdf)
        # if pdf:
        #     # filename_prefix = "rechnung_%s" % (invoice.invoice_number)
        #     filename = f"Rechnung_{invoice.invoice_number}.pdf"

        # temp = NamedTemporaryFile(suffix=".pdf", prefix=filename_prefix)
        # temp.write(pdf)
        # temp.seek(0)
        # invoice_email.add_attachment = temp
        # invoice.pdf.save(filename, ContentFile(pdf.read()))
        # invoice.save()

    invoice_email.invoice = invoice
    invoice_email.save()
    return invoice_email

def create_pdf(invoice):
    #invoice_type = get_invoice_type(invoice)
    invoice_type = invoice.invoice_type
    invoice_dict = {
        "i": {
            "subject": "Rechnung", 
        },
        "s": {
            "subject": "Storno-Rechnung",  
        }      
    }
    
    pdf_template = "invoices/pdf_invoice.html"
    context = {}
    context["storno"] = invoice_type == "s"
    context["invoice"] = invoice
    # if invoice_type == 'i':
    #     order = invoice.order
    # elif invoice_type == 's':
    #     order = invoice.original_invoice.order
    order = invoice.order
    context["order"] = order
    context["order_items"] = OrderItem.objects.filter(
        order=order, status="r"
    )
    context["contains_action_price"] = any(
        [
            item.is_action_price
            for item in OrderItem.objects.filter(order=order, status="r")
        ]
    )

    # delete existing pdf
    # Delete old PDF file if it exists
    if invoice.pdf and default_storage.exists(invoice.pdf.name):
        default_storage.delete(invoice.pdf.name)

    template = get_template(pdf_template)
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result, encoding="utf-8")

    if not pdf.err:
        result.seek(0)
        filename = f"{invoice_dict[invoice_type]['subject']}_{invoice.invoice_number}.pdf"
        # Save PDF to Invoice model's FileField
        invoice.pdf.save(filename, ContentFile(result.read()))
        invoice.save()
        return True
    return False
