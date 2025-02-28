from django.core.management.base import BaseCommand
from shop.models import Order
from invoices.models import Invoice
from mailings.models import InvoiceMessage


class Command(BaseCommand):
    help = "Migrate payment details from Order to Invoice"

    def handle(self, *args, **kwargs):
        orders = Order.objects.all()
        count = 0

        for order in orders:
            # Create an Invoice for each Order
            invoice, created = Invoice.objects.get_or_create(
                order=order,
                defaults={
                    "invoice_date": order.payment_date,
                    "invoice_receipt": order.payment_receipt,
                },
            )

            if not InvoiceMessage.objects.filter(invoice=invoice).exists():
                new_message = invoice.create_invoice_message()
                if order.mail_sent_date:
                    new_message.sent = True
                    new_message.last_attempt = order.mail_sent_date
                    new_message.save()

            if not invoice.pdf:
                invoice.create_invoice_pdf()

            if created:
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Invoice created for Order ID {order.id}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Migration complete: {count} invoices created.")
        )
