# from ctypes import HRESULT
from django.utils import timezone

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_tables2 import CheckBoxColumn
from django.core.validators import validate_email
from django.utils.html import escape
from django.contrib.admin.widgets import AdminDateWidget
from jinja2 import ChainableUndefined

from regex import B
from tinymce.widgets import TinyMCE
from entangled.forms import EntangledModelForm


from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout,
    Fieldset,
    HTML,
    Div,
    Submit,
    ButtonHolder,
    Row,
    Column,
    Field,
)
from crispy_forms.bootstrap import PrependedAppendedText, InlineRadios, InlineCheckboxes

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

from .api_models import VfllMemberEmail

from .widgets import RelatedFieldWidgetCanAddWithModal, MyRadioSelect


class CustomCheckbox(Field):
    template = "events/custom_checkbox.html"


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
    ("kA", "---"),
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
    category = forms.ModelChoiceField(
        queryset=EventCategory.shown_event_categories.all()
    )

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


class EventOrganizerNMModelForm(forms.ModelForm):
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


class EventLocationNMModelForm(forms.ModelForm):
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
        required=False,
        queryset=EventLocation.objects.all(),
        # widget=RelatedFieldWidgetCanAddWithModal(
        #    modal_id="create-event-location-sync", label="Veranstaltungsort"
        # ),
    )

    category = forms.ModelChoiceField(
        label="Kategorie",
        required=True,
        queryset=EventCategory.shown_event_categories.all(),
    )

    registration_possible = forms.BooleanField(label="Anmeldeformular", required=False)

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
            "eventurl",
            "target_group",
            "fees",
            "price",
            "location",
            "organizer",
            "registration_possible",
            "contribution",
            "notes",
            "notes_internal",
        ]


from .choices import (
    MEMBERSHIP_CHOICES,
    ATTENTION_CHOICES,
    MEMBER_TYPE_CHOICES,
    MEMBERSHIP_CHOICES_24_FULL,
    TAKES_PART_CHOICES,
    WS2022_CHOICES,
    TOUR_CHOICES,
    FOOD_PREFERENCE_CHOICES,
    BOOKING_CHOICES_27,
    BOOKING_CHOICES_28,
    BOOLEAN_CHOICES,
    YES_NO_CHOICES,
)


class MemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["lastname", "firstname", "email", "attend_status"]


class EventMemberForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["education_bonus"].initial = False

    # ref: https://stackoverflow.com/questions/9993939/django-display-values-of-the-selected-multiple-choice-field-in-a-template
    def selected_memberships_labels(self):
        return [
            label
            for value, label in self.fields["memberships"].choices
            if value in self["memberships"].value()
        ]

    academic = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
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
    company = forms.CharField(
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
        required=False,
    )

    # the onclick attribute is for changing the price if vfll member
    vfll = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={"class": "form-radio", "onclick": "changePrice()"}
        ),
        required=False,
        initial=False,
    )

    memberships = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "text-xs  text-gray-600", "onclick": "changePrice()"}
        ),
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

    # education_bonus = forms.BooleanField(
    #    widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    # )
    education_bonus = forms.BooleanField(
        widget=forms.HiddenInput(), required=False, initial=False
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

    agree = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    )

    newsletter = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}), required=False
    )

    # def clean_check(self):
    #    data = self.cleaned_data['check']
    #    if not data:
    #        raise ValidationError("Bitte bestätigen Sie die Einverständniserklärung.")
    #
    #    return data

    # def clean(self):
    #     cleaned_data = super().clean()
    #     vfll = cleaned_data.get("vfll")
    #     if not vfll and self.instance.vfll_only:
    #         self.add_error(
    #             "Veranstaltung ist nur für Mitglieder. Bitte entsprechende Checkbox bestätigen."
    #         )


class WelcomeMemberForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.event_label = kwargs.pop("event_label", "")
        super(WelcomeMemberForm, self).__init__(*args, **kwargs)
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
                    <p class='mb-2'><small>Bitte beachten: Bitte benutzen Sie die E-Mail-Adresse, mit der Sie beim VFLL
                    registriert sind.</small
                    </p>
                    """
                ),
                "member_type",
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

    def member_type_label(self):
        return [
            label
            for value, label in self.fields["member_type"].choices
            if value in self["member_type"].value()
        ]

    firstname = forms.CharField(
        label="Vorname",
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            },
        ),
        required=True,
    )
    lastname = forms.CharField(
        label="Nachname",
        widget=forms.TextInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )

    email = forms.EmailField(
        label="E-Mail",
        widget=forms.EmailInput(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=True,
    )

    member_type = forms.ChoiceField(label="Ich bin", choices=MEMBER_TYPE_CHOICES)

    def clean_email(self):
        email = self.cleaned_data["email"]

        # Check if the email already exists in the local Email model
        if not VfllMemberEmail.objects.filter(email=email).exists():
            self.add_error(
                "email",
                "Diese E-Mail ist in der Geschäftsstelle nicht bekannt. Bitte prüfen Sie Ihre Eingabe und wenden Sie sich ggf. an die Geschäftsstelle.",
            )

        return email


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
                    ist Voraussetzung für die Zusendung eines Zugangscodes für das digitale Wahltool und des Links für die Videokonferenz. 
                    </p>
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


class MV2023Form(forms.Form):
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
            "Ich bin damit einverstanden, das meine Daten (E-Mail-Adresse, Vor- und Nachname, Status der Stimmberechtigung) auf der internen Teilnahmeliste der Mitgliederversammlung stehen, die an Vorstand, Wahlleitung, Geschäftsstelle und an Lindmanns – Lebendige Online-Veranstaltungen weitergegeben werden. Ich habe zur Kenntnis genommen, dass diese Daten zum Versand der digitalen Stimmzettel sowie zur Durchführung der Wahlen und Abstimmungen mit dem Wahltool benötigt und nach Abschluss der Veranstaltung gelöscht werden."
        ),
    )

    def __init__(self, *args, **kwargs):
        self.event_label = kwargs.pop("event_label", "")
        super(MV2023Form, self).__init__(*args, **kwargs)
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
                    ist Voraussetzung für die Zusendung eines Zugangscodes für das digitale Wahltool und des Links für die Videokonferenz. 
                    </p>
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "Mitgliederversammlung",
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
        mv_check = cleaned_data.get("mv_check")
        member_type = cleaned_data.get("member_type")

        if vote_transfer_check and not vote_transfer:
            self.add_error("vote_transfer", "Bitte ordentliches VFLL-Mitglied angeben")

        if vote_transfer and not vote_transfer_check:
            self.add_error(
                "vote_transfer_check", "Bitte für Stimmübertragung bestätigen"
            )
        if vote_transfer and member_type != "o":
            self.add_error(
                "vote_transfer",
                "Stimmübertragung nur für ordentliche Mitglieder möglich",
            )

        if not mv_check:
            self.add_error(
                "mv_check",
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
                "Es gibt bereits eine Anmeldung mit dieser E-Mail-Adresse.",
                code="email_already_registered",
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


class Symposium2024Form(forms.Form):
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
    address_line = forms.CharField(
        label="Adresszusatz",
        widget=forms.TextInput(attrs={"placeholder": "Adresszusatz"}),
        required=False,
    )
    street = forms.CharField(
        label="Straße, Hausnummer",
        widget=forms.TextInput(attrs={"placeholder": "Straße, Hausnummer"}),
    )
    postcode = forms.CharField(
        label="PLZ", widget=forms.TextInput(attrs={"placeholder": "PLZ"})
    )
    city = forms.CharField(
        label="Ort", widget=forms.TextInput(attrs={"placeholder": "Ort"})
    )
    email = forms.EmailField(
        label="E-Mail",
        widget=forms.TextInput(attrs={"placeholder": "E-Mail"}),
    )
    phone = forms.CharField(
        label="Telefonnummer",
        widget=forms.TextInput(attrs={"placeholder": "Telefonnummer"}),
        required=False,
    )

    takes_part_in_ft = forms.BooleanField(
        label="Ich nehme an der Fachtagung teil.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio mb-0"}),
        required=False,
        help_text="(Kosten für Mitglieder des VFLL oder einiger Partnerverbände: 140&nbsp;€, Kosten für sonstige Teilnehmende: 190&nbsp;€, bitte unter Punkt&nbsp;7 die Mitgliedschaft/Nicht-Mitgliedschaft angeben)",
    )

    takes_part_in_mv = forms.BooleanField(
        label="Ich nehme an der MV teil.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
        help_text="(Kostenfrei; nur für VFLL-Mitglieder)",
    )

    having_lunch = forms.BooleanField(
        label="Ich möchte am anschließenden Mittagsimbiss teilnehmen.",
        # widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
        help_text="(Kostenfrei; nur für MV-Teilnehmende)",
    )

    networking = forms.BooleanField(
        label="Netzwerkabend im Tagungshaus BBZ am Freitag, 27.09.2024, ab 19 Uhr<br>(Kosten inkl. Buffet: 20 €**, Getränke: Selbstzahlung vor Ort)",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    yoga = forms.BooleanField(
        label="Führung im Haus der Wannsee-Konferenz am Freitag, 27.09.2024, ab 15:00 Uhr<br/>(Kosten: Eintritt frei, Spenden erwünscht, Treffpunkt BBZ Anmeldebereich)",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    celebration = forms.BooleanField(
        label="Festabend mit Tanz im Tagungshaus BBZ am Samstag, 28.09.2024, ab 19 Uhr<br>(Kosten inkl. Buffet: 25 €**, Getränke: Selbstzahlung vor Ort)",
        widget=forms.CheckboxInput(
            attrs={"class": "form-radio", "style": "white-space: pre-wrap;"}
        ),
        required=False,
    )

    ideas = forms.BooleanField(
        label="Erfahrungsaustausch und Ideenschmiede mit der AG Sprachwandel: <i>Menschenwürde schützen im Lektorat</i> am Freitag, 27.09.2024, ab 16:30 Uhr<br>(Kostenfrei; Treffpunkt BBZ Anmeldebereich)",
        widget=forms.CheckboxInput(
            attrs={"class": "form-radio", "style": "white-space: pre-wrap;"}
        ),
        required=False,
    )

    # Zimmerbuchung
    booking27 = forms.ChoiceField(
        widget=forms.RadioSelect,
        label="Für 27.09.&ndash;28.09. buche ich:",
        choices=BOOKING_CHOICES_27,
        required=False,
        initial="",
    )
    booking28 = forms.ChoiceField(
        widget=forms.RadioSelect,
        label="Für 28.09.&ndash;29.09. buche ich:",
        choices=BOOKING_CHOICES_28,
        required=False,
        initial="",
    )

    food_preferences = forms.ChoiceField(
        widget=forms.RadioSelect,
        label="Ich möchte:",
        choices=FOOD_PREFERENCE_CHOICES,
        required=False,
    )

    food_remarks = forms.CharField(
        label="Andere wichtige Informationen (Allergien, Unverträglichkeiten etc.):",
        widget=forms.Textarea(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
    )

    remarks = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
    )

    memberships_full = forms.MultipleChoiceField(
        label="Ich bin Mitglied folgender Organisation(en):",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "text-xs  text-gray-600"}),
        choices=MEMBERSHIP_CHOICES_24_FULL,
        required=False,
    )

    nomember = forms.BooleanField(
        label="Ich bin nicht Mitglied einer dieser Organisationen.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.event_label = kwargs.pop("event_label", "")
        super(Symposium2024Form, self).__init__(*args, **kwargs)
        # print("ws in form:", self.ws_utilisations)

        self.helper = FormHelper()
        # self.helper.form_class = "form-horizontal"
        self.helper.form_error_title = "Fehler im Formular"
        self.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                "1. Anmeldedaten",
                Row(
                    Column("firstname", css_class="form-group col-md-6 mb-0"),
                    Column("lastname", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                # "firstname",
                # "lastname",
                "address_line",
                "street",
                Row(
                    Column("postcode", css_class="form-group col-md-2 mb-0"),
                    Column("city", css_class="form-group col-md-10 mb-0"),
                    css_class="form-row",
                ),
                HTML(
                    """
                    <p class='mb-2'>Für die steuerliche Abzugsfähigkeit bitte Geschäftsadresse angeben!</p>
                    """
                ),
                "email",
                "phone",
                HTML(
                    """
                    <p class='mb-2'>Ich bin damit einverstanden, dass meine Kontakt- und Anmeldedaten zur Durchführung der Anmeldung verarbeitet werden und vor Ort auf nicht frei 
                    zugänglichen Anmeldelisten aufgeführt sind. 
                    Weiterhin bin ich damit einverstanden, dass ausschließlich mein Vor- und Nachname mit Wohnort auf einer eventuell vor Ort aushängenden 
                    Teilnahmeliste aufgeführt ist.</p>
                    <p><span class='font-bold'>Datenschutzhinweis:</span> Wir verwenden Ihre Angaben ausschließlich zur Durchführung der Veranstaltungen des Verbands der freien Lektorinnen und Lektoren e. V. Ihre Daten werden nicht an unbefugte Dritte weitergegeben. Verantwortlich im Sinne der DSGVO ist der Vorstand des Verbands der Freien Lektorinnen und Lektoren e. V., Geschäftsstelle, Büro Seehausen + Sandberg, Merseburger Straße 5, 10823 Berlin.</p>
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "2. Fachtagung am Samstag, 28.09.2024 ",
                CustomCheckbox("takes_part_in_ft"),
                HTML(
                    """
                    <p class='ml-4'>Auf dieser Veranstaltung werden Fotos, ggf. Film- und Tonaufnahmen der Teilnehmenden gemacht. 
                    Ausgewählte Aufnahmen können in den digitalen und den gedruckten Medien des Verbands 
                    veröffentlicht werden (z.&nbsp;B. Website, Facebook, X, Leitfaden Freies Lektorat, Broschüre „Gemeinsam für Textqualität“). 
                    <br/>Mit deren Verwendung bin ich einverstanden.</p>
                    """
                ),
                css_class="mt-4",
            ),
            Fieldset(
                "3. Mitgliederversammlung (MV) am Sonntag, 29.09.2024",
                CustomCheckbox(
                    "takes_part_in_mv",
                ),
                CustomCheckbox("having_lunch"),
                HTML(
                    """
                    <p class='ml-4'>Auf dieser Veranstaltung werden Fotos, ggf. Film- und Tonaufnahmen der Teilnehmenden gemacht. 
                    Ausgewählte Aufnahmen können in den digitalen und den gedruckten Medien des Verbands 
                    veröffentlicht werden (z.&nbsp;B. Website, Facebook, X, Leitfaden Freies Lektorat, Broschüre „Gemeinsam für Textqualität“). 
                    <br/>Mit deren Verwendung bin ich einverstanden.</p>
                    """
                ),
                css_class="mt-4",
            ),
            Fieldset(
                "4. Rahmenprogramm",
                HTML(
                    """
                    <p class='mb-2'>An den folgenden Rahmenprogrammpunkten nehme ich teil:</p>
                    """
                ),
                CustomCheckbox("yoga"),
                CustomCheckbox("ideas"),
                CustomCheckbox("networking"),
                CustomCheckbox("celebration"),
                css_class="mt-4",
            ),
            Fieldset(
                "5. Zimmerbuchung",
                HTML(
                    """
                    <p class='mb-2'>Die Übernachtungen im Tagungshaus BBZ sind hier verbindlich zu buchen 
                    (alle Preise inkl. MwSt.). Die Bestätigung und Rechnungsabwicklung erfolgt nach Anmeldeschluss durch das BBZ, 
                    die Übernachtungskosten sind somit nicht mit dem Tagungsbeitrag zu überweisen.</p>

                    """
                ),
                "booking27",
                "booking28",
                HTML(
                    """
                    <p>Bis zum 18.08.2024 kann diese Buchung kostenfrei storniert werden. Zu den weiteren Stornobedingungen s. Punkt 8. </p>
                    <p>Alternative Unterkünfte (s. Einladung) sind bitte in Eigenregie zu buchen.</p>

                    """
                ),
                css_class="mt-4",
            ),
            Fieldset(
                "6. Essenswünsche",
                # InlineCheckboxes(
                #    "food_preferences",
                #    required=False,
                # ),
                HTML(
                    """
                <p class='mb-2'>Bitte gebt hier eure Wünsche für die Mahlzeiten im BBZ an.</p>
                    """
                ),
                "food_preferences",
                "food_remarks",
                css_class="mt-4",
            ),
            Fieldset(
                "7. Teilnahmekosten",
                HTML(
                    """
                    <p>Der Tagungsbeitrag für die Fachtagung beträgt:
                    <ul style='list-style-position: outside; padding-left: 20px;'>
                    <li>140 € für Mitglieder des VFLL oder einiger Partnerverbände (bitte nachfolgend die Mitgliedschaft angeben)</li>
                    <li>190 € für sonstige Teilnehmende (bitte nachfolgend die Nicht-Mitgliedschaft angeben)</li>
                    </ul>
                    </p>
                    <p class='mt-2 mb-2'>
                    Darin enthalten sind die Kosten für die Fachtagung inklusive Mittagessen und Pausenverpflegung am Samstag. 
                    <b>Nicht enthalten</b> sind Rahmenprogramm, Netzwerkabend und Festabend, Unterkunft, Anreise.</p>
                    <p>Die Teilnahme an der MV ist kostenfrei.</p>
                    """
                ),
                css_class="mt-4",
            ),
            Fieldset(
                "Mitgliedschaft",
                "memberships_full",
                CustomCheckbox("nomember"),
                css_class="mt-4",
            ),
            Fieldset(
                "8. Zahlung, Rechnung, Stornierungsmodalitäten",
                HTML(
                    """
                    <p>Den Gesamtbetrag aus Tagungsbeitrag und ggf. den Kostenbeiträgen
                    für weitere von mir gewählte Angebote (**) überweise ich umgehend, <b>spätestens bis 18.08.2024</b> (erfolgter Zahlungseingang), an</br>
                    VFLL e. V., IBAN: DE24 4306 0967 6032 5237 00,<br/>
                    BIC: GENODEM1GLS – Stichwort: FFL 2024
                    </p>
                    <p class='mt-2 mb-2'>
                    Die Rechnungen werden mit dem Vermerk <i>Zahlung erhalten</i> im Anschluss an die Tagung verschickt.


                    </p>
                    <p class="mb-2">
                    <hr>
                    </p>
                    <p class="mt-2" style="border:top;">
                    <b>Für den Fall einer Absage bitte beachten:</b>
                    <ul style='list-style-position: outside; padding-left: 20px;'>
                    <li>Absagen bis 18.08.2024: Bearbeitungsgebühr 10 €.</li>
                    <li>Absagen 19.08.–30.08.2024: 80 % der gezahlten Beträge für die Tagung und das Rahmenprogramm werden rückerstattet (abzgl. 10 € Bearbeitungsgebühr).</li>
                    <li>Absagen ab 31.08.2024: 50 % der gezahlten Beträge für die Tagung und das Rahmenprogramm werden rückerstattet (abzgl. 10 € Bearbeitungsgebühr).</li>
                    </ul>
                    </p>
                    """
                ),
                css_class="mt-4",
            ),
            Fieldset(
                "Anmerkungen und Wünsche:",
                "remarks",
                css_class="mt-4",
            ),
            ButtonHolder(
                Submit(
                    "submit",
                    "Ich melde mich hiermit verbindlich an.",
                    css_class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-full",
                )
            ),
        )
        # self.helper.add_input(Submit("submit", "Anmelden"))

    def clean(self):
        cleaned_data = super().clean()
        takes_part_in_mv = cleaned_data.get("takes_part_in_mv")
        takes_part_in_ft = cleaned_data.get("takes_part_in_ft")
        having_lunch = cleaned_data.get("having_lunch")
        networking = cleaned_data.get("networking")
        ideas = cleaned_data.get("ideas")
        yoga = cleaned_data.get("yoga")
        celebration = cleaned_data.get("celebration")
        food_preferences = cleaned_data.get("food_preferences")
        booking27 = cleaned_data.get("booking27")
        booking28 = cleaned_data.get("booking28")
        remarks = cleaned_data.get("remarks")
        food_remarks = cleaned_data.get("food_remarks")
        memberships_full = cleaned_data.get("memberships_full")

        if not takes_part_in_mv and not takes_part_in_ft and not celebration:
            raise forms.ValidationError(
                "Bitte mind. eine der beiden Teilnahmen (FT oder MV) anklicken. Oder willst du nur am Festabend teilnehmen? Dann bitte anklicken."
            )

        if (booking27 or booking28) and not (takes_part_in_ft or takes_part_in_mv):
            raise forms.ValidationError(
                "Du hast eine Übernachtung gewählt, nimmst aber weder an der FT noch an der MV teil. Bitte korrigieren."
            )

        return cleaned_data

    # def clean_takes_part_in_ft(self):
    #     takes_part_in_ft = self.cleaned_data.get("takes_part_in_ft")
    #     ws2022 = self.cleaned_data.get("ws2022")
    #     if not takes_part_in_ft and ws2022 != "":
    #         self.add_error(
    #             "takes_part_in_ft",
    #             "Bitte dieses Feld anklicken, wenn Sie an der Fachtagung teilnehmen.",
    #         )
    #     return takes_part_in_ft

    def clean_having_lunch(self):
        having_lunch = self.cleaned_data["having_lunch"]
        takes_part_in_mv = self.cleaned_data["takes_part_in_mv"]
        if having_lunch and not takes_part_in_mv:
            self.add_error(
                None,
                "Du hast dich für das Mittagessen am Sonntag, aber nicht für die MV angemeldet. Bitte korrigieren.",
            )
        # raise forms.ValidationError(
        #     "Du hast dich für das Mittagessen am Sonntag, aber nicht für die MV angemeldet, bitte korrigieren."
        # )
        return having_lunch

    def clean_email(self):
        email = self.cleaned_data["email"]
        if (
            EventMember.objects.filter(
                email=email, event__label=self.event_label
            ).count()
            > 0
        ):
            self.add_error(
                None,
                "Es gibt bereits eine Anmeldung mit dieser E-Mail-Adresse.",
            )
        return email

    def clean_memberships_full(self):
        memberships_full = self.cleaned_data.get("memberships_full")
        if memberships_full and "vv" in memberships_full and "vk" in memberships_full:
            self.add_error(
                None,
                "Bitte nur eine der beiden VFLL-Mitgliedsvarianten ankreuzen",
            )
            # raise forms.ValidationError(
            #     "Bitte nur eine der beiden VFLL-Mitgliedsvarianten ankreuzen"
            # )
        return memberships_full

    def clean_nomember(self):
        nomember = self.cleaned_data.get("nomember")
        if nomember and len(self.cleaned_data.get("memberships_full")) > 0:
            self.add_error(
                None,
                "Wenn Mitgliedschaft in einem der Partnerverbände oder dem VFLL vorhanden, bitte 'Ich bin nicht Mitglied...' NICHT anklicken.",
            )

        if not nomember and len(self.cleaned_data.get("memberships_full")) == 0:
            self.add_error(
                None,
                "Wenn keine Mitgliedschaft in einem der Partnerverbände oder dem VFLL vorhanden, bitte 'Ich bin nicht Mitglied...' bestätigen.",
            )

        return nomember


############## form for edit json data of member (FT 2022) ######


# ref: https://github.com/jrief/django-entangled
class FTEventMemberForm(EntangledModelForm):
    YES_NO_CHOICES = (("ja", "ja"), ("nein", "nein"))
    firstname = forms.CharField(label="Vorname")
    lastname = forms.CharField(label="Nachname")
    email = forms.EmailField(label="Email")
    address_line = forms.CharField(label="Adresszusatz", required=False)
    street = forms.CharField(label="Straße", required=False)
    postcode = forms.CharField(label="PLZ", required=False)
    city = forms.CharField(label="Stadt", required=False)
    ws2022 = forms.CharField(label="WS", required=False)
    ws_alter = forms.CharField(label="WS Altern.", required=False)
    takes_part_in_mv = forms.ChoiceField(label="Teilnahme MV", choices=YES_NO_CHOICES)
    having_lunch = forms.ChoiceField(label="Mittagessen", choices=YES_NO_CHOICES)
    tour = forms.CharField(label="Führung", required=False)
    networking = forms.ChoiceField(label="Teilnahme Networking", choices=YES_NO_CHOICES)
    yoga = forms.ChoiceField(label="Teilnahme Yoga", choices=YES_NO_CHOICES)
    celebration = forms.ChoiceField(label="Teilnahme Feier", choices=YES_NO_CHOICES)
    food_preferences = forms.CharField(label="Essenswünsche", required=False)
    remark = forms.CharField(label="Bemerkungen", required=False)

    class Meta:
        model = EventMember
        entangled_fields = {
            "data": [
                "firstname",
                "lastname",
                "email",
                "address_line",
                "street",
                "postcode",
                "city",
                "ws2022",
                "ws_alter",
                "takes_part_in_mv",
                "having_lunch",
                "tour",
                "networking",
                "yoga",
                "celebration",
                "food_preferences",
                "remark",
            ]
        }  # fields provided by this form


class FT24EventMemberForm(EntangledModelForm):

    # def __init__(self, *args, **kwargs):
    #     # Pop the 'instance' kwarg to access the Member instance
    #     instance = kwargs.pop("instance", None)
    #     super(FT24EventMemberForm, self).__init__(*args, **kwargs)

    #     if instance and instance.data:
    #         for key, value in instance.data.items():
    #             self.fields[key] = forms.CharField(initial=value, required=False)

    class Meta:
        model = EventMember
        # entangled_fields = {
        #     "data": [
        #         "takes_part_in_mv",
        #         "takes_part_in_ft",
        #         "having_lunch",
        #         "networking",
        #         "yoga",
        #         "ideas",
        #         "celebration",
        #         "food_preferences",
        #         "food_remarks",
        #         "booking27",
        #         "booking28",
        #         "memberships_full",
        #         "nomember",
        #         "remarks",
        #     ]
        # }  # fields provided by this form
        # untangled_fields = [
        fields = [
            "lastname",
            "firstname",
            "email",
            "address_line",
            "street",
            "postcode",
            "city",
        ]  # these fields are provided by the Product model

    def __init__(self, *args, **kwargs):
        # Pop the 'instance' kwarg to access the Member instance
        super(FT24EventMemberForm, self).__init__(*args, **kwargs)
        instance = kwargs.pop("instance", None)
        data = instance.data
        self.fields["takes_part_in_mv"] = forms.BooleanField(
            required=False, initial=data["takes_part_in_mv"]
        )
        self.fields["takes_part_in_ft"] = forms.BooleanField(
            required=False, initial=data["takes_part_in_ft"]
        )
        self.fields["having_lunch"] = forms.BooleanField(
            required=False, initial=data["having_lunch"]
        )
        self.fields["networking"] = forms.BooleanField(
            required=False, initial=data["networking"]
        )
        self.fields["yoga"] = forms.BooleanField(required=False, initial=data["yoga"])
        self.fields["ideas"] = forms.BooleanField(required=False)
        self.fields["celebration"] = forms.BooleanField(required=False)
        self.fields["food_preferences"] = forms.ChoiceField(
            choices=FOOD_PREFERENCE_CHOICES, required=False
        )
        self.fields["food_remarks"] = forms.CharField(
            widget=forms.Textarea, required=False
        )
        self.fields["booking27"] = forms.ChoiceField(
            choices=BOOKING_CHOICES_27, required=False
        )
        self.fields["booking28"] = forms.ChoiceField(
            choices=BOOKING_CHOICES_28, required=False
        )
        self.fields["memberships_full"] = forms.MultipleChoiceField(
            choices=MEMBERSHIP_CHOICES_24_FULL
        )
        self.fields["nomember"] = forms.BooleanField(required=False)
        self.fields["remarks"] = forms.CharField(widget=forms.Textarea, required=False)


class DateRangeForm(forms.Form):
    start = forms.DateField(
        required=False,
        label="von (Datum)",
        widget=AdminDateWidget,
    )
    until = forms.DateField(
        required=False,
        label="bis (Datum)",
        widget=AdminDateWidget,
    )

    def clean(self):
        start = self.cleaned_data.get("start")
        until = self.cleaned_data.get("until")

        if start and until and start >= until:
            self.add_error("start", "Von-Datum muss vor dem Bis-Datum liegen")


class Symposium2022Form(forms.Form):
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
    address_line = forms.CharField(
        label="Adresszusatz",
        widget=forms.TextInput(attrs={"placeholder": "Adresszusatz"}),
        required=False,
    )
    street = forms.CharField(
        label="Straße, Hausnummer",
        widget=forms.TextInput(attrs={"placeholder": "Straße, Hausnummer"}),
    )
    postcode = forms.CharField(
        label="PLZ", widget=forms.TextInput(attrs={"placeholder": "PLZ"})
    )
    city = forms.CharField(
        label="Ort", widget=forms.TextInput(attrs={"placeholder": "Ort"})
    )
    email = forms.EmailField(
        label="E-Mail",
        widget=forms.TextInput(attrs={"placeholder": "E-Mail"}),
    )
    phone = forms.CharField(
        label="Telefonnummer",
        widget=forms.TextInput(attrs={"placeholder": "Telefonnummer"}),
        required=False,
    )
    ws2022 = forms.ChoiceField(
        widget=MyRadioSelect(),
        label="Workshop",
        choices=WS2022_CHOICES,
        required=False,
    )

    ws_alter = forms.CharField(
        label="Für den Fall, dass meine Wahl ausgebucht ist, wähle ich alternativ Workshop Nr.:",
        widget=forms.TextInput(attrs={"placeholder": "I, ..., VI", "class": "w-1/3"}),
        required=False,
    )

    takes_part_in_ft = forms.BooleanField(
        label="Ich nehme an der Fachtagung teil.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    takes_part_in_mv = forms.BooleanField(
        label="Ich nehme an der MV teil.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    having_lunch = forms.BooleanField(
        label="Ich möchte am anschließenden Mittagessen teilnehmen.",
        # widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    tour = forms.ChoiceField(
        # attrs={"class": "text-xs  text-gray-600"},
        widget=forms.RadioSelect,
        label="Ich nehme am Fr., 16.09.2022, ab 15:30 Uhr teil an folgender Führung:",
        choices=TOUR_CHOICES,
        required=False,
    )

    networking = forms.BooleanField(
        label="Netzwerkabend im Tagungshaus BBZ am Freitag, 27.09.2024, ab 19 Uhr<br>(Kosten inkl. Buffet: 20 €**, Getränke: Selbstzahlung vor Ort)",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    yoga = forms.BooleanField(
        label="Führung im Haus der Wannsee-Konferenz am Freitag, 27.09.2024, ab 15:00 Uhr<br/>(Kosten: Eintritt frei, Spenden erwünscht, Treffpunkt BBZ Anmeldebereich)",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    celebration = forms.BooleanField(
        label="Festabend mit Tanz im Tagungshaus BBZ am Samstag, 28.09.2024, ab 19 Uhr<br>(Kosten inkl. Abendessen: 25 €**, Getränke: Selbstzahlung vor Ort)",
        widget=forms.CheckboxInput(
            attrs={"class": "form-radio", "style": "white-space: pre-wrap;"}
        ),
        required=False,
    )

    # Zimmerbuchung
    booking = forms.ChoiceField(
        widget=forms.RadioSelect,
        label="Die Übernachtungen im Tagungshaus BBZ sind hier verbindlich zu buchen (alle Preise inkl. MwSt.). ",
        choices=FOOD_PREFERENCE_CHOICES,
        required=False,
    )

    food_preferences = forms.ChoiceField(
        widget=forms.RadioSelect,
        label="Ich möchte",
        choices=FOOD_PREFERENCE_CHOICES,
        required=False,
    )

    remarks = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "class": "block w-full p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner"
            }
        ),
        required=False,
    )

    memberships = forms.MultipleChoiceField(
        label="Ich bin Mitglied folgender Organisation(en):",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "text-xs  text-gray-600"}),
        choices=MEMBERSHIP_CHOICES,
        required=False,
    )

    nomember = forms.BooleanField(
        label="Ich bin nicht Mitglied einer dieser Organisationen.",
        widget=forms.CheckboxInput(attrs={"class": "form-radio"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.event_label = kwargs.pop("event_label", "")
        self.ws_utilisations = kwargs.pop("ws_utilisations", "{}")
        self.tour_utilisations = kwargs.pop("tour_utilisations", "{}")
        super(Symposium2022Form, self).__init__(*args, **kwargs)
        # print("ws in form:", self.ws_utilisations)
        if self.ws_utilisations:
            ws_choices = ()
            ws_full = []
            for choice in WS2022_CHOICES:
                if choice[0] == "-":
                    ws_choices = ws_choices + (choice,)
                elif self.ws_utilisations[choice[0]] > 0:
                    ws_choices = ws_choices + (choice,)
                elif self.ws_utilisations[choice[0]] <= 0:
                    ws_full.append(choice[0])
            if len(ws_full) > 0:
                help_text = (
                    "Workshop(s) "
                    + ", ".join(ws_full)
                    + " ist/sind bereits ausgebucht."
                )
            else:
                help_text = ""
            self.fields["ws2022"] = forms.ChoiceField(
                widget=MyRadioSelect(ws_utilisations=self.ws_utilisations),
                label="Workshop",
                # help_text="Bereits ausgebuchte Workshops werden nicht angezeigt.",
                help_text=help_text,
                choices=ws_choices,
                required=False,
            )
        if self.tour_utilisations:
            tour_choices = ()
            tour_full = []
            for choice in TOUR_CHOICES:
                if choice[0] == "-":
                    tour_choices = tour_choices + (choice,)
                elif self.tour_utilisations[choice[0]] > 0:
                    tour_choices = tour_choices + (choice,)
                elif self.tour_utilisations[choice[0]] <= 0:
                    tour_full.append(choice[0])
            if len(tour_full) > 0:
                help_text_tour = (
                    "Führung(en) "
                    + ", ".join(tour_full)
                    + " ist/sind bereits ausgebucht."
                )
            else:
                help_text_tour = ""
            self.fields["tour"] = forms.ChoiceField(
                widget=MyRadioSelect(tour_utilisations=self.tour_utilisations),
                label="Ich nehme am Fr., 16.09.2022, ab 15:30 Uhr teil an folgender Führung:",
                # help_text="Bereits ausgebuchte Workshops werden nicht angezeigt.",
                help_text=help_text_tour,
                choices=tour_choices,
                required=False,
            )
        self.helper = FormHelper()
        # self.helper.form_class = "form-horizontal"
        self.helper.form_error_title = "Fehler im Formular"
        self.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                "1. Anmeldedaten",
                Row(
                    Column("firstname", css_class="form-group col-md-6 mb-0"),
                    Column("lastname", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                # "firstname",
                # "lastname",
                "address_line",
                "street",
                Row(
                    Column("postcode", css_class="form-group col-md-2 mb-0"),
                    Column("city", css_class="form-group col-md-10 mb-0"),
                    css_class="form-row",
                ),
                HTML(
                    """
                    <p class='mb-2'>Für die steuerliche Abzugsfähigkeit bitte Geschäftsadresse angeben!</p>
                    """
                ),
                "email",
                "phone",
                HTML(
                    """
                    <p class='mb-2'>Ich bin damit einverstanden, dass meine Kontaktdaten (Vor- und Nachname, Telefon, E-Mail-Adresse) auf der Teilnahmeliste stehen und an die anderen Teilnehmenden weitergegeben werden.</p>
                    """
                ),
                css_class="border-b-2 border-gray-900 pb-2 mb-4",
            ),
            Fieldset(
                "2. Teilnahme an einem Workshop am Sa., 17.09.2022",
                # CustomCheckbox("takes_part_in_ft"),
                "ws2022",
                "ws_alter",
            ),
            Fieldset(
                "2. Mitgliederversammlung (MV) am So., 18.09.2022",
                CustomCheckbox(
                    "takes_part_in_mv",
                ),
                CustomCheckbox("having_lunch"),
                HTML(
                    """
                    <p class='mb-2'>(für VFLL-Mitglieder kostenfrei)</p>
                    """
                ),
                "food_preferences",
            ),
            Fieldset(
                "4. Rahmenprogramm",
                "tour",
                CustomCheckbox("networking"),
                CustomCheckbox("yoga"),
                CustomCheckbox("celebration"),
            ),
            Fieldset(
                "5. Zimmerbuchung",
                CustomCheckbox("networking"),
                CustomCheckbox("yoga"),
                CustomCheckbox("celebration"),
            ),
            Fieldset(
                "5. Essenswünsche",
                # InlineCheckboxes(
                #    "food_preferences",
                #    required=False,
                # ),
                "food_preferences",
            ),
            Fieldset(
                "6. Teilnahmekosten",
                HTML(
                    """
                    <p>Der Tagungsbeitrag für die Fachtagung beträgt
                    <ul style='list-style-position: outside; padding-left: 20px;'>
                    <li>130 € für Mitglieder des VFLL oder eines der u. g. Partnerverbände</li>
                    <li>180 € für sonstige Fachbesucher*innen</li>
                    </ul>
                    </p>
                    <p class='mt-2 mb-2'>
                    Darin enthalten sind die Kosten für die Fachtagung (hinzu kommen ggf.
                    gewählte Punkte des Rahmenprogramms, Übernachtungen u. Ä.).
                    </p>
                    """
                ),
            ),
            Fieldset(
                "Mitgliedschaft",
                "memberships",
                CustomCheckbox("nomember"),
            ),
            Fieldset(
                "7. Zahlung, Stornierungsmodalitäten",
                HTML(
                    """
                    <p>Den Gesamtbetrag aus Tagungsbeitrag und ggf. den Kostenbeiträgen
                    für weitere von mir gewählte Angebote (**) habe ich überwiesen an:</br>
                    VFLL e. V., IBAN: DE24 4306 0967 6032 5237 00,<br/>
                    BIC: GENODEM1GLS – Stichwort: FFL 2022
                    </p>
                    <p class="mb-2">
                    <hr>
                    </p>
                    <p class="mt-2" style="border:top;">
                    <b>Für den Fall einer Absage bitte beachten:</b>
                    <ul style='list-style-position: outside; padding-left: 20px;'>
                    <li>Bei Absagen bis Fr., 29.07.2022, wird eine Bearbeitungsgebühr in Höhe
                    von 20&nbsp;Euro erhoben.</li>
                    <li>Bei Absagen bis Fr., 19.08.2022, werden 50 % der gezahlten Beträge für die
                    Tagung und das Rahmenprogramm rückerstattet.</li>
                    <li>Bei Absagen ab Sa., 20.08.2022, ist eine Erstattung der gezahlten Beträge
                    leider nicht mehr möglich.</li>
                    </ul>
                    </p>
                    <p class='mt-2 mb-2'>
                    Bitte bucht eure Hotelübernachtungen selbst und beachtet im Fall einer
                    Absage die dortigen Stornierungsbedingungen.
                    </p>
                    """
                ),
            ),
            Fieldset(
                "Anmerkungen und Wünsche:",
                "remarks",
            ),
            ButtonHolder(
                Submit(
                    "submit",
                    "Ich melde mich hiermit verbindlich an.",
                    css_class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-full",
                )
            ),
        )
        # self.helper.add_input(Submit("submit", "Anmelden"))

    def clean(self):
        cleaned_data = super().clean()
        takes_part_in_mv = cleaned_data.get("takes_part_in_mv")
        having_lunch = cleaned_data.get("having_lunch")
        tour = cleaned_data.get("tour")
        networking = cleaned_data.get("networking")
        yoga = cleaned_data.get("yoga")
        celebration = cleaned_data.get("celebration")
        food_preferences = cleaned_data.get("food_preferences")
        remarks = cleaned_data.get("remarks")
        memberships = cleaned_data.get("memberships")

    def clean_ws2022(self):
        ws2022 = self.cleaned_data.get("ws2022")
        if (
            ws2022 in ["I", "II", "III", "IV", "V", "VI"]
            and self.ws_utilisations[ws2022] <= 0
        ):
            self.add_error("ws2022", "Dieser Workshop ist bereits ausgebucht")
        return ws2022

    def clean_ws_alter(self):
        ws_alter = self.cleaned_data.get("ws_alter")
        if ws_alter.strip() not in ["I", "II", "III", "IV", "V", "VI", ""]:
            self.add_error("ws_alter", "Bitte I bis VI eintragen oder leer lassen")
        if (
            ws_alter.strip() in ["I", "II", "III", "IV", "V", "VI"]
            and self.ws_utilisations[ws_alter.strip()] <= 0
        ):
            self.add_error("ws_alter", "Dieser Workshop ist bereits ausgebucht.")
        return ws_alter

    # def clean_takes_part_in_ft(self):
    #     takes_part_in_ft = self.cleaned_data.get("takes_part_in_ft")
    #     ws2022 = self.cleaned_data.get("ws2022")
    #     if not takes_part_in_ft and ws2022 != "":
    #         self.add_error(
    #             "takes_part_in_ft",
    #             "Bitte dieses Feld anklicken, wenn Sie an der Fachtagung teilnehmen.",
    #         )
    #     return takes_part_in_ft

    def clean_email(self):
        email = self.cleaned_data["email"]
        if (
            EventMember.objects.filter(
                email=email, event__label=self.event_label
            ).count()
            > 0
        ):
            raise forms.ValidationError(
                "Es gibt bereits eine Anmeldung mit dieser E-Mail-Adresse."
            )
        return email

    # def clean_nomember(self):
    #     nomember = self.cleaned_data.get("nomember")
    #     if nomember and len(self.cleaned_data.get("memberships")) > 0:
    #         self.add_error(
    #             "memberships",
    #             "Wenn Mitgliedschaft vorhanden, bitte 'Ich bin nicht Mitglied...' nicht anklicken.",
    #         )

    #     if not nomember and len(self.cleaned_data.get("memberships")) == 0:
    #         self.add_error(
    #             "memberships",
    #             "Wenn keine Mitgliedschaft, bitte 'Ich bin nicht Mitglied...' anklicken.",
    #         )

    #     return nomember
