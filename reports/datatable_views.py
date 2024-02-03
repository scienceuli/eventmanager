from ajax_datatable.views import AjaxDatatableView
from django.http import JsonResponse
from django.shortcuts import render

from shop.models import Order


class OrderAjaxDatatableView(AjaxDatatableView):
    model = Order
    title = "Bestellungen"
    initial_order = [
        ["lastname"],
    ]
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, "all"]]
    search_values_separator = "+"

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {
            "name": "id",
            "visible": False,
        },
        {
            "name": "date_created",
            "visible": True,
        },
        {
            "name": "lastname",
            "visible": True,
        },
        {
            "name": "email",
            "visible": True,
        },
    ]


def get_orders_data(request):
    result_list = list(
        Order.objects.all().values(
            "date_created",
            "lastname",
            "email",
            "id",
        )
    )

    return JsonResponse(result_list, safe=False)


def orders_view(request):
    context = {}
    return render(request, "reports/orders_datatable.html", context)
