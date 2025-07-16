import pytz
from datetime import datetime
from django.utils import timezone

from django.contrib import admin
from django.urls import reverse, path
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponseRedirect
from django.forms.models import BaseInlineFormSet


from django.utils.html import mark_safe

from shop.models import Order, OrderItem, OrderNote
from payment.utils import check_order_date_in_future, update_order
from .actions import (
    export_to_csv,
    export_to_excel,
    download_invoices_as_zipfile,
    reset_download_markers,
)

from .filter import EventListFilter, YearQuarterFilter

from events.filter import DateRangeFilter

from invoices.models import Invoice


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["event"]


class OrderNoteInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)
        if not obj.created_by_id:  # Only set created_by if it hasn't been set already
            obj.created_by = self.request.user  # Set created_by to the logged-in user
        if commit:
            obj.save()
        return obj


class OrderNoteInline(admin.TabularInline):
    model = OrderNote
    raw_id_fields = ["order"]
    extra = 1
    formset = OrderNoteInlineFormSet
    readonly_fields = ["created_by", "date_created", "date_modified"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.request = request  # Pass the request to formset
        return formset
    
class OrderNoteAdmin(admin.ModelAdmin):
    list_display = ["order", "title", "note", "created_by", "date_created", "date_modified"]
    readonly_fields = ["created_by", "date_created", "date_modified"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # only set on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

admin.site.register(OrderNote, OrderNoteAdmin)


def order_pdf_and_mail(obj):
    url = reverse("shop:admin-order-pdf-and-mail", args=[obj.id])
    if obj.payment_type == "r":
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
        # "payment_date_html",
        # "mail_sent_date",
        "date_created",
        "date_modified",
        # "paid",
        # "payment_receipt",
        "invoice_paid",
        # "download_marker",
        order_detail,
        "invoices_button",
        # "order_pdf_button",
        # "storno_pdf_button",
        # order_pdf_and_mail,
        # reminder_mail,
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
        YearQuarterFilter,
        "download_marker",
        ("date_created", DateRangeFilter),
    ]

    search_fields = [
        "id",
        "lastname",
        "items__event__name",
        "notes__note",
        "notes__title",
    ]
    inlines = [OrderItemInline, OrderNoteInline]

    actions = [
        export_to_csv,
        export_to_excel,
        download_invoices_as_zipfile,
        reset_download_markers,
    ]

    export_to_csv.short_description = "Export -> CSV"
    export_to_excel.short_description = "Export -> Excel"
    download_invoices_as_zipfile.short_description = "Export -> ZIP"
    reset_download_markers.short_description = "Reset Download Markers"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "order_pdf/<int:order_id>/<str:process>",
                self.admin_site.admin_view(self.order_pdf),
                name="order_pdf",
            ),
        ]
        return custom_urls + urls

    def order_pdf_button(self, obj):
        url = reverse("admin:order_pdf", args=[obj.id, "order"])
        return mark_safe(f'<a href="{url}">PDF</a>')

    order_pdf_button.short_description = "Rechnung"
    order_pdf_button.allow_tags = True

    def invoices_button(self, obj):
        url = (
            reverse("admin:invoices_standardinvoice_changelist") + f"?order__id__exact={obj.id}"
        )
        return mark_safe(f"<a class='button' href='{url}'>Rechnung(en)</a>")

    invoices_button.short_description = "Rechnung(en)"
    invoices_button.allow_tags = True

    def storno_pdf_button(self, obj):
        if obj.storno:
            url = reverse("admin:order_pdf", args=[obj.id, "storno"])
            return mark_safe(f'<a href="{url}">Storno</a>')
        else:
            return mark_safe("-")

    storno_pdf_button.short_description = "Storno"
    storno_pdf_button.allow_tags = True

    def order_pdf(self, request, order_id, process):
        order = get_object_or_404(Order, id=order_id)
        order_list_url = reverse(
            "admin:%s_%s_changelist" % (order._meta.app_label, order._meta.model_name),
        )

        if process == "order":
            if not check_order_date_in_future(order):
                if request.method == "POST":
                    if request.POST.get("update") == "Ja":
                        update_order(order)
                        self.message_user(request, "Order updated successfully!")
                    return redirect(
                        reverse("shop:admin-order-pdf", args=[order_id, process])
                    )

                # Render a template to ask for confirmation
                return render(
                    request,
                    "admin/confirm_update.html",
                    {"order": order, "cancel_url": order_list_url},
                )

            else:
                # If order is valid, directly update and return to the changelist
                update_order(order)
                self.message_user(request, "Order updated successfully!")
                return redirect(
                    reverse("shop:admin-order-pdf", args=[order_id, process])
                )

        elif process == "storno":
            return redirect(reverse("shop:admin-order-pdf", args=[order_id, process]))

    def amount(self, instance):
        return instance.get_total_cost()

    amount.short_description = "Betrag"

    def payment_date_html(self, instance):
        if instance.payment_date and instance.get_total_cost() == 0:
            return mark_safe(f"<s>{instance.payment_date.strftime('%d.%m.%Y')}</s>")
        return instance.payment_date

    payment_date_html.short_description = "Rechnungsdatum"

    change_list_template = "admin/daterange/change_list.html"

    @admin.display(boolean=True, description='bez.')
    def invoice_paid(self, instance):
        return Invoice.objects.filter(order=instance).first().invoice_receipt is not None
    
    


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "event",
    ]
    search_fields = ["event__name"]
