from django.contrib import admin
from django.urls import reverse
from django.utils.html import mark_safe


from shop.models import Order, OrderItem

from .actions import export_to_csv, download_invoices_as_zipfile, reset_download_markers

from .filter import EventListFilter

from events.filter import DateRangeFilter


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
        return mark_safe(f'<a href="{url}">Pdf+✉</a>')
    else:
        return ""


order_pdf_and_mail.short_description = "R+M"


def reminder_mail(obj):
    url = reverse("shop:reminder-mail", args=[obj.id])
    if not obj.paid:
        return mark_safe(f'<a href="{url}">✉</a>')
    else:
        return ""


reminder_mail.short_description = "Mahn"


def order_detail(obj):
    url = reverse("shop:admin-order-detail", args=[obj.id])
    return mark_safe(f"<a href='{url}'>Anschauen</a>")


def order_events(obj):
    order_events_string = " | ".join(
        [item.event.name for item in obj.items.filter(status="r")]
    )
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
        "storno",
        "discounted",
        "payment_date_html",
        "mail_sent_date",
        "date_created",
        "date_modified",
        "paid",
        "payment_receipt",
        "download_marker",
        order_detail,
        order_pdf,
        order_pdf_and_mail,
        reminder_mail,
        order_events,
    ]

    list_filter = [
        EventListFilter,
        "paid",
        "payment_type",
        "payment_date",
        "payment_receipt",
        "date_created",
        "date_modified",
        "download_marker",
        ("date_created", DateRangeFilter),
    ]

    search_fields = [
        "id",
        "lastname",
        "items__event__name",
    ]
    inlines = [OrderItemInline]

    actions = [export_to_csv, download_invoices_as_zipfile, reset_download_markers]

    export_to_csv.short_description = "Export -> CSV"
    download_invoices_as_zipfile.short_description = "Export -> ZIP"
    reset_download_markers.short_description = "Reset Download Markers"

    def amount(self, instance):
        return instance.get_total_cost()

    amount.short_description = "Betrag"

    def payment_date_html(self, instance):
        if instance.payment_date and instance.get_total_cost() == 0:
            return mark_safe(f"<s>{instance.payment_date.strftime('%d.%m.%Y')}</s>")
        return instance.payment_date

    payment_date_html.short_description = "Rechnungsdatum"

    change_list_template = "admin/daterange/change_list.html"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "event",
    ]
    search_fields = ["event__name"]
