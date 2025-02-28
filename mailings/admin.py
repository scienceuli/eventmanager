from django.utils.html import format_html, mark_safe

from django.contrib import admin

from .models import InvoiceMessage

from mailqueue.admin import MailerAdmin  # Import base admin class


@admin.register(InvoiceMessage)
class InvoiceMessageAdmin(MailerAdmin):
    model = InvoiceMessage

    list_display = [
        "invoice_name_display",
        "invoice_display",
        "invoice_lastname_firstname_display",
        "invoice_date_display",
        "mail_type",
        "sent",
        "last_attempt",
    ]

    def invoice_name_display(self, obj):
        return obj.invoice.name if obj.invoice else "keine Rechnung"

    invoice_name_display.admin_order_field = (
        "invoice__name"  # Enables sorting by invoice name
    )
    invoice_name_display.short_description = "Rechnungs-Mail"

    def related_invoice_link(self, obj):
        """Creates a clickable link to the related Invoice admin page."""
        if hasattr(obj, "invoice") and obj.invoice:  # Ensure the invoice exists
            url = f"/admin/myapp/invoice/{obj.invoice.id}/change/"  # Adjust app/model names
            return format_html('<a href="{}">{}</a>', url, f"Invoice {obj.invoice.id}")
        return "No Invoice"

    related_invoice_link.short_description = "Related Invoice"

    def invoice_display(self, obj):
        if hasattr(obj, "invoice") and obj.invoice:
            url = f"/admin/invoices/invoice/{obj.invoice.id}/change/"
            return mark_safe(f'<a href="{url}">{obj.invoice.invoice_number}</a>')

        return "keine Rechnung"

    invoice_display.admin_order_field = "invoice"  # Enables sorting by order
    invoice_display.short_description = "Rechnung"  # Column name in admin

    def invoice_lastname_firstname_display(self, obj):
        if obj.invoice and obj.invoice.order:
            return (
                f"{obj.invoice.order.lastname}, {obj.invoice.order.firstname}"
                if obj.invoice.order.lastname and obj.invoice.order.firstname
                else ""
            )
        return ""

    invoice_lastname_firstname_display.admin_order_field = (
        "invoice"  # Enables sorting by order
    )
    invoice_lastname_firstname_display.short_description = (
        "Rechnungsempfänger"  # Column name in admin
    )

    def invoice_date_display(self, obj):
        if obj.invoice:
            return obj.invoice.invoice_date
        return ""

    invoice_date_display.admin_order_field = "invoice"  # Enables sorting by order
    invoice_date_display.short_description = "Rechnungsdatum"  # Column name in admin
