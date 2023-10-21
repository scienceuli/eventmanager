from django.contrib import admin
from django.urls import reverse
from django.utils.html import mark_safe

from shop.models import Order, OrderItem

from .actions import export_to_csv


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
    ]

    list_filter = [
        "paid",
        "payment_type",
        "payment_date",
        "date_created",
        "date_modified",
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
