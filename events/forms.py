from django.utils import timezone

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from tinymce.widgets import TinyMCE


from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML, Div, Submit, ButtonHolder
from crispy_forms.bootstrap import PrependedAppendedText, InlineRadios

from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from django.forms.models import inlineformset_factory

from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm

from events.models import (
    Event,
    EventCategory,
    EventDocument,
    EventDay,
    EventMember,
    EventLocation,
    EventOrganizer,
)

from .widgets import RelatedFieldWidgetCanAddWithModal


class EventDocumentForm(forms.ModelForm):
    class Meta:
        model = EventDocument
        exclude = ()
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


EventDocumentFormSet = inlineformset_factory(
    Event,
    EventDocument,
    form=EventDocumentForm,
    fields=["title", "description", "upload"],
    extra=1,
    can_delete=True,
)


class EventDayForm(forms.ModelForm):
    """Form for Event Day Input.
    type='date' yields html5 date picker in form and passes date in YYYY-mm-dd form.
    for correct rendering of  initial date the same format must be specified in widget
    """

    start_date = forms.DateField(
        widget=forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"})
    )
    # start_date = forms.DateField(
    #     required=True,
    #     label="Datum",
    #     input_formats=["%d.%m.%Y"],
    #     error_messages={"invalid": "Datum im Format DD.MM.YYYY angeben."},
    #     widget=forms.DateInput(
    #         format="%d.%m.%Y",
    #         attrs={
    #             "placeholder": "DD.MM.YYYY",
    #             "type": "date",
    #         },
    #     ),
    # )
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    # start_time = forms.TimeField(
    #     required=True,
    #     label="Beginn",
    #     input_formats=["%H:%M"],
    #     error_messages={"invalid": "Zeit im Format HH:MM angeben."},
    #     widget=forms.TimeInput(
    #         format="%H:%M",
    #         attrs={
    #             "placeholder": "HH:MM",
    #             "type": "time",
    #         },
    #     ),
    # )
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    # end_time = forms.TimeField(
    #     required=True,
    #     label="Ende",
    #     input_formats=["%H:%M"],
    #     error_messages={"invalid": "Zeit im Format HH:MM angeben."},
    #     widget=forms.TimeInput(
    #         format="%H:%M",
    #         attrs={
    #             "placeholder": "HH:MM",
    #             "type": "time",
    #         },
    #     ),
    # )

    class Meta:
        model = EventDay
        exclude = ()

    def clean_start_date(self):
        start_date = self.cleaned_data.get("start_date")
        if start_date < timezone.now().date():
            raise forms.ValidationError("Das Startdatum liegt in der Vergangenheit")
        return start_date


EventDayFormSet = inlineformset_factory(
    Event,
    EventDay,
    form=EventDayForm,
    fields=["start_date", "start_time", "end_time"],
    extra=1,
    can_delete=True,
)

STATE_CHOICES = (
    ("kA", "*"),
    ("BW", "Baden-Württemberg"),
    ("BY", "Bayern"),
    ("BE", "Berlin"),
    ("BB", "Brandenburg"),
    ("HB", "Bremen"),
    ("HH", "Hamburg"),
    ("HE", "Hessen"),
    ("MV", "Mecklenburg-Vorpommern"),
    ("NI", "Niedersachsen"),
    ("NW", "Nordrhein-Westfalen"),
    ("RP", "Rheinland-Pfalz"),
    ("SL", "Saarland"),
    ("SN", "Sachsen"),
    ("ST", "Sachsen-Anhalt"),
    ("SH", "Schleswig-Holstein"),
    ("TH", "Thüringen"),
)


class EventCategoryFilterForm(BSModalForm):
    category = forms.ModelChoiceField(queryset=EventCategory.objects.all())

    class Meta:
        fields = ["category"]


class EventOrganizerModelForm(BSModalModelForm):
    class Meta:
        model = EventOrganizer
        fields = [
            "name",
            "contact",
            "url",
        ]


class EventLocationModelForm(BSModalModelForm):
    state = forms.ChoiceField(required=False, label="Bundesland", choices=STATE_CHOICES)

    class Meta:
        model = EventLocation
        fields = [
            "title",
            "address_line",
            "street",
            "postcode",
            "city",
            "state",
            "country",
            "url",
        ]


class EventModelForm(forms.ModelForm):
    # start_date = forms.DateTimeField(
    #     required=True,
    #     label="Beginn",
    #     input_formats=["%d.%m.%Y %H:%M"],
    #     error_messages={"invalid": "Datum/Zeit im Format DD.MM.YYYY HH:MM angeben."},
    #     widget=forms.DateTimeInput(
    #         format="%d.%m.%Y %H:%M",
    #         attrs={
    #             "placeholder": "DD.MM.YYYY HH:MM",
    #             "type": "datetime-local",
    #         },
    #     ),
    # )
    # end_date = forms.DateTimeField(
    #     required=False,
    #     label="Ende",
    #     input_formats=["%d.%m.%Y %H:%M"],
    #     error_messages={"invalid": "Datum/Zeit im Format DD.MM.YYYY HH:MM angeben."},
    #     widget=forms.DateTimeInput(
    #         format="%d.%m.%Y %H:%M",
    #         attrs={
    #             "placeholder": "DD.MM.YYYY HH:MM",
    #             "type": "datetime-local",
    #         },
    #     ),
    # )

    fees = forms.CharField(label="Gebühren", widget=TinyMCE(mce_attrs={"height": 200}))

    notes = forms.CharField(
        required=False, label="weitere Infos", widget=TinyMCE(mce_attrs={"height": 200})
    )

    notes_internal = forms.CharField(
        required=False,
        label="interne Hinweise",
        widget=TinyMCE(mce_attrs={"height": 200}),
    )

    location = forms.ModelChoiceField(
        label="Veranstaltungsort",
        # required=False,
        queryset=EventLocation.objects.all(),
        # widget=RelatedFieldWidgetCanAddWithModal(
        #    modal_id="create-event-location-sync", label="Veranstaltungsort"
        # ),
    )

    category = forms.ModelChoiceField(
        label="Kategorie",
        required=True,
        queryset=EventCategory.objects.all(),
    )

    organizer = forms.ModelChoiceField(
        label="Veranstalter",
        # required=False,
        queryset=EventOrganizer.objects.all(),
        # widget=RelatedFieldWidgetCanAddWithModal(
        #    modal_id="create-event-organizer-sync", label="Veranstalter"
        # ),
    )

    class Meta:
        model = Event
        fields = [
            "name",
            "category",
            "eventformat",
            "pub_status",
            "target_group",
            "fees",
            "location",
            "organizer",
            "contribution",
            "notes",
            "notes_internal",
        ]


from .choices import (
    MEMBERSHIP_CHOICES,
    ATTENTION_CHOICES,
    MEMBER_TYPE_CHOICES,
    TAKES_PART_CHOICES,
    YES_NO_CHOICES,
)


class EventMemberForm(forms.Form):

    # ref: https://stackoverflow.com/questions/9993939/django-display-values-of-the-selected-multiple-choice-field-in-a-template
    def selected_memberships_labels(self):
        return [
            label
            for value, label in self.fields["memberships"].choices
            if value in self["memberships"].value()
        ]

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
    company = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
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
        label="Land",
        required=False,
    )

    country = CountryField().formfield(
        widget=CountrySelectWidget(
            attrs={
                "class": "mt-1 block w-full p-3 text-gray-700 bg-gray-200 focus:outline-none  focus:bg-gray-300 sm:text-sm "
            }
        )
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

    free_text_field = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
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


class SymposiumForm(forms.Form):
    def member_type_label(self):
        return [
            label
            for value, label in self.fields["member_type"].choices
            if value in self["member_type"].value()
        ]

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
        label="Ich nehme an der Mitgliederversammlung nicht teil und übertrage als ordentliches Mitglied meine Stimme für alle Abstimmungen und Wahlen inhaltlich unbegrenzt an:",
        widget=forms.TextInput(attrs={"placeholder": "Stimmübertragung an"}),
        required=False,
    )

    vote_transfer_check = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
        label="Ich habe mich rückversichert, dass die Person, der ich meine Stimme übertrage, ordentliches Mitglied im VFLL ist und an der virtuellen Mitgliederversammlung teilnehmen wird.",
    )

    mv_check = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
        label=mark_safe(
            "Ich bin damit einverstanden, dass meine Kontaktdaten (Vor- und Nachname, <br/>E-Mail-Adresse) auf der internen Teilnahmeliste der Mitgliederversammlung stehen, die an Vorstand, Wahlleitung und Geschäftsstelle weitergegeben wird."
        ),
    )

    takes_part_in_zw = forms.ChoiceField(
        label="Ich nehme an der Online-Veranstaltung Zukunftswerkstatt Freies Lektorat am Samstag/Sonntag, 18./19. September 2021",
        choices=TAKES_PART_CHOICES,
    )

    zw_check = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
        label=mark_safe(
            "Ich bin damit einverstanden, dass meine Kontaktdaten (Vor- und Nachname, <br/>E-Mail-Adresse) auf der internen Teilnahmeliste der „Zukunftswerkstatt Freies Lektorat“ stehen, die an den Vorstand, die Geschäftsstelle und zwei Personen der boscop eG als Veranstaltungsbetreuende weitergegeben wird."
        ),
    )

    def __init__(self, *args, **kwargs):
        self.event_label = kwargs.pop("event_label", "")
        super(SymposiumForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_error_title = "Fehler im Formular"
        self.error_text_inline = False
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
                    digitale Wahltool Votingtech und einer Einladungsmail für das Videokonferenztool Clickmeeting – beide Tools werden während der Mitgliederversammlung genutzt.<br/> 
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
                    required=True,
                ),
                InlineRadios(
                    "member_type",
                    required=True,
                ),
                "vote_transfer",
                "vote_transfer_check",
            ),
            Fieldset(
                "Einverständniserklärung",
                HTML(
                    """
                    <p><i>Die Zustimmung zur Einverständniserklärung ist notwendig, 
                    um den technisch-organisatorischen Zugang zur Veranstaltung zu 
                    gewährleisten.</i></p>
                    """
                ),
                "mv_check",
                HTML(
                    """
                    <hr class="my-12 pt-4"/>
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "2. Zukunftswerkstatt",
                InlineRadios("takes_part_in_zw", required=True),
            ),
            Fieldset(
                "Einverständniserklärung",
                HTML(
                    """
                    <p><i>Die Zustimmung zur Einverständniserklärung ist notwendig, 
                    um den technisch-organisatorischen Zugang zur Veranstaltung zu 
                    gewährleisten.</i></p>
                    """
                ),
                "zw_check",
                HTML(
                    """
                    <p class="mt-4"><b>Falls ihr euch für die „Zukunftswerkstatt Freies Lektorat“ 
                    angemeldet habt und doch nicht teilnehmen könnt, 
                    bitten wir euch um eine frühzeitige Absage per <br/>
                    E-Mail an: geschaeftsstelle@vfll.de. </b></p>
                    """
                ),
                HTML(
                    """
                    <p class="mt-4"><b>Datenschutzhinweis:</b><br/>
                    Wir verwenden deine Angaben ausschließlich zur Durchführung 
                    der Veranstaltungen des Verbands der Freien Lektorinnen und 
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
        vote_transfer = cleaned_data.get("vote_transfer")
        vote_transfer_check = cleaned_data.get("vote_transfer_check")
        takes_part_in_mv = cleaned_data.get("takes_part_in_mv")
        takes_part_in_zw = cleaned_data.get("takes_part_in_zw")
        mv_check = cleaned_data.get("mv_check")
        zw_check = cleaned_data.get("zw_check")
        member_type = cleaned_data.get("member_type")

        if takes_part_in_mv != "y":
            if vote_transfer and not vote_transfer_check:
                self.add_error(
                    "vote_transfer_check", "Bitte für Stimmübertragung bestätigen"
                )
            if vote_transfer and member_type != "o":
                self.add_error(
                    "vote_transfer",
                    "Stimmübertragung nur für ordentliche Mitglieder möglich",
                )
            if takes_part_in_zw != "y" and not vote_transfer:
                self.add_error(
                    "vote_transfer",
                    "Bitte mindestens eine Teilnahme (MV oder Zukunftswerkstatt) angeben oder für die MV eine Stimmübertragung festlegen!",
                )
        else:
            if vote_transfer:
                self.add_error(
                    "vote_transfer", "Stimmübertragung nur bei Nichtteilnahme möglich"
                )
            if vote_transfer_check:
                self.add_error(
                    "vote_transfer_check",
                    "Stimmübertragung nur bei Nichtteilnahme möglich",
                )
            if not mv_check:
                self.add_error(
                    "mv_check",
                    "Bestätigung der Einverständniserklärung notwendig für Teilnahme",
                )
        if takes_part_in_zw == "y" and not zw_check:
            self.add_error(
                "zw_check",
                "Bestätigung der Einverständniserklärung notwendig für Teilnahme",
            )

    def clean_email(self):
        data = self.cleaned_data["email"]
        if (
            EventMember.objects.filter(
                email=data, event__label=self.event_label
            ).count()
            > 0
        ):
            raise forms.ValidationError(
                "Es gibt bereits eine Anmeldung mit dieser E-Mail-Adresse."
            )
        return data


class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = [
            "firstname",
            "lastname",
            "email",
        ]


class EventUpdateCapacityForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["capacity"]
