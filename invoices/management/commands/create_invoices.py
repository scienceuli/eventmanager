# your_app/management/commands/create_invoides.py

from django.core.management.base import BaseCommand
from invoices.models import Invoice
from shop.models import Order
from events.models import Event, EventMember
from mailings.models import InvoiceMessage

from invoices.utils import get_invoice_date


class Command(BaseCommand):
    help = 'Creates Invoive instances based on existing Order data'

    def handle(self, *args, **options):
        created_count = 0
        for order in Order.objects.all():
            invoice_name = f"Rechnung {order.lastname}, {order.firstname} ({', '.join([ev.label for ev in order.get_registered_items_events()])})"
            invoice_name = invoice_name[:255]

            new_invoice = Invoice.objects.create(
                invoice_date=get_invoice_date(order),
                order=order,
                invoice_number=order.get_order_number,
                invoice_type="i",
                name=invoice_name,
                amount=order.get_total_cost()
            )
            if new_invoice:
                created_count += 1

                # create a message for the invoice
                new_invoice.create_invoice_message()

        self.stdout.write(self.style.SUCCESS(f"Done. {created_count} Invoice(s) created."))


        
