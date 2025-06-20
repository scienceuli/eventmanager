from django.db import models
from ckeditor.fields import RichTextField


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    status = models.CharField(max_length=64, null=False, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Newsletter Subscription"
        verbose_name_plural = "Newsletter Subscriptions"

    def __str__(self):
        return self.email


class EmailTemplate(models.Model):
    subject = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    recipients = models.ManyToManyField(NewsletterSubscription)
    use_mjml = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, auto_created=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=1, default="a", choices=(("a", "active"), ("c", "cancelled"),), null=True, blank=True)

    def __str__(self):
        return self.subject
