from django.contrib import admin
from django.utils.html import mark_safe, format_html
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect

from invoices.models import Invoice, StandardInvoice, StornoInvoice
from invoices.actions import export_to_excel_short, export_pdfs_as_zip, set_date_action, set_paid_action
from invoices.filter import InvoiceEventListFilter, InvoicesYearQuarterFilter
from mailings.models import InvoiceMessage
from shop.models import OrderNote




#class InvoiceAdmin(admin.ModelAdmin):
class StandardInvoiceAdmin(admin.ModelAdmin):

    change_list_template = "admin/invoices/standardinvoice/change_list.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        base_url = reverse('admin:invoices_standardinvoice_changelist')
        buttons = [
            {'label': 'Alle Filter aufhaben', 'url': base_url},
        ]
        extra_context['filter_buttons'] = buttons
        return super().changelist_view(request, extra_context=extra_context)


    def queryset(self, request):
        qs = super(StandardInvoiceAdmin, self).queryset(request)
        return qs.filter(invoice_type="i")
    
    list_display = (
        "name",
        "order_button",
        "amount",
        "invoice_number",
        "invoice_date",
        "invoice_type",
        "invoice_mail",
        # "is_paid",
        "paid_button",
        "get_invoice_receipt_formatted",
        # "create_invoice_message_button",
        "mail_sent_date",
        "invoice_export",
        "pdf",
        "pdf_exported",
        "pdf_export",
        "recreate_invoice_pdf_button",
        "get_storno",
        # "view_notes_button",
        # 'note_preview',
        'notes_popup_icon',
        'add_note_link',
    )
    actions = [
        export_to_excel_short, export_pdfs_as_zip, set_date_action, set_paid_action
    ]
    export_to_excel_short.short_description = "Export -> Excel (St.)"
    export_pdfs_as_zip.short_description = "Export PDFs -> ZIP"

    list_filter = [
        "invoice_type",
        "invoice_date",
        "invoice_receipt",
        InvoiceEventListFilter,
        InvoicesYearQuarterFilter
        ]

    search_fields = [
        "name",
        "invoice_number",
        "order__items__event__name"
    ]

    def add_note_link(self, obj):
        if obj.order:
            url = reverse('admin:shop_ordernote_add') + f'?order={obj.order.id}&next={reverse("admin:invoices_standardinvoice_changelist")}'
            return format_html(
                '<a href="{}" onclick="window.open(this.href, \'addNote\', \'width=600,height=400\'); return false;" title="Add Note">📝 Add</a>',
                url
            )
        else:
            return "kB"
        
    add_note_link.short_description = format_html('🔖')

    def view_notes_button(self, obj):
        note_count = obj.order.notes.count()
        if note_count == 0:
            return "—"
        url = reverse('admin:shop_ordernote_changelist') + f'?order__id__exact={obj.order.id}'
        return format_html(
            '<a class="button" href="{}" target="_blank">View Notes ({})</a>',
            url,
            note_count
        )
    view_notes_button.short_description = "Notes"
    view_notes_button.allow_tags = True

    def note_preview(self, obj):
        notes = obj.order.notes.all()
        return format_html('<br>'.join(note.note[:30] for note in notes))

    def notes_popup_icon(self, obj):
        if not obj.order:
            return ""
        notes = obj.order.notes.all()
        if not notes:
            return ""
        url = reverse('admin:shop_ordernote_changelist') + f'?order__id__exact={obj.order.id}'
        return format_html(
            '<a href="{}" onclick="window.open(this.href, \'notesPopup\', \'width=600,height=400\'); return false;" title="Notizen">📝 ({})</a>',
            url,
            notes.count()
        )
    notes_popup_icon.short_description = "Notes"

    def get_invoice_receipt_formatted(self, obj):
        if obj:
            if obj.invoice_receipt:
                return obj.invoice_receipt.date().strftime("%d.%m.%Y")
            return "-"
        
    get_invoice_receipt_formatted.admin_order_field = 'invoice_receipt'
    get_invoice_receipt_formatted.short_description = 'Rechnungseingang'
    
    @admin.display(boolean=True, description='bez.')
    def is_paid(self, obj):
        return obj.invoice_receipt is not None

    
    
    @admin.display(boolean=True, description='↓')
    def pdf_exported(self, obj):
        return obj.pdf and obj.pdf_export is not None

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
            path(
                "create_storno/<int:invoice_id>/",
                self.admin_site.admin_view(self.create_storno_invoice),
                name="create-storno-invoice",
            ),
            path(
                "set_paid/<int:invoice_id>/",
                self.admin_site.admin_view(self.set_paid_view),
                name="set-invoice-paid",
            ),
        ]
        return custom_urls + urls
    
    def set_paid_view(self, request, invoice_id):
        invoice = self.get_object(request, invoice_id)
        if invoice and not invoice.invoice_receipt:
            invoice.set_paid()
            self.message_user(request, f"Rechnung {invoice.invoice_number} als bez. markiert.", messages.SUCCESS)
        else:
            self.message_user(request, f"Rechnung bereits bezahlt.", messages.INFO)
        return redirect(request.META.get("HTTP_REFERER", "/admin/"))
    
    def paid_button(self, obj):
        if obj.invoice_receipt:
            return format_html('✅')
        if not obj.invoice_receipt and not obj.mail_sent_date:
            return format_html('❌')
        
        url = reverse("admin:set-invoice-paid", args=[obj.pk])
        return mark_safe(
            f"<a  href='{url}'>💰</a>"
        )

    paid_button.short_description = "bez."

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
            return redirect(reverse("admin:invoices_standardinvoice_change", args=[invoice_id]))

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
            request.META.get("HTTP_REFERER", "admin:invoices_standardinvoice_changelist")
        )

    def get_storno(self, obj):
        if hasattr(obj, "storno_invoice") and obj.storno_invoice:
            # if obj.storno_invoice:
            url = reverse(
                "admin:invoices_stornoinvoice_change", args=[obj.storno_invoice.id]
            )
            return mark_safe(f'<a href="{url}">zur Storno-Rechnung</a>')
        else:
            url = reverse(
                "admin:create-storno-invoice", args=[obj.pk]
            )  # reverse("admin:create-invoice-message", args=[obj.pk])
            return mark_safe(f"<a class='button' href='{url}'>Storno erzeugen</a>")

    get_storno.short_description = "Storno-Rechnung"
    get_storno.allow_tags = True

    def create_storno_invoice(self, request, invoice_id):
        invoice = Invoice.objects.get(pk=invoice_id)

        if (
            hasattr(invoice, "storno_invoice") and invoice.storno_invoice
        ):  # Prevent duplicate messages
            messages.warning(request, "Storno-Rechnung existiert bereits!")
            return redirect(reverse("admin:invoices_standardinvoice_change", args=[invoice_id]))

        storno = invoice.create_storno_invoice()
        messages.success(request, "Storno-Rechnung wurde angelegt!")
        return redirect(
            reverse("admin:invoices_stornoinvoice_change", args=[storno.pk])
        )

    


admin.site.register(StandardInvoice, StandardInvoiceAdmin)


class StornoInvoiceAdmin(admin.ModelAdmin):
    def queryset(self, request):
        qs = super(StornoInvoiceAdmin, self).queryset(request)
        return qs.filter(invoice_type="s")

    exclude = ('storno_invoice', 'invoice_receipt')
    
    list_display = (
        "name",
        "amount",
        "invoice_number",
        "invoice_date",
        "invoice_type",
        "pdf",
        "pdf_export",
        "get_original_invoice",
    )
    readonly_fields = ("order", "invoice_number", "pdf", "pdf_export", "invoice_type")

    list_filter = (
        InvoicesYearQuarterFilter,
    )
    actions = [
        export_to_excel_short, export_pdfs_as_zip, set_date_action
    ]
    export_to_excel_short.short_description = "Export -> Excel (St.)"
    export_pdfs_as_zip.short_description = "Export PDFs -> ZIP"

    def get_original_invoice(self, obj):
        if hasattr(obj, "original_invoice") and obj.original_invoice:
            # if obj.storno_invoice:
            url = reverse(
                "admin:invoices_standardinvoice_change", args=[obj.original_invoice.id]
            )
            return mark_safe(f'<a href="{url}">zur Original-Rechnung</a>')
        else:
            return ""

    get_original_invoice.short_description = "Original-Rechnung"
    get_original_invoice.allow_tags = True


admin.site.register(StornoInvoice, StornoInvoiceAdmin)
