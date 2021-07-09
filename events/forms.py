from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML, Div, Submit, ButtonHolder
from crispy_forms.bootstrap import PrependedAppendedText, InlineRadios

from events.models import EventMember


class EventMemberForm(forms.Form):

    MEMBERSHIP_CHOICES = (
        ("vdu", "VdÜ"),
        ("bf", "BücherFrauen"),
        ("il", "Illustratoren Organisation"),
        ("tv", "Texterverband"),
        ("jv", "Junge Verlagsmenschen"),
        ("sp", "Selfpublisher-Verband"),
        ("at", "ATICOM"),
    )

    # ref: https://stackoverflow.com/questions/9993939/django-display-values-of-the-selected-multiple-choice-field-in-a-template
    def selected_memberships_labels(self):
        return [
            label
            for value, label in self.fields["memberships"].choices
            if value in self["memberships"].value()
        ]

    ATTENTION_CHOICES = (
        ("vfll", "VFLL-Website oder -Blog"),
        ("pers", "persönliche Einladung"),
        ("info", "Info einer anderen Organisation"),
    )

    firstname = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    lastname = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    address_line = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
    )
    street = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    city = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    state = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        label="Bundesland",
        required=False,
    )
    postcode = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )
    phone = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )

    vfll = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    )

    memberships = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={"class": "text-xs  text-gray-600"}),
        choices=MEMBERSHIP_CHOICES,
        required=False,
    )
    attention = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={"class": "text-xs  text-gray-600"}),
        choices=ATTENTION_CHOICES,
        required=False,
    )

    attention_other = forms.CharField(
        max_length=64,
        widget=forms.TextInput(
            attrs={
                "class": "block w-full text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
    )

    education_bonus = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    )

    message = forms.CharField(
        label="Anmerkungen", widget=forms.Textarea, required=False
    )

    check = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    )

    # def clean_check(self):
    #    data = self.cleaned_data['check']
    #    if not data:
    #        raise ValidationError("Bitte bestätigen Sie die Einverständniserklärung.")
    #
    #    return data


TAKES_PART_CHOICES = (
    ("y", "teil"),
    ("n", "nicht teil"),
)

YES_NO_CHOICES = (
    ("y", "ja"),
    ("n", "nein"),
)

MEMBER_TYPE_CHOICES = (
    ("o", "ordentliches Mitglied"),
    ("k", "Kandidat/Kandidatin"),
    ("f", "Fördermitglied"),
    ("e", "Ehrenmitglied"),
)


class SymposiumForm(forms.Form):
    firstname = forms.CharField(
        label="Vorname", widget=forms.TextInput(attrs={"placeholder": "Vorname"})
    )
    lastname = forms.CharField(
        label="Nachname", widget=forms.TextInput(attrs={"placeholder": "Nachname"})
    )
    email = forms.CharField(
        label="E-Mail",
        widget=forms.TextInput(attrs={"placeholder": "E-Mail"}),
    )
    takes_part_in_mv = forms.ChoiceField(
        label="Ich nehme an der virtuellen Mitgliederversammlung des VFLL am Freitag, 17. September 2021",
        choices=TAKES_PART_CHOICES,
    )

    member_type = forms.ChoiceField(label="Ich bin", choices=MEMBER_TYPE_CHOICES)

    vote_transfer = forms.CharField(
        label="Ich nehme an der Mitgliederversammlung nicht teil und übertrage meine Stimme für alle Abstimmungen und Wahlen inhaltlich unbegrenzt an:",
        widget=forms.TextInput(attrs={"placeholder": "Stimmübertragung an"}),
    )

    vote_transfer_check = forms.ChoiceField(
        label="Ich habe mich rückversichert, dass die Person, der ich meine Stimme übertrage, ordentliches Mitglied im VFLL ist und an der virtuellen Mitgliederversammlung teilnehmen wird.",
        choices=YES_NO_CHOICES,
    )

    mv_check = forms.ChoiceField(
        label="Ich bin damit einverstanden, dass meine Kontaktdaten (Vor- und Nachname, E-Mail-Adresse) auf der internen Teilnahmeliste der Mitgliederversammlung stehen, die an Vorstand, Wahlleitung, Geschäftsstelle und eine Person von Votingtech weitergegeben wird.",
        choices=YES_NO_CHOICES,
    )

    takes_part_in_zw = forms.ChoiceField(
        label="Ich nehme an der Online-Veranstaltung Zukunftswerkstatt Freies Lektorat am Samstag/Sonntag, 18./19. September 2021",
        choices=TAKES_PART_CHOICES,
    )

    zw_check = forms.ChoiceField(
        label="Ich bin damit einverstanden, dass meine Kontaktdaten (Vor- und Nachname, E-Mail-Adresse) auf der internen Teilnahmeliste der „Zukunftswerkstatt Freies Lektorat“ stehen, die an den Vorstand, die Geschäftsstelle und zwei Personen der boscop eG als Veranstaltungsbetreuende weitergegeben wird.",
        choices=YES_NO_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Persönliche Daten",
                "firstname",
                "lastname",
                "email",
                HTML(
                    """
                    <p>Bitte beachten: Die Angabe einer aktuellen E-Mail-Adresse 
                    ist Voraussetzung für die Zusendung eines Zugangscodes für das
                    digitale Wahltool Votingtech während der Mitgliederversammlung.<br/> 
                    Ebenso wird ein Link zum Zoom-Raum für die „Zukunftswerkstatt 
                    Freies Lektorat“ versandt.</p>
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "1. Mitgliederversammlung",
                InlineRadios(
                    "takes_part_in_mv",
                ),
                InlineRadios(
                    "member_type",
                ),
                "vote_transfer",
                InlineRadios("vote_transfer_check"),
            ),
            Fieldset(
                "Einverständniserklärung",
                InlineRadios("mv_check"),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "2. Zukunftswerkstatt",
                InlineRadios("takes_part_in_zw"),
            ),
            Fieldset(
                "Einverständniserklärung",
                InlineRadios("zw_check"),
                HTML(
                    """
                    <p class="mt-4"><b>Für den Fall einer Nichtteilnahme nach Anmeldung zur „Zukunftswerkstatt Freies Lektorat“ bitte beachten:</b></p>
                    <p>Die Anzahl der Teilnehmenden an der „Zukunftswerkstatt Freies Lektorat“ ist begrenzt. Wer nicht teilnehmen kann, 
                    möge sich bitte per E-Mail an geschaeftsstelle@vfll.de wieder abmelden. 
                    Über den frei gewordenen Platz freut sich dann ein anderes Mitglied.</p>
                    """
                ),
                HTML(
                    """
                    <p class="mt-4"><b>Datenschutzhinweis:</b><br/>
                    Wir verwenden Deine Angaben ausschließlich zur Durchführung 
                    der Veranstaltungen des Verbands der freien Lektorinnen und 
                    Lektoren e.V. Deine Daten werden nicht an unbefugte Dritte 
                    weitergegeben. Verantwortlich im Sinne der DSGVO ist der 
                    Vorstand des Verbands der Freien Lektorinnen und Lektoren e.V.,
                    Geschäftsstelle, Büro Seehausen + Sandberg, 
                    Merseburger Straße 5, 10823 Berlin.</p>                    
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            ButtonHolder(
                Submit(
                    "submit",
                    "Anmelden",
                    css_class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-full",
                )
            ),
        )
        # self.helper.add_input(Submit("submit", "Anmelden"))

    def clean(self):
        cleaned_data = super().clean()
        fee = cleaned_data.get("fee")
        fee_amount = cleaned_data.get("fee_amount")

        if fee == "k":
            if not fee_amount:
                self.add_error("fee_amount", "Bitte einen Betrag angeben.")
                # raise forms.ValidationError("Bitte einen Betrag angeben.")
            elif fee_amount < 195:
                self.add_error("fee_amount", "Bitte mind. 195 Euro eingeben")
                # raise forms.ValidationError("Bitte mind. 195 Euro eingeben")
