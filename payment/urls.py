from django.urls import path
from . import views

app_name = "payment"

urlpatterns = [
    path("payment_process/", views.payment_process, name="payment-process"),
    path(
        "payment_success/<int:order_id>", views.payment_success, name="payment-success"
    ),
    path("payment_failed/", views.payment_failed, name="payment-failed"),
    path(
        "payment_by_invoice/<int:order_id>/",
        views.payment_by_invoice,
        name="payment-by-invoice",
    ),
    path(
        "payment_by_invoice_success/",
        views.payment_by_invoice_success,
        name="payment-by-invoice-success",
    ),
]
