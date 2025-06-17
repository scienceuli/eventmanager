from django import forms
from django.utils import timezone

class SetDateForm(forms.Form):
    date = forms.DateField(
        label="Datum auswählen",
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )