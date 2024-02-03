from django.urls import path
from . import datatable_views

app_name = "reports"

urlpatterns = [
    # path(
    #    "datatable/orders/",
    #    datatable_views.OrderAjaxDatatableView.as_view(),
    #    name="ajax_datatable_orders",
    # ),
    path(
        "datatable/get_orders_data/",
        datatable_views.get_orders_data,
        name="get-orders-data",
    ),
    path(
        "datatable/orders/",
        datatable_views.orders_view,
        name="orders-view",
    ),
]
