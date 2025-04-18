from django import forms
from .models import EmailTemplate, NewsletterSubscription
from ckeditor.fields import RichTextFormField

from django.contrib.auth.models import User

ALL_RECIPIENTS_ID = "__all__"

class EmailTemplateForm(forms.ModelForm):

    recipients = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = EmailTemplate
        fields = ("subject", "title", "body", "recipients", 'use_mjml')
        widgets = {
            "body": forms.Textarea(),
        }

    

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        # first call parent's constructor
        super().__init__(*args, **kwargs)        # there's a `fields` property now
        self.subs = NewsletterSubscription.objects.all()
        #self.fields["recipients"].queryset = subs
        choices = [(ALL_RECIPIENTS_ID, "Alle Subscribers")] + [
            (str(sub.pk), str(sub)) for sub in self.subs
        ]
        self.fields["recipients"].choices = choices

        if instance and instance.pk:
            initial_pks = list(instance.recipients.values_list('pk', flat=True))
            self.initial["recipients"] = [str(pk) for pk in initial_pks]

    def clean_recipients(self):
        data = self.cleaned_data.get("recipients", [])
        if ALL_RECIPIENTS_ID in data:
            return self.subs
        else:
            valid_ids = [int(pk) for pk in data]
            return self.subs.filter(pk__in=valid_ids)
