import uuid
from datetime import timedelta, datetime

from decimal import Decimal
from django.conf import settings
from django.db.models import Min
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from shop.models import Order
from payment.tasks import payment_completed

from payment.forms import CustomPayPalPaymentsForm


# todo
# create the payment instance


def payment_process(request):
    order_id = request.session.get("order_id", None)
    order = get_object_or_404(Order, id=order_id)
    # order.payment_type = "p"
    # order.save()

    # success_url = request.build_absolute_uri(
    #                 reverse('payment:completed'))
    # cancel_url = request.build_absolute_uri(
    #                 reverse('payment:canceled'))

    # get the current host of requested website
    host = request.get_host()

    # paypal dict
    if settings.PAYPAL_ENABLED:
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
        paypal_form = CustomPayPalPaymentsForm(initial=paypal_dict)

        return render(
            request,
            "payment/process.html",
            {"paypal_form": paypal_form, "order": order},
        )
    else:
        return redirect("payment:payment-by-invoice", order.id)


# Payment success


def payment_success(request, order_id):
    order = Order.objects.get(id=order_id)
    order.payment_type = "p"
    order.save()
    return render(request, "payment/payment_success.html")


# Payment failed


def payment_failed(request, order_id):
    # if payment failed payment_type is set to r
    order = Order.objects.get(id=order_id)
    order.payment_type = "r"
    order.save()
    order.payment_date = get_payment_date(order)
    order.save()

    return render(request, "payment/payment_failed.html")


def get_payment_date(order):
    """returns the correct date for invoice
    invoice can have more than one item (event)
    correct invoice date is first_day of earliest event

    if payment_type = p(aypal) or payment_type = 'r' and settings.SEND_INVOICE_AFTER_ORDER_CREATION is true
    the invoice/payment date is date_created

    if payment_type = r and not settings.SEND_INVOICE_AFTER_ORDER_CREATION:
    invoice can have more than one item (event)
    correct invoice date is now first_day of earliest event
    """
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


# payment by invoice
def payment_by_invoice(request, order_id):
    if not settings.PAYPAL_ENABLED:
        request.method = "POST"
    if request.method == "POST":
        order = Order.objects.get(id=order_id)
        order.payment_type = "r"
        order.payment_date = get_payment_date(order)
        order.save()

        # payment_completed.delay(order_id)
        if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
            payment_completed(order_id)
        return redirect("payment:payment-by-invoice-success")


# success page for payment by invoice


def payment_by_invoice_success(request):
    if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
        message = "Die Rechnung geht Ihnen per E-Mail zu."
    else:
        message = "Die Rechnung geht Ihnen wenige Tage vor Veranstaltungsbeginn per E-Mail zu."
    context = {"message": message}
    return render(request, "payment/payment_by_invoice.html", context)
