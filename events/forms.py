from django import forms

class EventMemberForm(forms.Form):
    name = forms.CharField(label="Name", required=True)
    address = forms.CharField(label="Anschrift", widget=forms.Textarea, required=True)
    email = forms.EmailField(label="E-Mail", required=True)
    phone = forms.CharField(label="Telefon", required=True)
    message = forms.CharField(label="Anmerkungen", widget=forms.Textarea, required=False)