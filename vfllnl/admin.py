from django.contrib import admin
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.template.loader import render_to_string

from .constants import SUBSCRIBE_STATUS_CONFIRMED, SUBSCRIBE_STATUS_SUBSCRIBED
from .models import NewsletterSubscription, EmailTemplate
from .forms import EmailTemplateForm


class SubscriptionStatusFilter(admin.SimpleListFilter):
    """Status filter that shows only confirmed subscriptions by default."""

    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [
            (SUBSCRIBE_STATUS_SUBSCRIBED, "Unbestätigt"),
            ("all", "Alle"),
        ]

    def choices(self, changelist):
        value = self.value()
        yield {
            "selected": value is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": "Bestätigt",
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == lookup,
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup}
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            return queryset.filter(status=SUBSCRIBE_STATUS_CONFIRMED)
        if value == "all":
            return queryset
        return queryset.filter(status=value)


class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "subscribed_at", "updated_at")
    list_filter = [SubscriptionStatusFilter, "subscribed_at"]
    search_fields = ("email",)
    date_hierarchy = "subscribed_at"
    ordering = ("email", "subscribed_at")


admin.site.register(NewsletterSubscription, NewsletterSubscriptionAdmin)





class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateForm
    fields = ("subject", "title", "body", "recipients", 'use_mjml', "created_at", "created_by", "sent_at")
    readonly_fields = ["created_at", "created_by", "sent_at"]


admin.site.register(EmailTemplate, EmailTemplateAdmin)
