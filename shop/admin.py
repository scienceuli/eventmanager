from django.contrib import admin
from django.urls import reverse
from django.utils.html import mark_safe

from shop.models import Order, OrderItem

from .actions import export_to_csv

from .filter import EventListFilter


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["event"]


def order_pdf(obj):
    url = reverse("shop:admin-order-pdf", args=[obj.id])
    return mark_safe(f'<a href="{url}">PDF</a>')


order_pdf.short_description = "Rechnung"


def order_pdf_and_mail(obj):
    url = reverse("shop:admin-order-pdf-and-mail", args=[obj.id])
    if obj.payment_type == "n":
        return mark_safe(f'<a href="{url}">PDF+Mail</a>')
    else:
        return ""


order_pdf_and_mail.short_description = "R+M"


def order_detail(obj):
    url = reverse("shop:admin-order-detail", args=[obj.id])
    return mark_safe(f"<a href='{url}'>Anschauen</a>")


def order_events(obj):
    order_events_string = ", ".join([item.event.name for item in obj.items.all()])
    return order_events_string


order_events.short_description = "Veranstaltung(en)"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ("amount",)
    list_display = [
        "id",
        "firstname",
        "lastname",
        "email",
        "get_total_cost",
        "payment_type",
        "paid",
        "discounted",
        "date_created",
        "date_modified",
        order_detail,
        order_pdf,
        order_pdf_and_mail,
        order_events,
    ]

    list_filter = [
        EventListFilter,
        "paid",
        "payment_type",
        "payment_date",
        "date_created",
        "date_modified",
    ]

    search_fields = [
        "lastname",
        "items__event__name",
    ]
    inlines = [OrderItemInline]

    actions = [export_to_csv]

    export_to_csv.short_description = "Export -> CSV"

    def amount(self, instance):
        return instance.get_total_cost()

    amount.short_description = "Betrag"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "event",
    ]
