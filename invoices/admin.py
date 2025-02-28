from django.contrib import admin
from django.utils.html import mark_safe
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect

from invoices.models import Invoice
from invoices.actions import export_to_excel_short
from mailings.models import InvoiceMessage


class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "order_button",
        "amount",
        "invoice_number",
        "invoice_date",
        "invoice_type",
        "invoice_mail",
        # "create_invoice_message_button",
        "mail_sent_date",
        "pdf",
        "recreate_invoice_pdf_button",
    )
    actions = [
        export_to_excel_short,
    ]
    export_to_excel_short.short_description = "Export -> Excel (St.)"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "recreate_pdf/<int:invoice_id>/",
                self.admin_site.admin_view(self.recreate_invoice_pdf),
                name="recreate-invoice-pdf",
            ),
            path(
                "create_mail/<int:invoice_id>/",
                self.admin_site.admin_view(self.create_invoice_message),
                name="create-invoice-message",
            ),
        ]
        return custom_urls + urls

    def order_button(self, obj):
        if obj.order:
            url = reverse("admin:shop_order_change", args=[obj.order.id])
            return mark_safe(
                f"<a class='button' href='{url}'>Order {obj.order.get_order_number}</a>"
            )
        return "Keine Order"

    order_button.short_description = "Order"
    order_button.allow_tags = True

    def order_display(self, obj):
        return obj.order.get_order_number

    order_display.admin_order_field = "order"  # Enables sorting by order
    order_display.short_description = "Order"  # Column name in admin

    def invoice_mail(self, obj):
        if not hasattr(obj, "message"):
            if not obj.pdf:
                return mark_safe(f"Bitte Pdf anlegen")
            # if not InvoiceMessage.objects.filter(invoice=obj).exists():
            url = reverse("admin:create-invoice-message", args=[obj.pk])
            return mark_safe(f"<a class='button' href='{url}'>Mail erzeugen</a>")
        else:
            url = (
                reverse("admin:mailings_invoicemessage_changelist")
                + f"?invoice__id__exact={obj.id}"
            )
            return mark_safe(f'<a href="{url}">zur Mail</a>')

    invoice_mail.short_description = "Mail"
    invoice_mail.allow_tags = True

    def create_invoice_message(self, request, invoice_id):
        """View function to create an InvoiceMessage and redirect to edit it."""
        invoice = Invoice.objects.get(pk=invoice_id)

        if hasattr(invoice, "message"):  # Prevent duplicate messages
            messages.warning(request, "Mail existiert bereits!")
            return redirect(reverse("admin:invoices_invoice_change", args=[invoice_id]))

        message = invoice.create_invoice_message()
        messages.success(request, "Mail wurde angelegt!")
        return redirect(
            reverse("admin:mailings_invoicemessage_change", args=[message.pk])
        )

    def recreate_invoice_pdf(self, request, invoice_id):
        invoice = Invoice.objects.get(id=invoice_id)
        if invoice.create_invoice_pdf():
            messages.success(
                request,
                f"PDF für Rechnung Invoice {invoice.invoice_number} wurde erzeugt.",
            )
        else:
            messages.error(
                request,
                f"PDF für Rechnung {invoice.invoice_number} konnte nicht erzeugt werden.",
            )
        return redirect(
            request.META.get("HTTP_REFERER", "admin:invoices_invoice_changelist")
        )


admin.site.register(Invoice, InvoiceAdmin)
