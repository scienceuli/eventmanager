from django.db import models
from datetime import datetime
from datetime import date
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

        if self.country:
            if address:
                address += ", " + self.get_country_display()
            else:
                address += self.get_country_display()
        return address

    


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
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, null=False, unique=True, editable=False)
    label = models.CharField(max_length=64)
    description = RichTextUploadingField(verbose_name="Teaser")
    duration = models.CharField(verbose_name="Dauer", max_length=255, null=True, blank=True)
    target_group = models.CharField(verbose_name="Zielgruppe", max_length=255, )
    prerequisites = RichTextUploadingField(verbose_name="Voraussetzungen", max_length=255, config_name='short')
    objectives = RichTextUploadingField(verbose_name="Lernziele", config_name='short')
    speaker = models.ManyToManyField(EventSpeaker, verbose_name="Referent*innen", through='EventSpeakerThrough')
    methods = models.CharField(verbose_name="Methoden", max_length=255, null=True, blank=True)

    SCHEDULED_STATUS_CHOICES = (
        ('yet to scheduled', 'noch offen'),
        ('scheduled', 'terminiert')
    )
    scheduled_status = models.CharField(max_length=25, choices=SCHEDULED_STATUS_CHOICES)
    location = models.ForeignKey(EventLocation, null=True, on_delete=models.DO_NOTHING, related_name='location_events')
    fees = RichTextField(verbose_name="Gebühren", config_name='short')
    catering = RichTextField(verbose_name="Verpflegung", null=True, blank=True, config_name='short')
    lodging = RichTextField(verbose_name="Übernachtung", null=True, blank=True, config_name='short')
    total_costs = RichTextField(verbose_name="Gesamtkosten", null=True, blank=True, config_name='short')
    registration = RichTextField(verbose_name="Anmeldung", config_name='short')
    notes = RichTextField(verbose_name="Hinweise", null=True, blank=True, config_name='short')
    start_date = models.DateTimeField(verbose_name="Beginn", null=True, help_text='Datum: Picker verwenden oder in der Form tt.mm.jj; Zeit: hh:mm')
    end_date = models.DateTimeField(verbose_name="Ende", null=True, help_text='Datum: Picker verwenden oder in der Form tt.mm.jj; Zeit: hh:mm')
    open_date = models.DateTimeField(
        verbose_name="Anmeldefrist Beginn",
        null=True,
        auto_now_add=True,
    )
    close_date = models.DateTimeField(
        verbose_name="Anmeldefrist Ende", null=True, blank=True
    )
    capacity = models.PositiveIntegerField()
    STATUS_CHOICES = (
        ('active', 'aktiv'),
        ('deleted', 'verschoben'),
        ('cancel', 'abgesagt'),
    )
    status = models.CharField(choices=STATUS_CHOICES, max_length=10)
    moodle_id = models.PositiveSmallIntegerField(default=0)
    moodle_course_created = models.BooleanField(default=False)
    students_number = models.PositiveSmallIntegerField(default=0, editable=False)

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
        if not self.pk and self.close_date and self.close_date < timezone.now():
            raise ValidationError("Die Anmeldfrist liegt in der Vergangenheit!")
        #if not self.pk and self.start_date and self.start_date < timezone.now():
        #    raise ValidationError("Das Startdatum liegt in der Vergangenheit!")

        #if self.start_date and self.end_date and self.start_date >= self.end_date:
        #    raise ValidationError("Das Startdatum muss vor dem Enddatum liegen!")
        #if self.start_date and self.end_date:
        #    delta = self.end_date - self.start_date
        #    if delta.days >= 14:
        #        raise ValidationError(f"Das Event umfasst {delta.days} Tage! Korrekt?")

        
    def save(self, *args, **kwargs):
        max_length = self._meta.get_field('slug').max_length
        if not self.id:
            self.slug = slugify(f"{self.name}-{self.moodle_id}")[:max_length]
        add = not self.pk
        #super(Event, self).save(*args, **kwargs)
        if add:
            #if not self.slug:
            #    self.slug = slugify(self.name)[:max_length]
            if not self.label:
                last_id = Event.objects.latest('id').id
                self.label = f"{self.eventformat.name[0].capitalize()}-{date.today().year}-{str(last_id+1)}"
            kwargs['force_insert'] = False # create() uses this, which causes error.
        super(Event, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('event-detail', kwargs={'slug': self.slug}) 

    def is_yet_open_for_registration(self):
        return not self.open_date or self.open_date < timezone.now().date

    def get_end_of_registration(self):
        return self.close_date.date() if self.close_date else self.get_first_day_start_date()

    def is_past(self):
        if self.get_end_of_registration() and date.today() > self.get_end_of_registration():
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
        '''
        gibt die Anzahl der Teilnehmer und der eingeschriebenen Moodle-User zurück
        '''
        return f"{self.members.count()} ({self.students_number})"

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

    def get_first_day(self):
        try:
            return self.event_days.all().order_by('start_date')[0]
           
        except IndexError:
            pass

    def get_first_day_start_date(self):
        try:
            return self.event_days.all().order_by('start_date')[0].start_date
           
        except IndexError:
            pass

    def get_year(self):
        try:
            return self.event_days.all().order_by('start_date')[0].start_date.year
           
        except IndexError:
            pass
    
    def get_last_day(self):
        try:
            return self.event_days.all().order_by('-start_date')[0]
           
        except IndexError:
            pass


class EventSpeakerThrough(BaseModel):
    eventspeaker = models.ForeignKey(EventSpeaker, verbose_name='Referent*in', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, verbose_name='Veranstaltung', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Referent*in"
        verbose_name_plural = "Referent*innen"


class EventDay(BaseModel):
    event = models.ForeignKey(Event, related_name="event_days", on_delete=models.CASCADE)
    start_date = models.DateField(verbose_name="Datum", help_text='Datum: Picker verwenden oder in der Form tt.mm.jj')
    start_time = models.TimeField(verbose_name="Beginn", help_text='hh:mm')
    end_time = models.TimeField(verbose_name="Ende", help_text='hh:mm')

    class Meta:
        ordering = ('start_date',)
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

MEMBER_ROLE_CHOICES = (
    (1, 'Manager*in'),
    (3, 'Trainer*in'),
    (5, 'Teilnehmer*in'),
)

class MemberRole(BaseModel):
    roleid = models.PositiveSmallIntegerField(choices=MEMBER_ROLE_CHOICES)

    def __str__(self):
        return self.get_roleid_display()



class EventMember(AddressModel):
    '''
    Teilnehmer werden verwaltet 
    mit ihren Anmeldedaten
    '''
    event = models.ForeignKey(Event, verbose_name='Veranstaltung', related_name="members", on_delete=models.CASCADE)
    name = models.CharField('Kurzbezeichnung', max_length=255)
    firstname = models.CharField('Vorname', max_length=255, blank=True)
    lastname = models.CharField('Nachname', max_length=255, blank=True)
    email = models.EmailField("E-Mail", blank=True, max_length=255)
    phone = models.CharField("Tel", max_length=64, blank=True)
    vfll = models.BooleanField("VFLL-Mitglied", default=False)

    memberships = models.CharField("Mitgliedschaften", max_length=64, blank=True)
    attention = models.CharField('aufmerksamen geworden durch', max_length=64, blank=True)
    attention_other = models.CharField('sonstige', max_length=64, blank=True)
    education_bonus = models.BooleanField('Bildungsprämie', default=False)
    message = models.TextField("Anmerkung", blank=True)
    check = models.BooleanField(default=False)

    label = models.CharField(max_length=64)
    ATTEND_STATUS_CHOICES = (
        ('registered', 'angemeldet'),
        ('waiting', 'Warteliste'),
        ('attending', 'nimmt teil'),
        ('absent', 'nicht erschienen'),
        ('cancelled', 'abgesagt'),
    )
    attend_status = models.CharField(choices=ATTEND_STATUS_CHOICES, max_length=10)
    mail_to_admin = models.BooleanField("m > admin", default=False)
    moodle_id = models.PositiveIntegerField("MoodleID", default=0)
    roles = models.ManyToManyField(MemberRole, through='EventMemberRole')
    enroled = models.BooleanField(">m", default=False)

    class Meta:
        verbose_name = 'Teilnehmer*in'
        verbose_name_plural = 'Teilnehmer*innen'
        unique_together = ['event', 'name']

    def __str__(self):
        return str(f"Anmeldung von {self.lastname}, {self.firstname}")

    def save(self, *args, **kwargs):
        add = not self.pk
        super(EventMember, self).save(*args, **kwargs)
        if add:
            if not self.label:
                self.label = f"{self.event.label}-A{str(self.id)}"
            kwargs['force_insert'] = False # create() uses this, which causes error.
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

    

