from datetime import timedelta, datetime

from django.conf import settings
from django.db.models import Min
from django.urls import reverse
from django.utils import timezone

from shop.models import Order, OrderItem
from events.core_models import SiteSettings
from payment.utils import update_order, check_order_date_in_future
from payment.forms import CustomPayPalPaymentsForm
from utilities.pdf import render_to_pdf
from events.utils.email_utils import send_email


class PaymentService:

    def get_payment_date(self, order):
        """Returns the correct date for an invoice.

        If ORDER_DATE_DELAYED is False or payment is via PayPal,
        the invoice date is the order creation date.

        If payment is by invoice and SEND_INVOICE_AFTER_ORDER_CREATION is False,
        the invoice date is calculated relative to the earliest event date.
        """
        if not settings.ORDER_DATE_DELAYED:
            return order.date_created
        if order.payment_type == "p":
            return order.date_created

        if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
            return order.date_created

        earliest_event_date = order.items.aggregate(
            earliest_event=Min("event__first_day")
        )["earliest_event"]

        if earliest_event_date < datetime.now().date():
            return datetime.now()

        calculated_date = earliest_event_date - timedelta(
            days=settings.ORDER_DATE_TIMEDELTA
        )
        if calculated_date < datetime.now().date():
            return datetime.now()

        return calculated_date

    def build_paypal_form(self, order, host):
        """Build the PayPal payment form for an order."""
        amount = order.get_total_cost()
        paypal_dict = {
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": amount,
            "item_name": order.get_order_number,
            "no_shipping": "2",
            "invoice": str(order.uuid),
            "currency_code": "EUR",
            "notify_url": "http://{}{}".format(host, reverse("paypal-ipn")),
            "return_url": "http://{}{}".format(
                host, reverse("payment:payment-success", args=[order.id])
            ),
            "cancel_return": "http://{}{}".format(
                host, reverse("payment:payment-failed", args=[order.id])
            ),
        }
        return CustomPayPalPaymentsForm(initial=paypal_dict)

    def handle_payment_success(self, order):
        """Mark order as paid via PayPal."""
        order.payment_type = "p"
        order.save()

    def handle_payment_failure(self, order):
        """Handle failed PayPal payment — fall back to invoice."""
        order.payment_type = "r"
        order.save()
        order.payment_date = self.get_payment_date(order)
        order.save()

    def handle_invoice_payment(self, order):
        """Process payment by invoice."""
        order.payment_type = "r"
        order.payment_date = self.get_payment_date(order)
        order.save()

        if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
            from payment.tasks import payment_completed
            payment_completed(order.id)

    def generate_invoice_pdf(self, order, process):
        """Generate an invoice or storno PDF for an order."""
        site_settings = SiteSettings.load()
        context = {
            "order": order,
            "vfll_recipient_payment": site_settings.vfll_recipient_payment,
            "vfll_bank_account": site_settings.vfll_bank_account,
            "process": process,
        }

        if process == "storno":
            context["label"] = "Storno-Rechnung"
            context["invoice_date"] = datetime.now()
            context["order_items"] = OrderItem.objects.filter(
                order=order, status="c"
            )
        elif process == "order":
            context["label"] = "Rechnung"
            context["invoice_date"] = (
                order.payment_date if order.payment_date else order.date_created
            )
            context["order_items"] = OrderItem.objects.filter(
                order=order, status="r"
            )

        context["contains_action_price"] = any(
            item.is_action_price
            for item in OrderItem.objects.filter(order=order, status="r")
        )

        template_path = "shop/pdf_invoice.html"
        response = render_to_pdf(template_path, context)
        filename = f"{process}_rechnung_{order.get_order_number}"
        response["Content-Disposition"] = f'filename="{filename}.pdf"'
        return response

    def send_invoice_and_pdf(self, order):
        """Set payment type to invoice and trigger invoice email with PDF."""
        order.payment_type = "r"
        order.save()
        from payment.tasks import payment_completed
        payment_completed(order.id)

    def send_reminder(self, order):
        """Send a payment reminder email for an order.

        Returns a tuple (success: bool, error_message: str or None).
        """
        from payment.utils import check_order_complete

        if order.paid:
            return False, "Rechnung wurde bereits bezahlt"

        if not check_order_complete(order):
            return False, "Bitte erst die Rechnung vervollständigen (Name, Email)"

        addresses = {"to": [order.email]}
        subject = f"Mahnung Rechnung {order.get_order_number}"
        formatting_dict = {
            "firstname": order.firstname,
            "lastname": order.lastname,
            "order_number": order.get_order_number,
            "payment_date": order.payment_date.date().strftime("%d.%m.%Y"),
            "events": ", ".join(
                [event.name for event in order.get_registered_items_events()]
            ),
            "total_costs": order.get_total_cost(),
        }

        sent = send_email(
            addresses,
            subject,
            settings.DEFAULT_FROM_EMAIL,
            [settings.REPLY_TO_EMAIL],
            "reminder",
            formatting_dict=formatting_dict,
        )

        if sent:
            order.reminder_sent_date = timezone.now()
            order.save()
            return True, None

        return False, "Mahnung konnte nicht verschickt werden"
