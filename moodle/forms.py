from django import forms

from events.models import Event

class EventForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    event = forms.ModelChoiceField(queryset=Event.objects.all())
