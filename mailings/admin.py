from functools import update_wrapper

from django.utils.html import format_html, mark_safe

from django.contrib import admin

from admin_confirm import AdminConfirmMixin, confirm_action

from django.conf import settings

from .models import InvoiceMessage, ConfirmationMessage
from vfllnl.models import NewsletterImage
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

    @confirm_action
    def set_mails_to_sent_with_confirm(self, request, queryset):
        for invoice_mail in queryset.select_related('invoice'):
            invoice_mail.sent = True
            invoice_mail.last_attempt = invoice_mail.invoice.invoice_date
            invoice_mail.save()

    set_mails_to_sent_with_confirm.short_description = "Markieren als gesendet"

    actions = [
        'send_failed_with_confirm',
        'resend_emails_with_confirm',
        'mark_unsent_with_confirm',
        'set_mails_to_sent_with_confirm',
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


@admin.register(ConfirmationMessage)
class ConfirmationMessageAdmin(AdminConfirmMixin, MailerAdmin):
    model = ConfirmationMessage

    list_display = [
        "member_name_display",
        "event_display",
        "sent",
        "last_attempt",
    ]
    list_filter = ["sent"]

    @confirm_action
    def resend_emails_with_confirm(self, request, queryset):
        return super().resend_emails(request, queryset)

    @confirm_action
    def mark_unsent_with_confirm(self, request, queryset):
        return super().mark_unsent(request, queryset)

    resend_emails_with_confirm.short_description = "E-Mails senden"
    mark_unsent_with_confirm.short_description = "Markieren als ungesendet"

    actions = [
        "resend_emails_with_confirm",
        "mark_unsent_with_confirm",
    ]

    def member_name_display(self, obj):
        if obj.confirmation and obj.confirmation.event_member:
            member = obj.confirmation.event_member
            return f"{member.lastname}, {member.firstname}"
        return "—"

    member_name_display.short_description = "Teilnehmer*in"

    def event_display(self, obj):
        if obj.confirmation and obj.confirmation.event_member:
            return obj.confirmation.event_member.event.name
        return "—"

    event_display.short_description = "Veranstaltung"


@admin.register(NewsletterImage)
class NewsletterImageAdmin(admin.ModelAdmin):
    list_display = ["title", "image_preview", "image_url_display", "uploaded_at"]
    readonly_fields = ["image_preview", "image_url_display", "uploaded_at"]

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 80px;">')
        return "—"
    image_preview.short_description = "Vorschau"

    def image_url_display(self, obj):
        if obj.image:
            domain = getattr(settings, "EMAIL_LINK_DOMAIN", "").rstrip("/")
            full_url = f"{domain}{obj.image.url}"
            return mark_safe(
                f'<input type="text" value="{full_url}" readonly '
                f'style="width: 500px; cursor: pointer;" '
                f'onclick="this.select(); document.execCommand(\'copy\');">'
            )
        return "—"
    image_url_display.short_description = "Bild-URL (zum Kopieren)"
