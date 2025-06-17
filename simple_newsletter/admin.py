from django.contrib import admin
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.template.loader import render_to_string

from .models import NewsletterSubscription, EmailTemplate
from .forms import EmailTemplateForm


class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "subscribed_at", "updated_at")
    list_filter = ["subscribed_at"]
    search_fields = ("email",)
    date_hierarchy = "subscribed_at"
    ordering = ("email", "subscribed_at")


admin.site.register(NewsletterSubscription, NewsletterSubscriptionAdmin)





class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateForm
    fields = ("subject", "title", "body", "recipients", 'use_mjml', "created_at", "created_by", "sent_at")
    readonly_fields = ["created_at", "created_by", "sent_at"]


admin.site.register(EmailTemplate, EmailTemplateAdmin)
