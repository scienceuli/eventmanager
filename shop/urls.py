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
        "admin/order/<int:order_id>/pdf/", views.admin_order_pdf, name="admin-order-pdf"
    ),
    path(
        "admin/order/<int:order_id>/",
        views.admin_order_detail,
        name="admin-order-detail",
    ),
]
