import uuid

from decimal import Decimal
from django.conf import settings
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
    order.payment_type = "p"
    order.save()

    # success_url = request.build_absolute_uri(
    #                 reverse('payment:completed'))
    # cancel_url = request.build_absolute_uri(
    #                 reverse('payment:canceled'))

    # get the current host of requested website
    host = request.get_host()

    # paypal dict
    amount = order.get_total_cost()
    paypal_dict = {
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": amount,
        "item_name": order.get_order_number,
        "no_shipping": "2",
        "invoice": str(order.uuid),
        "currency_code": "EUR",
        "notify_url": "http://{}{}".format(host, reverse("paypal-ipn")),
        "return_url": "http://{}{}".format(host, reverse("payment:payment-success")),
        "cancel_return": "http://{}{}".format(host, reverse("payment:payment-failed")),
    }
    paypal_form = CustomPayPalPaymentsForm(initial=paypal_dict)

    return render(
        request, "payment/process.html", {"paypal_form": paypal_form, "order": order}
    )


# Payment success


def payment_success(request):
    return render(request, "payment/payment_success.html")


# Payment failed


def payment_failed(request):
    return render(request, "payment/payment_failed.html")


# payment by invoice


def payment_by_invoice(request, order_id):
    if request.method == "POST":
        print("alles gut")

        order = Order.objects.get(id=order_id)
        order.payment_type = "r"
        order.save()

        payment_completed.delay(order_id)
        return redirect("payment:payment-by-invoice-success")


# success page for payment by invoice


def payment_by_invoice_success(request):
    return render(request, "payment/payment_by_invoice.html")
