from django.contrib import admin
from django import forms
from django.conf import settings
from django.core.mail import send_mail
from ckeditor.fields import RichTextFormField

from .models import NewsletterSubscription, EmailTemplate


class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at")
    list_filter = ["subscribed_at"]
    search_fields = ("email",)
    date_hierarchy = "subscribed_at"
    ordering = ("email", "subscribed_at")


admin.site.register(NewsletterSubscription, NewsletterSubscriptionAdmin)


class EmailTemplateAdminForm(forms.ModelForm):
    send_now = forms.BooleanField(required=False)

    class Meta:
        model = EmailTemplate
        fields = ("subject", "message", "recipients", "send_now")
        widgets = {
            "message": RichTextFormField(),
        }

    def __init__(self, *args, **kwargs):
        # first call parent's constructor
        super(EmailTemplateAdminForm, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        self.fields["recipients"].required = False


class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateAdminForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        send_now = form.cleaned_data["send_now"]
        if send_now:
            subject = obj.subject
            html_message = obj.message

            recipients = [subscriber.email for subscriber in obj.recipients.all()]
            if not recipients:
                recipients = [
                    subscriber.email
                    for subscriber in NewsletterSubscription.objects.all()
                ]
            from_email = settings.NEWSLETTER_EMAIL_FROM

            send_mail(
                subject,
                "",
                from_email,
                recipients,
                fail_silently=False,
                html_message=html_message,
            )


admin.site.register(EmailTemplate, EmailTemplateAdmin)
