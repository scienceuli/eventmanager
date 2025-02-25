from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    path("", views.cart_detail, name="cart-detail"),
    path("add/<int:event_id>/", views.cart_add, name="cart-add"),
    path(
        "add_collection/<int:event_collection_id>/",
        views.cart_add_collection,
        name="cart-add-collection",
    ),
    path("remove/<int:event_id>/", views.cart_remove, name="cart-remove"),
    # path("order_create/", views.order_create, name="order-create"),
    path("order_create/", views.OrderCreateView.as_view(), name="order-create"),
    path(
        "admin/order/<int:order_id>/<str:process>/pdf/",
        views.admin_order_pdf,
        name="admin-order-pdf",
    ),
    path(
        "admin/order/<int:order_id>/pdf_and_mail/",
        views.admin_order_pdf_and_mail,
        name="admin-order-pdf-and-mail",
    ),
    path(
        "admin/order/list/",
        views.invoice_report,
        name="invoice-report",
    ),
    path(
        "admin/order/<int:order_id>/",
        views.admin_order_detail,
        name="admin-order-detail",
    ),
    path(
        "admin/order_reminder/<int:order_id>/",
        views.reminder_mail,
        name="reminder-mail",
    ),
]
