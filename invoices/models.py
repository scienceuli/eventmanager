from xhtml2pdf import pisa
from io import BytesIO

from datetime import datetime, date

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
from invoices.utils import (
    get_email_template,
    validate_email_template,
    create_mail, 
    create_pdf,
)

from invoices.managers import StandardInvoiceManager, StornoInvoiceManager

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
    invoice_export = models.DateTimeField(
        verbose_name="Exportdatum", null=True, blank=True
    )
    pdf = PrivateFileField(upload_to="invoices/", null=True, blank=True)
    pdf_export = models.DateTimeField(
        verbose_name="Pdf-Export", null=True, blank=True
    )
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
    storno_invoice = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_invoice",
        limit_choices_to={"invoice_type": "s"},
    )

    class Meta:
        verbose_name = "Rechnung"
        verbose_name_plural = "Rechnungen"
        ordering = ["-invoice_date"]

    def __str__(self):
        return self.name

    @property
    def get_full_name_and_events(self):
        return f"{self.order.lastname}, {self.order.firstname} / {', '.join([ev.label for ev in self.order.get_registered_items_events()])}"

    def create_invoice_pdf(self):
        invoice = self
        return create_pdf(invoice)
        

    def recreate_invoice_pdf_button(self):
        """Return a button for recreating the PDF in admin list view."""
        url = reverse("admin:recreate-invoice-pdf", args=[self.pk])
        todo = "erzeugen" if not self.pdf else "erneuern"
        return format_html(f'<a class="button" href="{url}">Rechnungs-Pdf {todo}</a>')

    recreate_invoice_pdf_button.short_description = "PDF"
    recreate_invoice_pdf_button.allow_tags = True

    def create_invoice_message(self):
        invoice = self
        return create_mail(invoice)
    

    def create_invoice_message_button(self):
        """Return a button for recreating the invoice message in admin list view."""
        url = reverse("admin:create-invoice-message", args=[self.pk])
        todo = "erzeugen" if not self.message else ""
        return format_html(f'<a class="button" href="{url}">Rechnungs-Mail {todo}</a>')

    recreate_invoice_pdf_button.short_description = "Mail"
    recreate_invoice_pdf_button.allow_tags = True

    def create_storno_invoice(self):
        invoice = self
        if invoice.invoice_type == "s":
            return False
        if Invoice.objects.filter(original_invoice=invoice).exists():
            return False
        storno_invoice_number = f"{invoice.invoice_number}S"
        new_storno = Invoice.objects.create(
            name = f"Storno {invoice.name}",
            invoice_date=datetime.now(),
            invoice_number=storno_invoice_number,
            amount=invoice.amount,
            order=invoice.order,
            invoice_type="s",
        )
        invoice.storno_invoice = new_storno
        invoice.save()

        new_storno.create_invoice_pdf()
        new_storno.create_invoice_message()
        return new_storno

    def create_storno_invoice_button(self):
        """Return a button for creating the storno invoice in admin list view."""
        url = reverse("admin:create-storno-invoice", args=[self.pk])
        todo = "erzeugen" if not self.storno_invoice else ""
        return format_html(f'<a class="button" href="{url}">Storno-Rechnung {todo}</a>')

    create_storno_invoice_button.short_description = "Storno"
    create_storno_invoice_button.allow_tags = True

    def set_paid(self):
        today = date.today()
        self.invoice_receipt = today
        self.save()


# class StornoInvoice(models.Model):

#     original_invoice = models.OneToOneField(
#         Invoice,
#         null=True,
#         blank=True,
#         on_delete=models.SET_NULL,
#         related_name="storno_invoice",
#     )
#     amount = models.DecimalField(
#         verbose_name="Betrag",
#         max_digits=10,
#         decimal_places=2,
#         null=True,
#         blank=True,
#         help_text="Der Betrag erscheint auf der Storno-Rechnung mit Minuszeichen.",
#     )
#     invoice_number = models.CharField(
#         verbose_name="Rechnungsnummer", max_length=255, null=True, blank=True
#     )
#     invoice_date = models.DateTimeField(
#         verbose_name="Rechnungsdatum", auto_now_add=True
#     )
#     paid = models.BooleanField(verbose_name="bezahlt", default=False)
#     invoice_receipt = models.DateTimeField(
#         verbose_name="Rechnungseingang", null=True, blank=True
#     )
#     pdf = PrivateFileField(upload_to="stornos/", null=True, blank=True)

#     class Meta:
#         verbose_name = "Storno Rechnung"
#         verbose_name_plural = "Storno Rechnungen"

#     def save(self, *args, **kwargs):
#         self.amount = self.original_invoice.amount
#         super().save(*args, **kwargs)

#     def create_storno_invoice_pdf(self):
#         invoice = self
#         return create_pdf(invoice)
        

#     def create_storno_invoice_mail(self):
#         invoice = self
#         return create_mail(invoice)






class StandardInvoice(Invoice):

    objects = StandardInvoiceManager()
    class Meta:
        proxy = True
        verbose_name = "Rechnung"
        verbose_name_plural = "Rechnungen"


class StornoInvoice(Invoice):


    objects = StornoInvoiceManager()
    class Meta:
        proxy = True
        verbose_name = "Storno-Rechnung"
        verbose_name_plural = "Storno-Rechnungen"

    @property
    def get_storno_amount(self):
        return self.amount * (-1)
