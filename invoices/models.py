from xhtml2pdf import pisa
from io import BytesIO

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.template.loader import get_template
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.html import format_html

import logging

from private_storage.fields import PrivateFileField

from shop.models import Order, OrderItem
from mailings.models import InvoiceMessage
from invoices.utils import get_email_template, validate_email_template

logger = logging.getLogger(__name__)


INVOICE_TYPE_CHOICES = (
    ("s", "Storno"),
    ("i", "Rechnung"),
)


class Invoice(models.Model):
    name = models.CharField(max_length=255)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(verbose_name="Betrag", max_digits=10, decimal_places=2)
    invoice_number = models.CharField(verbose_name="Rechnungsnummer", max_length=255)
    invoice_date = models.DateTimeField(
        verbose_name="Rechnungsdatum", null=True, blank=True
    )
    invoice_receipt = models.DateTimeField(
        verbose_name="Rechnungseingang", null=True, blank=True
    )
    invoice_type = models.CharField(
        verbose_name="Rechnungsart",
        max_length=1,
        choices=INVOICE_TYPE_CHOICES,
        default="i",
    )
    mail_sent_date = models.DateTimeField(
        verbose_name="Rechnungsversand", null=True, blank=True
    )
    pdf = PrivateFileField(upload_to="invoices/", null=True, blank=True)
    # these fields are for overwriting event name and event date
    replacement_event = models.CharField(
        "Ersatzangabe Event Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Zum Überschreiben des automatisch erzeugten Veranstaltungstitels. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.",
    )
    replacement_date = models.CharField(
        "Ersatzangabe Event Datum",
        max_length=40,
        null=True,
        blank=True,
        help_text="Zum Überschreiben des automatisch erzeugten Veranstaltungsdatums. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.",
    )
    use_replacements = models.BooleanField(
        "Ersatzangaben benutzen",
        default=False,
        help_text="Anklicken, um Ersatzangaben zu benutzen",
    )

    class Meta:
        verbose_name = "Rechnung"
        verbose_name_plural = "Rechnungen"

    def __str__(self):
        return self.name

    @property
    def get_full_name_and_events(self):
        return f"{self.order.lastname}, {self.order.firstname} / {', '.join([ev.label for ev in self.order.get_registered_items_events()])}"

    def create_invoice_pdf(self):
        invoice = self
        pdf_template = "invoices/pdf_invoice.html"
        context = {}
        context["storno"] = False
        context["invoice"] = invoice
        context["order"] = invoice.order
        context["order_items"] = OrderItem.objects.filter(
            order=invoice.order, status="r"
        )
        context["contains_action_price"] = any(
            [
                item.is_action_price
                for item in OrderItem.objects.filter(order=invoice.order, status="r")
            ]
        )

        # delete existing pdf
        # Delete old PDF file if it exists
        if invoice.pdf and default_storage.exists(self.pdf.name):
            default_storage.delete(self.pdf.name)

        template = get_template(pdf_template)
        html = template.render(context)

        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result, encoding="utf-8")

        if not pdf.err:
            result.seek(0)
            filename = f"Rechnung_{invoice.invoice_number}.pdf"
            # Save PDF to Invoice model's FileField
            self.pdf.save(filename, ContentFile(result.read()))
            self.save()
            return True
        return False

    def recreate_invoice_pdf_button(self):
        """Return a button for recreating the PDF in admin list view."""
        url = reverse("admin:recreate-invoice-pdf", args=[self.pk])
        todo = "erzeugen" if not self.pdf else "erneuern"
        return format_html(f'<a class="button" href="{url}">Rechnungs-Pdf {todo}</a>')

    recreate_invoice_pdf_button.short_description = "PDF"
    recreate_invoice_pdf_button.allow_tags = True

    def create_invoice_message(self):
        invoice = self
        invoice_email = InvoiceMessage()
        invoice_email.subject = f"VFLL - Rechnung Nr. {invoice.invoice_number}"
        invoice_email.from_address = settings.DEFAULT_FROM_EMAIL
        invoice_email.to_address = invoice.order.email
        invoice_email.reply_to = settings.REPLY_TO_EMAIL
        invoice_email.bcc_address = settings.EMAIL_NOTIFY_BCC

        # create mail content
        event_string = ", ".join(
            [item.event.name for item in invoice.order.items.all()]
        )
        formatting_dict = {
            "academic": invoice.order.academic if invoice.order.academic else "",
            "firstname": invoice.order.firstname,
            "lastname": invoice.order.lastname,
            "event_string": event_string,
            "costs": invoice.amount,
        }
        template_name = "invoice"
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

    def create_invoice_message_button(self):
        """Return a button for recreating the invoice message in admin list view."""
        url = reverse("admin:create-invoice-message", args=[self.pk])
        todo = "erzeugen" if not self.message else ""
        return format_html(f'<a class="button" href="{url}">Rechnungs-Mail {todo}</a>')

    recreate_invoice_pdf_button.short_description = "Mail"
    recreate_invoice_pdf_button.allow_tags = True

    def create_storno_invoice(self):
        invoice = self
        if StornoInvoice.objects.filter(original_invoice=invoice).exists():
            return False
        storno_invoice_number = f"{invoice.invoice_number}S"
        new_storno = StornoInvoice.objects.create(
            original_invoice=invoice,
            invoice_number=storno_invoice_number,
            amount=invoice.amount,
        )
        new_storno.create_storno_invoice_pdf()
        return new_storno

    def create_storno_invoice_button(self):
        """Return a button for creating the storno invoice in admin list view."""
        url = reverse("admin:create-storno-invoice", args=[self.pk])
        todo = "erzeugen" if not self.storno_invoice else ""
        return format_html(f'<a class="button" href="{url}">Storno-Rechnung {todo}</a>')

    create_storno_invoice_button.short_description = "Storno"
    create_storno_invoice_button.allow_tags = True


class StornoInvoice(models.Model):

    original_invoice = models.OneToOneField(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="storno_invoice",
    )
    amount = models.DecimalField(
        verbose_name="Betrag",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Der Betrag erscheint auf der Storno-Rechnung mit Minuszeichen.",
    )
    invoice_number = models.CharField(
        verbose_name="Rechnungsnummer", max_length=255, null=True, blank=True
    )
    invoice_date = models.DateTimeField(
        verbose_name="Rechnungsdatum", auto_now_add=True
    )
    paid = models.BooleanField(verbose_name="bezahlt", default=False)
    invoice_receipt = models.DateTimeField(
        verbose_name="Rechnungseingang", null=True, blank=True
    )
    pdf = PrivateFileField(upload_to="stornos/", null=True, blank=True)

    class Meta:
        verbose_name = "Storno Rechnung"
        verbose_name_plural = "Storno Rechnungen"

    def save(self, *args, **kwargs):
        self.amount = self.original_invoice.amount
        super().save(*args, **kwargs)

    def create_storno_invoice_pdf(self):
        invoice = self
        pdf_template = "invoices/pdf_invoice.html"
        context = {}
        context["storno"] = True
        context["invoice"] = invoice
        context["order"] = invoice.original_invoice.order
        context["order_items"] = OrderItem.objects.filter(
            order=invoice.original_invoice.order, status="r"
        )
        context["contains_action_price"] = any(
            [
                item.is_action_price
                for item in OrderItem.objects.filter(
                    order=invoice.original_invoice.order, status="r"
                )
            ]
        )

        # delete existing pdf
        # Delete old PDF file if it exists
        if invoice.pdf and default_storage.exists(self.pdf.name):
            default_storage.delete(self.pdf.name)

        template = get_template(pdf_template)
        html = template.render(context)

        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result, encoding="utf-8")

        if not pdf.err:
            result.seek(0)
            filename = f"Storno-Rechnung_{invoice.invoice_number}.pdf"
            # Save PDF to Invoice model's FileField
            self.pdf.save(filename, ContentFile(result.read()))
            self.save()
            return True
        return False
