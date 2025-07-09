from datetime import date

from django.core.management.base import BaseCommand
from invoices.models import Invoice
from shop.models import Order

from invoices.utils import get_invoice_date


class Command(BaseCommand):
    help = 'Set Invoice Payment Receipt according to Order Payment Receipt'

    def handle(self, *args, **options):
        updated_count = 0
        today = date.today()
        for order in Order.objects.all():
            invoice = Invoice.objects.filter(order=order).first()

            if order.paid and invoice:
                if order.payment_receipt and not invoice.invoice_receipt:
                    invoice.invoice_receipt = order.payment_receipt
                    invoice.save()
                    updated_count += 1
                elif not order.payment_receipt and not invoice.invoice_receipt:
                    invoice.invoice_receipt = order.date_modified if order.date_modified else today
                    invoice.save()
                    updated_count += 1


        self.stdout.write(self.style.SUCCESS(f"Done. {updated_count} Invoice(s) updated."))


        
