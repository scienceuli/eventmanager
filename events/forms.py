from django import forms

class EventMemberForm(forms.Form):

    MEMBERSHIP_CHOICES = (
        ('vdu', 'VdÜ'),
        ('bf', 'BücherFrauen'),
        ('il', 'Illustratoren Organisation'),
        ('tv', 'Texterverband'),
        ('jv', 'Junge Verlagsmenschen'),
        ('sp', 'Selfpublisher-Verband'),
        ('at', 'ATICOM')
    )

    ATTENTION_CHOICES = (
        ('vfll','VFLL-Website oder -Blog'),
        ('pers', 'persönliche Einladung'),
        ('info', 'Info einer anderen Organisation')
    )

    firstname = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=True)
    lastname = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=True)
    address_line = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=False)
    street = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}), 
        required=True)
    city = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=True)
    state = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        label="Bundesland", required=False)
    postcode = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
         required=True)
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=True)
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=True)

    vfll = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class' : 'form-radio'}),
        required=False)

    memberships = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'text-xs  text-gray-600'}),
        choices=MEMBERSHIP_CHOICES, 
        required=False)
    attention = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'text-xs  text-gray-600'}),
        choices=ATTENTION_CHOICES, 
        required=False)

    attention_other = forms.CharField(
        widget=forms.TextInput(attrs={'class' : 'block w-full text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner'}),
        required=False)

    education_bonus = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class' : 'form-radio'}),
        required=False)

    message = forms.CharField(label="Anmerkungen", widget=forms.Textarea, required=False)

    check = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class' : 'form-radio'}),
        required=True)


    def clean_check(self):
        data = self.cleaned_data['check']
        if not data:
            raise ValidationError("Bitte bestätigen Sie die Einverständniserklärung.")

        return data