from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError
from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.fields import RichTextField

from .abstract import BaseModel, AddressModel


class EventCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField("Beschreibung", blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('event-category-list')

class EventFormat(BaseModel):
    name = models.CharField(verbose_name="Format", max_length=255, unique=True)
    description = models.TextField("Beschreibung", blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "Format"
        verbose_name_plural = "Formate"

    def __str__(self):
        return self.name

class EventLocation(AddressModel):
    title = models.CharField("Name", max_length=128)
    url = models.URLField(verbose_name="Veranstaltungsort Website", blank=True,)

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

        if self.country:
            if address:
                address += ", " + self.get_country_display()
            else:
                address += self.get_country_display()
        return address

    class Meta:
        verbose_name = "Veranstaltungsort"
        verbose_name_plural = "Veranstaltungsorte"


class EventSpeaker(BaseModel):
    first_name = models.CharField("Vorname", blank=True, max_length=128)
    last_name = models.CharField("Nachname", max_length=128)
    email = models.EmailField("E-Mail", blank=True, max_length=255)
    phone = models.CharField("Tel", max_length=64, blank=True)
    bio = models.TextField("Biografie", blank=True)
    url = models.URLField("Website", blank=True)
    social_url = models.URLField("Soziale Medien", blank=True)
    image = models.ImageField(upload_to='speaker/', blank=True)

    class Meta:
        ordering = ('last_name',)
        verbose_name = "Referent*in"
        verbose_name_plural = "Referent*innen"

    def __str__(self):
        return '{first_name} {last_name}'.format(
            first_name=self.first_name,
            last_name=self.last_name
        ).strip()


class Event(BaseModel):
    category = models.ForeignKey(EventCategory, verbose_name="Kategorie", on_delete=models.CASCADE)
    eventformat = models.ForeignKey(EventFormat, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, null=False, unique=True)
    label = models.CharField(max_length=64)
    description = RichTextUploadingField(verbose_name="Teaser")
    duration = models.CharField(verbose_name="Dauer", max_length=255, null=True, blank=True)
    target_group = models.CharField(verbose_name="Zielgruppe", max_length=255, )
    prerequisites = RichTextUploadingField(verbose_name="Voraussetzungen", max_length=255, config_name='short')
    objectives = RichTextUploadingField(verbose_name="Lernziele", config_name='short')
    speaker = models.ForeignKey(EventSpeaker, verbose_name="Referent/-in", on_delete=models.DO_NOTHING, related_name="speaker_events")
    methods = models.CharField(verbose_name="Methoden", max_length=255, null=True, blank=True)

    select_scheduled_status = (
        ('yet to scheduled', 'noch offen'),
        ('scheduled', 'terminiert')
    )
    scheduled_status = models.CharField(max_length=25, choices=select_scheduled_status)
    location = models.ForeignKey(EventLocation, null=True, on_delete=models.DO_NOTHING, related_name='location_events')
    fees = RichTextField(verbose_name="Gebühren", config_name='short')
    catering = RichTextField(verbose_name="Verpflegung", null=True, blank=True, config_name='short')
    lodging = RichTextField(verbose_name="Übernachtung", null=True, blank=True, config_name='short')
    total_costs = RichTextField(verbose_name="Gesamtkosten", null=True, blank=True, config_name='short')
    registration = RichTextField(verbose_name="Anmeldung", config_name='short')
    notes = RichTextField(verbose_name="Hinweise", null=True, blank=True, config_name='short')
    start_date = models.DateTimeField(verbose_name="Beginn")
    end_date = models.DateTimeField(verbose_name="Ende")
    open_date = models.DateTimeField(
        verbose_name="Anmeldefrist Beginn",
        null=True,
        blank=True,
        # default=timezone.datetime(2020, 1, 1),
    )
    close_date = models.DateTimeField(
        verbose_name="Anmeldefrist Ende", null=True, blank=True
    )
    capacity = models.PositiveIntegerField()
    status_choice = (
        ('active', 'aktiv'),
        ('deleted', 'verschoben'),
        ('cancel', 'abgesagt'),
    )
    status = models.CharField(choices=status_choice, max_length=10)
    moodle_id = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('start_date',)
        verbose_name = "Veranstaltung"
        verbose_name_plural = "Veranstaltungen"

    def __str__(self):
        return self.name

    def clean(self):
        """
        die im Admin Bereich eingegebenen Daten werden geprüft:
        - start_date darf nicht in der Vergangenheit liegen
        - end_date muss nach dem start_date liegen
        - Nachfrage bei mehr als 14 Tagen Dauer
        - 
        """
        if self.start_date < timezone.now():
            raise ValidationError("Das Startdatum liegt in der Vergangenheit!")

        if self.start_date >= self.end_date:
            raise ValidationError("Das Startdatum muss vor dem Enddatum liegen!")

        delta = self.end_date - self.start_date
        if delta.days >= 14:
            raise ValidationError(f"Das Event umfasst {delta.days} Tage! Korrekt?")


        
    def save(self, *args, **kwargs):
        max_length = self._meta.get_field('slug').max_length
        self.slug = slugify(self.name)[:max_length]
        add = not self.pk
        super(Event, self).save(*args, **kwargs)
        if add:
            if not self.slug:
                self.slug = slugify(self.name)[:max_length]
            if not self.label:
                self.label = f"{self.eventformat.name[0].capitalize()}{self.start_date.year}-{str(self.id)}"
            kwargs['force_insert'] = False # create() uses this, which causes error.
            super(Event, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('event-detail', kwargs={'slug': self.slug}) 


    def is_yet_open_for_registration(self):
        return not self.open_date or self.open_date < timezone.now()

    def get_end_of_registration(self):
        return self.close_date if self.close_date else self.start_date


    def is_past(self):
        if timezone.now() > self.get_end_of_registration():
            return True
        return False

    def is_open_for_registration(self):
        return self.is_yet_open_for_registration() and not self.is_past()

    def is_past_hinweis(self):
        if self.is_past():
            return "abgelaufen"
        return "offen"

    is_past_hinweis.short_description = "Anmeldefrist"

    registration_over = property(is_past_hinweis)

    def get_number_of_members(self):
        return self.members.count()

    get_number_of_members.short_description = "Teilnehmer"

    def get_number_of_free_places(self):
        return self.capacity - self.members.count() 

    get_number_of_free_places.short_description = "offen"

    def is_full(self):
        count = self.members.count()
        capacity = self.capacity if self.capacity is not None else sys.maxsize
        if capacity <= count:
            return True
        return False




class EventAgenda(BaseModel):
    event = models.ForeignKey(Event, related_name="agendas", on_delete=models.CASCADE)
    session_name = models.CharField(verbose_name="Programmteil", max_length=120, )
    start_time = models.TimeField(verbose_name="Beginn", null=True, blank=True)
    end_time = models.TimeField(verbose_name="Ende", null=True, blank=True)
    venue_name = models.CharField(verbose_name="wo", max_length=255, null=True, blank=True)
    description = RichTextUploadingField(verbose_name="Programm")

    class Meta:
        ordering = ('start_time',)
        verbose_name = "Programm"
        verbose_name_plural = "Programme"

    def __str__(self):
        return self.session_name

class EventImage(BaseModel):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='event_image/')

class EventMember(BaseModel):
    '''
    Teilnehmer sollen nicht verwaltet werden
    d.h. nur anonyme Erfassung ohne Teilnehmerdaten
    '''
    event = models.ForeignKey(Event, related_name="members", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=64)
    attend_status_choice = (
        ('registered', 'angemeldet'),
        ('waiting', 'Warteliste'),
        ('attending', 'nimmt teil'),
        ('absent', 'nicht erschienen'),
        ('cancelled', 'abgesagt'),
    )
    attend_status = models.CharField(choices=attend_status_choice, max_length=10)
    mail_to_admin = models.BooleanField("m > admin", default=False)

    class Meta:
        unique_together = ['event', 'name']

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        add = not self.pk
        super(EventMember, self).save(*args, **kwargs)
        if add:
            if not self.label:
                self.label = f"{self.event.label}-A{str(self.id)}"
            kwargs['force_insert'] = False # create() uses this, which causes error.
            super(EventMember, self).save(*args, **kwargs)
    
