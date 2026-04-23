from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InvoiceMessage, ConfirmationMessage
from shop.models import Order


@receiver(post_save, sender=InvoiceMessage)
def update_invoice_email_date(sender, instance, **kwargs):
    if instance.sent and instance.last_attempt:
        instance.invoice.mail_sent_date = instance.last_attempt
        instance.invoice.save(update_fields=["mail_sent_date"])


@receiver(post_save, sender=ConfirmationMessage)
def update_confirmation_email_date(sender, instance, **kwargs):
    if instance.sent and instance.last_attempt and instance.confirmation:
        instance.confirmation.mail_sent_date = instance.last_attempt
        instance.confirmation.save(update_fields=["mail_sent_date"])
