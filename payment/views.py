from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404

from shop.models import Order
from payment.services.payment_service import PaymentService


def payment_process(request):
    order_id = request.session.get("order_id", None)
    order = get_object_or_404(Order, id=order_id)
    host = request.get_host()

    if settings.PAYPAL_ENABLED:
        service = PaymentService()
        paypal_form = service.build_paypal_form(order, host)
        return render(
            request,
            "payment/process.html",
            {"paypal_form": paypal_form, "order": order},
        )
    else:
        return redirect("payment:payment-by-invoice", order.id)


def payment_success(request, order_id):
    order = Order.objects.get(id=order_id)
    service = PaymentService()
    service.handle_payment_success(order)
    return render(request, "payment/payment_success.html")


def payment_failed(request, order_id):
    order = Order.objects.get(id=order_id)
    service = PaymentService()
    service.handle_payment_failure(order)
    return render(request, "payment/payment_failed.html")


def payment_by_invoice(request, order_id):
    if not settings.PAYPAL_ENABLED:
        request.method = "POST"
    if request.method == "POST":
        order = Order.objects.get(id=order_id)
        service = PaymentService()
        service.handle_invoice_payment(order)
        return redirect("payment:payment-by-invoice-success")


def payment_by_invoice_success(request):
    if settings.SEND_INVOICE_AFTER_ORDER_CREATION:
        message = "Die Rechnung geht Ihnen per E-Mail zu."
    else:
        message = "Die Rechnung geht Ihnen per E-Mail zu."
    context = {"message": message}
    return render(request, "payment/payment_by_invoice.html", context)
