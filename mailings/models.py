from django.db import models

from mailqueue.models import MailerMessage


MAIL_TYPE_CHOICES = (
    ("s", "Storno"),
    ("i", "Rechnung"),
)


class InvoiceMessage(MailerMessage):
    invoice = models.OneToOneField(
        "invoices.Invoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="message",
    )
    mail_type = models.CharField(max_length=1, choices=MAIL_TYPE_CHOICES, default="i")

    class Meta:
        verbose_name = "Rechnung Mail"
        verbose_name_plural = "Rechnung Mails"
