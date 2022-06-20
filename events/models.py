from django.db import models
from django.db.models import F
from datetime import datetime
from datetime import date
from django.db.models.fields import related
from django.utils import timezone
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError
from django.template.defaultfilters import truncatechars
from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.fields import RichTextField

from embed_video.fields import EmbedVideoField

from .abstract import BaseModel, AddressModel

from .choices import PUB_STATUS_CHOICES, REGIO_GROUP_CHOICES

from events.utils import find_duplicates_in_list


class Home(BaseModel):
    """
    Model for start page title and text
    Only one record is allowed
    Restriction ist made in ModelAdmin
    """

    name = models.CharField("Name", max_length=40)
    title = models.CharField("Titel", max_length=255, null=True, blank=True)
    text = models.TextField("Haupttext", blank=True)

    class Meta:
        verbose_name = "Home"
        verbose_name_plural = "Home"

    def __str__(self):
        return self.name


class EventCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField("Beschreibung", blank=True)
    singular = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="wird im Frontend als Kategorie angezeigt",
    )
    position = models.PositiveSmallIntegerField(default=1)
    show = models.BooleanField(
        default=True,
        help_text="gibt an, ob die Kachel auf der Startseite grundsätzlich gezeigt werden soll. Es werden aber nur die Kacheln angezeigt, zu denen auch eine Veranstaltung besteht.",
    )

    class Meta:
        ordering = ("position",)
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"

    def __str__(self):
        if self.title:
            return self.title
        return self.name

    def get_absolute_url(self):
        return reverse("event-category-list")


class EventFormat(BaseModel):
    name = models.CharField(verbose_name="Format", max_length=255, unique=True)
    description = models.TextField("Beschreibung", blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Format"
        verbose_name_plural = "Formate"

    def __str__(self):
        return self.name


class EventLocation(AddressModel):
    title = models.CharField("Name", max_length=128)
    url = models.URLField(
        verbose_name="Veranstaltungsort Website",
        blank=True,
    )

    class Meta:
        verbose_name = "Veranstaltungsort"
        verbose_name_plural = "Veranstaltungsorte"

    def __str__(self):
        return self.title

    def get_complete_address(self):
        address = ""
        if self.address_line:
            address += self.address_line
        if self.street:
            if address:
                address += "\n" + self.street
            else:
                address += self.street
        if self.city:
            if address:
                address += (
                    "\n" + (self.postcode + " " if self.postcode else "") + self.city
                )
            else:
                address += self.city
        if self.state:
            if address:
                address += ", " + self.state
            else:
                address += self.state

        if self.url:
            if address:
                address += "\n" + self.url
            else:
                address += self.url

        return address


class EventOrganizer(BaseModel):
    name = models.CharField(max_length=255)
    contact = models.CharField(
        verbose_name="Kontakt", max_length=255, blank=True, null=True
    )
    url = models.URLField(verbose_name="Veranstalter Website", blank=True)

    def __str__(self):
        return self.name


class EventSpeaker(BaseModel):
    first_name = models.CharField("Vorname", blank=True, max_length=128)
    last_name = models.CharField("Nachname", max_length=128)
    email = models.EmailField("E-Mail", blank=True, max_length=255)
    phone = models.CharField("Tel", max_length=64, blank=True)
    bio = models.TextField("Biografie", blank=True)
    url = models.URLField("Website", blank=True)
    social_url = models.URLField("Soziale Medien", blank=True)
    image = models.ImageField(upload_to="speaker/", blank=True)

    class Meta:
        ordering = ("last_name",)
        verbose_name = "Dozent*in"
        verbose_name_plural = "Dozent*innen"

    def __str__(self):
        return "{first_name} {last_name} ({email})".format(
            first_name=self.first_name, last_name=self.last_name, email=self.email
        ).strip()

    @property
    def full_name(self):
        return "{first_name} {last_name}".format(
            first_name=self.first_name, last_name=self.last_name
        ).strip()


class EventSponsor(BaseModel):
    first_name = models.CharField("Vorname", blank=True, max_length=128)
    last_name = models.CharField("Nachname", max_length=128)
    email = models.EmailField("E-Mail", blank=True, max_length=255)
    phone = models.CharField("Tel", max_length=64, blank=True)
    url = models.URLField("Website", blank=True)
    image = models.ImageField(upload_to="speaker/", blank=True)

    class Meta:
        ordering = ("last_name",)
        verbose_name = "Pat*in"
        verbose_name_plural = "Pat*innen"

    def __str__(self):
        return "{first_name} {last_name} ({email})".format(
            first_name=self.first_name, last_name=self.last_name, email=self.email
        ).strip()

    @property
    def full_name(self):
        return "{first_name} {last_name}".format(
            first_name=self.first_name, last_name=self.last_name
        ).strip()


class Event(BaseModel):
    """Events"""

    category = models.ForeignKey(
        EventCategory,
        verbose_name="Kategorie",
        related_name="events",
        on_delete=models.CASCADE,
    )
    eventformat = models.ForeignKey(EventFormat, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, null=False, unique=True, editable=True)
    eventurl = models.URLField(null=True, blank=True)

    pub_status = models.CharField(
        max_length=8,
        choices=PUB_STATUS_CHOICES,
        default="PUB",
        verbose_name="Status Veröffentlichung",
        help_text=(
            "veröffentlicht: sichtbar und buchbar; "
            "draft: nicht sichtbar, nicht buchbar; "
            "archiviert: nicht sichtbar, nicht buchbar"
        ),
    )
    frontend_flag = models.BooleanField(
        verbose_name="im Frontend zeigen?", default=True
    )
    label = models.CharField(
        max_length=64,
        verbose_name="Kurzname",
        unique=True,
        help_text="eindeutiger Kurzname",
    )
    description = RichTextUploadingField(
        verbose_name="Teaser", blank=True, config_name="short"
    )
    duration = models.CharField(
        verbose_name="Dauer", max_length=255, null=True, blank=True
    )
    target_group = models.CharField(
        verbose_name="Zielgruppe",
        null=True,
        blank=True,
        max_length=255,
    )
    prerequisites = RichTextUploadingField(
        verbose_name="Voraussetzungen", null=True, blank=True, config_name="short"
    )
    objectives = RichTextUploadingField(
        verbose_name="Lernziele", null=True, blank=True, config_name="short"
    )

    speaker = models.ManyToManyField(
        EventSpeaker, verbose_name="Dozent*innen", through="EventSpeakerThrough"
    )
    sponsors = models.ManyToManyField(
        EventSponsor,
        verbose_name="Pate,Patin",
        through="EventSponsorThrough",
    )

    organizer = models.ForeignKey(
        EventOrganizer,
        verbose_name="Veranstalter",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="organizer_events",
    )

    regio_group = models.CharField(
        "Regionalgruppe",
        max_length=3,
        choices=REGIO_GROUP_CHOICES,
        default="KA",
    )
    # methods = models.CharField(
    #    verbose_name="Methoden", max_length=255, null=True, blank=True
    # )
    methods = RichTextField(
        verbose_name="Methoden", null=True, blank=True, config_name="short"
    )
    contribution = models.CharField(
        verbose_name="VFLL-Beteiligung", max_length=255, null=True, blank=True
    )

    SCHEDULED_STATUS_CHOICES = (
        ("yet to scheduled", "noch offen"),
        ("scheduled", "terminiert"),
    )
    scheduled_status = models.CharField(
        max_length=25, choices=SCHEDULED_STATUS_CHOICES, default="scheduled"
    )
    location = models.ForeignKey(
        EventLocation,
        verbose_name="Veranstaltungsort",
        null=True,
        on_delete=models.SET_NULL,
        related_name="location_events",
    )
    fees = RichTextField(verbose_name="Gebühren", config_name="short")
    catering = RichTextField(
        verbose_name="Verpflegung", null=True, blank=True, config_name="short"
    )
    lodging = RichTextField(
        verbose_name="Übernachtung", null=True, blank=True, config_name="short"
    )
    total_costs = RichTextField(
        verbose_name="Gesamtkosten", null=True, blank=True, config_name="short"
    )
    registration = RichTextField(
        verbose_name="Anmeldung", config_name="short", blank=True
    )

    registration_possible = models.BooleanField("Anmeldung möglich", default=True)

    REGISTRATION_FORM_CHOICES = (
        ("s", "Standard"),
        ("m", "MV/ZW"),
        ("f", "Fachtagung 2022/MV"),
    )

    registration_form = models.CharField(
        "Anmeldeformular",
        max_length=1,
        choices=REGISTRATION_FORM_CHOICES,
        default="s",
    )

    registration_recipient = models.EmailField(
        verbose_name="Anmelde-Email an",
        max_length=254,
        null=True,
        blank=True,
        help_text="an diese Adresse werden Anmeldungen geschickt",
    )
    notes = RichTextField(
        verbose_name="Hinweise", null=True, blank=True, config_name="short"
    )

    video = EmbedVideoField(null=True, blank=True)
    show_video = models.BooleanField(default=False)
    video_comment = models.TextField(null=True, blank=True)

    notes_internal = RichTextField(
        verbose_name="interne Hinweise", null=True, blank=True, config_name="short"
    )

    free_text_field_intro = RichTextField(
        verbose_name="Freitextfeld Intro", null=True, blank=True, config_name="short"
    )

    start_date = models.DateTimeField(
        verbose_name="Beginn",
        null=True,
        help_text="Datum: Picker verwenden oder in der Form tt.mm.jj; Zeit: hh:mm",
    )
    end_date = models.DateTimeField(
        verbose_name="Ende",
        null=True,
        help_text="Datum: Picker verwenden oder in der Form tt.mm.jj; Zeit: hh:mm",
    )
    open_date = models.DateTimeField(
        verbose_name="Anmeldefrist Beginn",
        null=True,
        auto_now_add=True,
    )
    close_date = models.DateTimeField(
        verbose_name="Anmeldefrist Ende", null=True, blank=True
    )
    first_day = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(verbose_name="Kapazität", default=15)
    STATUS_CHOICES = (
        ("active", "findet statt"),
        ("deleted", "verschoben"),
        ("cancel", "abgesagt"),
    )
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default="active")
    moodle_id = models.PositiveSmallIntegerField(default=0)
    moodle_course_created = models.BooleanField(default=False)

    MOODLE_COURSE_TYPE_CHOICES = (
        (3, "in Planung"),
        (4, "Fortbildungen"),
    )
    moodle_course_type = models.PositiveSmallIntegerField(
        verbose_name="Moodle Kurstyp", choices=MOODLE_COURSE_TYPE_CHOICES, default=4
    )
    moodle_new_user_flag = models.BooleanField(
        verbose_name="Autom. E-Mail an neue Moodle-User",
        default=False,
        help_text="Hier kann für den Kurs festgelegt werden, ob neue Moodle-User die automatische Begrüßungsmail bekommen (default=False).",
    )
    moodle_standard_password = models.CharField(
        max_length=24, verbose_name="Moodle Standard-Passwort", default="VfllMoodle123#"
    )
    students_number = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        ordering = ("start_date",)
        verbose_name = "Veranstaltung"
        verbose_name_plural = "Veranstaltungen"

    def __str__(self):
        return f"{self.name} ({self.first_day})"

    def clean(self):
        """
        die im Admin Bereich eingegebenen Daten werden geprüft:
        - start_date darf nicht in der Vergangenheit liegen
        - end_date muss nach dem start_date liegen
        - Nachfrage bei mehr als 14 Tagen Dauer
        -
        """
        # if not self.pk and self.close_date and self.close_date < timezone.now():
        #    raise ValidationError("Die Anmeldfrist liegt in der Vergangenheit!")
        # if not self.pk and self.start_date and self.start_date < timezone.now():
        #    raise ValidationError("Das Startdatum liegt in der Vergangenheit!")

        # if self.start_date and self.end_date and self.start_date >= self.end_date:
        #    raise ValidationError("Das Startdatum muss vor dem Enddatum liegen!")
        # if self.start_date and self.end_date:
        #    delta = self.end_date - self.start_date
        #    if delta.days >= 14:
        #        raise ValidationError(f"Das Event umfasst {delta.days} Tage! Korrekt?")
        if self.capacity < self.members.filter(attend_status="registered").count():
            raise ValidationError(
                "Die Teilnehmer*innenzahl darf nicht größer als die Kapazität sein."
            )

    def get_absolute_url(self):
        return reverse("event-detail", kwargs={"slug": self.slug})

    def is_yet_open_for_registration(self):
        return not self.open_date or self.open_date < timezone.now()

    def get_end_of_registration(self):
        return (
            self.close_date.date()
            if self.close_date
            else self.get_first_day_start_date()
        )

    def is_past(self):
        if date.today() > self.first_day:
            return True
        return False

    def is_past_hinweis(self):
        if self.is_past():
            return "vorüber"
        return "kommt noch"

    is_past_hinweis.short_description = "Event vorüber"

    event_over = property(is_past_hinweis)

    def is_open_for_registration(self):
        return self.is_yet_open_for_registration() and not self.is_past()

    def is_closed_for_registration(self):
        if (
            self.get_end_of_registration()
            and date.today() > self.get_end_of_registration()
        ):
            return True
        return False

    def is_closed_hinweis(self):
        if self.is_closed_for_registration():
            return "abgelaufen"
        return "offen"

    is_closed_hinweis.short_description = "Anmeldefrist"

    registration_over = property(is_closed_hinweis)

    def get_number_of_registered_members(self):
        return self.members.filter(attend_status="registered").count()

    def get_number_of_members(self):
        """
        gibt die Anzahl der Teilnehmer und der eingeschriebenen Moodle-User zurück
        """
        return f"{self.get_number_of_registered_members()} ({self.students_number})"

    get_number_of_members.short_description = "Teilnehmer"

    def get_number_of_free_places(self):
        return self.capacity - self.get_number_of_registered_members()

    get_number_of_free_places.short_description = "offen"

    def is_full(self):
        count = self.get_number_of_registered_members()
        capacity = self.capacity if self.capacity is not None else sys.maxsize
        if capacity <= count:
            return True
        return False

    def few_remaining_places(self):
        count = self.get_number_of_registered_members()
        capacity = self.capacity if self.capacity is not None else sys.maxsize
        if capacity - count <= 3:
            return True
        return False

    def get_duplicate_members(self):
        email_list = list(self.members.values_list("email", flat=True))
        return find_duplicates_in_list(email_list)

    def get_first_day(self):
        try:
            return self.event_days.all().order_by("start_date")[0]

        except IndexError:
            pass

    def get_first_day_start_date(self):
        try:
            return self.event_days.all().order_by("start_date")[0].start_date

        except IndexError:
            pass

    def get_year(self):
        try:
            return self.event_days.all().order_by("start_date")[0].start_date.year

        except IndexError:
            pass

    def get_last_day(self):
        try:
            return self.event_days.all().order_by("-start_date")[0]

        except IndexError:
            pass

    def is_several_days(self):
        return self.event_days.count() > 1

    @property
    def sorted_sponsors(self):
        return self.sponsors.order_by("eventsponsorthrough__position")

    def save(self, *args, **kwargs):
        max_length = self._meta.get_field("slug").max_length
        last_id = 0
        if Event.objects.exists():
            last_id = Event.objects.latest("id").id
        if not self.id:
            self.slug = slugify(f"{self.name}-{str(last_id+1)}")[:max_length]
        add = not self.pk
        # super(Event, self).save(*args, **kwargs)
        if add:
            # if not self.slug:
            #    self.slug = slugify(self.name)[:max_length]
            if not self.label:
                self.label = f"{self.name.partition(' ')[0]}-{date.today().year}-{str(last_id+1)}"
            kwargs["force_insert"] = False  # create() uses this, which causes error.

        self.first_day = self.get_first_day_start_date()

        return super().save(*args, **kwargs)


class EventSpeakerThrough(BaseModel):
    eventspeaker = models.ForeignKey(
        EventSpeaker, verbose_name="Dozent*in", on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        Event, verbose_name="Veranstaltung", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = "Dozent*in"
        verbose_name_plural = "Dozent*innen"


class EventSponsorThrough(BaseModel):
    eventsponsor = models.ForeignKey(
        EventSponsor, verbose_name="Pat*in", on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        Event, verbose_name="Veranstaltung", on_delete=models.CASCADE
    )
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Pat*in"
        verbose_name_plural = "Pat*innen"
        ordering = [
            "position",
        ]


class EventDocument(BaseModel):
    event = models.ForeignKey(
        Event, related_name="event_documents", on_delete=models.CASCADE
    )
    title = models.CharField("Titel", max_length=255)
    description = models.TextField("Beschreibung", null=True, blank=True)
    upload = models.FileField(upload_to="documents/")

    def __str__(self):
        return self.title


class EventDay(BaseModel):
    event = models.ForeignKey(
        Event, related_name="event_days", on_delete=models.CASCADE
    )
    start_date = models.DateField(
        verbose_name="Datum",
        help_text="Datum: Picker verwenden oder in der Form tt.mm.jj",
    )
    start_time = models.TimeField(verbose_name="Beginn", help_text="hh:mm")
    end_time = models.TimeField(verbose_name="Ende", help_text="hh:mm")

    class Meta:
        ordering = ("start_date",)
        verbose_name = "Veranstaltungstag"
        verbose_name_plural = "Veranstaltungstage"

    def __str__(self):
        return self.start_date.strftime("%d.%m.%y")

    def clean(self):
        """
        die im Admin Bereich eingegebenen Daten werden geprüft:
        - start_date darf nicht in der Vergangenheit liegen
        - end_date muss nach dem start_date liegen
        - Nachfrage bei mehr als 14 Tagen Dauer
        -
        """
        if not self.pk and self.start_date and self.start_date < timezone.now().date():
            raise ValidationError("Das Startdatum liegt in der Vergangenheit!")

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Die Startzeit muss vor der Endzeit liegen!")


class EventAgenda(BaseModel):
    event = models.ForeignKey(Event, related_name="agendas", on_delete=models.CASCADE)
    session_name = models.CharField(
        verbose_name="Programmteil",
        max_length=120,
    )
    start_time = models.TimeField(verbose_name="Beginn", null=True, blank=True)
    end_time = models.TimeField(verbose_name="Ende", null=True, blank=True)
    position = models.PositiveSmallIntegerField(
        verbose_name="Reihenfolge",
        null=True,
        help_text="Reihenfolge der Programme in der Anezige",
    )
    venue_name = models.CharField(
        verbose_name="wo", max_length=255, null=True, blank=True
    )
    description = RichTextField(
        verbose_name="Programm", config_name="short", blank=True
    )

    class Meta:
        ordering = ("position",)
        verbose_name = "Programm"
        verbose_name_plural = "Programme"

    def __str__(self):
        return self.session_name

    def save(self, *args, **kwargs):
        EventAgenda.objects.filter(position__gte=self.position).update(
            position=F("position") + 1
        )
        super(EventAgenda, self).save(*args, **kwargs)


class EventImage(BaseModel):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="event_image/")


MEMBER_ROLE_CHOICES = (
    (1, "Manager*in"),
    (3, "Trainer*in"),
    (5, "Teilnehmer*in"),
)


class MemberRole(BaseModel):
    roleid = models.PositiveSmallIntegerField(choices=MEMBER_ROLE_CHOICES)

    def __str__(self):
        return self.get_roleid_display()


class EventMember(AddressModel):
    """
    Teilnehmer werden verwaltet
    mit ihren Anmeldedaten
    """

    event = models.ForeignKey(
        Event,
        verbose_name="Veranstaltung",
        related_name="members",
        on_delete=models.CASCADE,
    )
    name = models.CharField("Kurzbezeichnung", max_length=255, null=True, blank=True)
    academic = models.CharField("Titel", max_length=40, null=True, blank=True)
    firstname = models.CharField("Vorname", max_length=255, blank=True)
    lastname = models.CharField("Nachname", max_length=255, blank=True)
    email = models.EmailField("E-Mail", blank=True, max_length=255)
    phone = models.CharField("Tel", max_length=64, blank=True)
    company = models.CharField("Firma", max_length=255, null=True, blank=True)
    vfll = models.BooleanField("VFLL-Mitglied", default=False)

    memberships = models.CharField("Mitgliedschaften", max_length=64, blank=True)
    attention = models.CharField(
        "aufmerksamen geworden durch", max_length=64, blank=True
    )
    attention_other = models.CharField("sonstige", max_length=64, blank=True)
    education_bonus = models.BooleanField("Bildungsprämie", default=False)
    message = models.TextField("Anmerkung", blank=True)
    free_text_field = models.TextField("Freitext", blank=True)
    check = models.BooleanField("Einverständnis", default=False)

    label = models.CharField(max_length=64)
    ATTEND_STATUS_CHOICES = (
        ("registered", "angemeldet"),
        ("waiting", "Warteliste"),
        ("attending", "nimmt teil"),
        ("absent", "nicht erschienen"),
        ("cancelled", "abgesagt"),
    )
    attend_status = models.CharField(
        verbose_name="Status", choices=ATTEND_STATUS_CHOICES, max_length=10
    )
    mail_to_admin = models.BooleanField("m > admin", default=False)
    mail_to_member = models.BooleanField("m > member", default=False)
    via_form = models.BooleanField("AF", default=False)
    moodle_id = models.PositiveIntegerField("MoodleID", default=0)
    roles = models.ManyToManyField(MemberRole, through="EventMemberRole")
    enroled = models.BooleanField(">m", default=False)

    # für vfll intern
    takes_part = models.BooleanField("Teilnahme", default=False)

    member_type = models.CharField(
        "Art der Mitgliedschaft",
        max_length=1,
        null=True,
        blank=True,
        default=None,
    )

    vote_transfer = models.CharField(
        "Stimmübertragung",
        max_length=255,
        blank=True,
    )
    vote_transfer_check = models.BooleanField(
        "Check Stimmübertragung",
        default=False,
    )

    data = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Teilnehmer*in"
        verbose_name_plural = "Teilnehmer*innen"
        unique_together = ["event", "name"]

    def __str__(self):
        return str(f"Anmeldung von {self.lastname}, {self.firstname}")

    def get_absolute_url(self):
        return reverse("member-detail", kwargs={"pk": self.pk})

    def get_registration_date(self):
        return self.date_created.strftime("%d.%m.%Y %H:%M")

    get_registration_date.short_description = "Anmeldedatum"

    def save(self, *args, **kwargs):
        add = not self.pk
        super(EventMember, self).save(*args, **kwargs)
        if add:
            if not self.label:
                self.label = f"{self.event.label}-A{str(self.id)}"
            kwargs["force_insert"] = False  # create() uses this, which causes error.
            super(EventMember, self).save(*args, **kwargs)
        if not self.name:
            self.name = f"{self.event.label} | {timezone.now()}"
            super(EventMember, self).save(*args, **kwargs)


class EventMemberRole(BaseModel):
    eventmember = models.ForeignKey(EventMember, on_delete=models.CASCADE)
    memberrole = models.ForeignKey(MemberRole, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Rolle"
        verbose_name_plural = "Rollen"


class EventHighlight(BaseModel):
    event = models.ForeignKey(
        Event,
        related_name="highlight",
        on_delete=models.CASCADE,
        limit_choices_to={
            "pub_status": "PUB",
            "first_day__gte": date.today(),
        },
    )

    def __str__(self):
        return self.event.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_single_instance",
                check=models.Q(id=1),
            ),
        ]
