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
