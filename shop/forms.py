from django import forms

EVENT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 2)]


class CartAddEventForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=EVENT_QUANTITY_CHOICES, widget=forms.HiddenInput, coerce=int, initial=1
    )
    override = forms.BooleanField(
        required=False, initial=True, widget=forms.HiddenInput
    )
