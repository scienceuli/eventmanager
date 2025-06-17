from functools import update_wrapper

from django.utils.html import format_html, mark_safe

from django.contrib import admin

from admin_confirm import AdminConfirmMixin, confirm_action

from .models import InvoiceMessage
from django.urls import reverse

from mailqueue.admin import MailerAdmin  # Import base admin class



@admin.register(InvoiceMessage)
class InvoiceMessageAdmin(AdminConfirmMixin, MailerAdmin):
    model = InvoiceMessage
    change_list_template = "admin/mailings/invoicemessage/change_list.html"

    list_display = [
        "invoice_name_display",
        "invoice_display",
        "invoice_lastname_firstname_display",
        "invoice_date_display",
        "mail_type",
        "sent",
        "last_attempt",
    ]
    list_filter = ["mail_type", "sent"]

    @confirm_action
    def resend_emails_with_confirm(self, request, queryset):
        return super().resend_emails(request, queryset)
    
    @confirm_action
    def send_failed_with_confirm(self, request, queryset):
        return super().send_failed(request, queryset)
    
    @confirm_action
    def mark_unsent_with_confirm(self, request, queryset):
        return super().mark_unsent(request, queryset)
    
    mark_unsent_with_confirm.short_description = "Markieren als ungesendet"
    send_failed_with_confirm.short_description = "Versenden fehlgeschlagen"
    resend_emails_with_confirm.short_description = "E-Mails senden"

    actions = [
        'send_failed_with_confirm',
        'resend_emails_with_confirm',
        'mark_unsent_with_confirm'
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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        base_url = reverse('admin:mailings_invoicemessage_changelist')
        buttons = [
            {'label': 'Zeige alle', 'url': base_url},
            {'label': 'Mails Rechn.', 'url': f'{base_url}?mail_type=i'},
            {'label': 'Mails Storno-R.', 'url': f'{base_url}?mail_type=s'},
        ]
        extra_context['filter_buttons'] = buttons
        return super().changelist_view(request, extra_context=extra_context)


class SentMailsAdmin(admin.ModelAdmin):
    list_display = ("id", "view_email_logs")  # Add the button to the admin list

    def view_email_logs(self, obj):
        url = reverse("mailings:view-emails")
        return format_html(
            '<a href="{}" target="_blank" class="button">Gesendete Emails</a>', url
        )

    view_email_logs.short_description = "Email Logs"


