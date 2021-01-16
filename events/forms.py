from django import forms

class EventMemberForm(forms.Form):
    name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)