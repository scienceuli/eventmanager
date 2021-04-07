from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.utils.http import urlencode
from django.utils.html import format_html
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, path
from django import forms
from django.db.models import Min, Max
from django.forms.models import BaseInlineFormSet

import io, csv

from mapbox_location_field.admin import MapAdmin

# for inline actions, from 3rd party module
from inline_actions.admin import InlineActionsMixin
from inline_actions.admin import InlineActionsModelAdminMixin

from fieldsets_with_inlines import FieldsetsInlineMixin

from .actions import export_as_xls

from .validators import csv_content_validator

from .models import (
    EventCategory,
    EventFormat,
    Event,
    EventDay,
    EventImage,
    EventSpeaker,
    EventSpeakerThrough,
    EventSponsor,
    EventSponsorThrough,
    EventLocation,
    EventAgenda,
    EventMember,
    EventMemberRole,
)

from .email_template import (
    EmailTemplate
)

from moodle.management.commands.moodle import enrol_user_to_course, unenrol_user_from_course, create_moodle_course, delete_moodle_course

# setting date format in admin page
from django.conf.locale.de import formats as de_formats

de_formats.DATETIME_FORMAT = "d.m.y H:i"


class InlineWithoutDelete(BaseInlineFormSet): 
    '''
    is needed to provide Inlines without Delete Checkbox
    '''
    def __init__(self, *args, **kwargs): 
        super(InlineWithoutDelete, self).__init__(*args, **kwargs) 
        self.can_delete = False 

class EventImageInline(admin.StackedInline):
    model = EventImage


class EventAgendaInline(admin.StackedInline):
    model = EventAgenda
    extra = 0
    verbose_name = "Programm"
    verbose_name_plural = "Programme"

class EventDayAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'start_time', 'end_time']

admin.register(EventDay, EventDayAdmin)

class EventDayInline(admin.StackedInline):
    model = EventDay
    extra = 0
    verbose_name = "Veranstaltungstag"
    verbose_name_plural = "Veranstaltungstage"

class CsvImportForm(forms.Form):
    '''
    For for importing Course Participants
    '''
    csv_file = forms.FileField(
        label='CSV-Datei für Import auswählen:',
        validators=[csv_content_validator],
        )


class EventMemberRoleInline(admin.TabularInline):
    model = EventMemberRole
    extra = 0

class EventMemberAdmin(admin.ModelAdmin):

    list_display = ['lastname', 'firstname', 'email', 'event']
    list_filter = ['event',]
    search_fields = (
        'lastname',
        'firstname',
        'email'
    )
    inlines = [EventMemberRoleInline,]

    change_list_template = "admin/event_member_list.html"
    fieldsets = (
        ('Veranstaltung', {
            'fields': ('event', 'name')
        }),
        ('Name/Email/Tel', {
            'fields': ('firstname', 'lastname', 'email', 'phone')
        }),
        ('Anschrift', {
            'fields': ('address_line', 'street', 'postcode', 'city', 'state')
        }),
        ('weitere Angaben', {
            'classes': ('collapse',),
            'fields': ('vfll', 'attention', 'attention_other', 'education_bonus'),
        }),
    )
    actions = [export_as_xls]

   
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls


    def import_csv(self, request):
        print(request.GET.get('event__id','None'))
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]

            # let's check if it is a csv file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Keine CSV-Datei')

            data_set = csv_file.read().decode('UTF-8')
            # setup a stream which is when we loop through each line we are able to handle a data in a stream
            io_string = io.StringIO(data_set)
            next(io_string)

            bulk_create_list = []

            for row in csv.reader(io_string, delimiter=';'):
                # Here's how the row list looks like:
                # ['firstname', 'lastname' 'email']
                # username will be calculated when exported to moodle
                # preparing bulk crate
                bulk_create_list.append(EventMember(
                    firstname=row[0],
                    lastname=row[1], 
                    email=row[2])
                )

                print(row[0])
                print(row[1])
                print(row[2])
                print(request.GET.get('event__id','None'))

            self.message_user(request, "CSV-Datei wurde importiert")
            # EventMember
            return redirect("..")

        form = CsvImportForm()
        context = {"form": form,
            'message': 'Reihenfolge der Spalten in der CSV-Datei: firstname, lastname, email'
            }
        return render(
            request, "admin/csv_form.html", context
        )

admin.site.register(EventMember, EventMemberAdmin)

class EventMemberInline(InlineActionsMixin, admin.TabularInline):
    model = EventMember
    extra = 0
    formset = InlineWithoutDelete
    # ref for inline actions: https://github.com/escaped/django-inline-actions
    inline_actions = []
    # show_change_link = False
    verbose_name = "Anmeldung"
    verbose_name_plural = "Anmeldungen"
    fields = ('firstname', 'lastname', 'email', 'vfll', 'education_bonus', 'change_link', 'enroled', 'moodle_id')
    #inline_actions = ['enrol_to_moodle_course']
    readonly_fields = ('change_link','enroled', 'moodle_id')

    def has_add_permission(self, request, obj=None):
        if obj and obj.is_past():
            return False
        return True

    def change_link(self, obj):
        return mark_safe('<a href="%s">Edit</a>' % \
                        reverse('admin:events_eventmember_change',
                        args=(obj.id,)))

    change_link.short_description = 'Edit'

    def get_inline_actions(self, request, obj=None):
        actions = super(EventMemberInline, self).get_inline_actions(request, obj)
        if obj and obj.event.moodle_id > 0:
            if obj.enroled == False:
                actions.append('enrol_to_moodle_course')
            elif obj.enroled == True:
                actions.append('unenrol_from_moodle_course')
        elif obj and obj.event.moodle_id == 0:
            actions.append('delete_user')
        return actions

    def enrol_to_moodle_course(self, request, obj, parent_obj=None):
        obj.enroled = True
        obj.save()
        enrol_user_to_course(obj.email, obj.event.moodle_id, obj.event.moodle_new_user_flag, 5, obj.firstname, obj.lastname) # 5: student
        return True

    enrol_to_moodle_course.short_description = 'Einschreiben'

    def unenrol_from_moodle_course(self, request, obj, parent_obj=None):
        obj.enroled = False
        obj.save()
        unenrol_user_from_course(obj.moodle_id, obj.event.moodle_id)

    unenrol_from_moodle_course.short_description = "Ausschreiben"


    def delete_user(self, request, obj, parent_obj):
        obj.delete()
    delete_user.short_description = "Löschen"

class EventSpeakerThroughInline(admin.TabularInline):
    model = EventSpeakerThrough
    extra = 0

class EventSponsorThroughInline(admin.TabularInline):
    model = EventSponsorThrough
    extra = 0

class EventSpeakerAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name',)
    ordering = ('last_name', 'first_name',)
    search_fields = ('=last_name', '=first_name',)  # case insensitive searching
    readonly_fields = ('date_created', 'date_modified')
    inlines = (EventSpeakerThroughInline,)
    fieldsets = (
        ('Name', {
            'fields': (('first_name', 'last_name',),)
        }),
        ('Kontakt', {
            'fields': ('email', 'phone',)
        }),
        ('Über', {
            'fields': ('bio',  ('url', 'social_url',), 'image',)
        }),
        ('Änderungen', {
            'fields': ('date_created', 'date_modified'),
            'classes': ('collapse',),
        }),
    )
    
admin.site.register(EventSpeaker, EventSpeakerAdmin)

class EventSponsorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name',)
    ordering = ('last_name', 'first_name',)
    search_fields = ('=last_name', '=first_name',)  # case insensitive searching
    readonly_fields = ('date_created', 'date_modified')
    inlines = (EventSponsorThroughInline,)
    fieldsets = (
        ('Name', {
            'fields': (('first_name', 'last_name',),)
        }),
        ('Kontakt', {
            'fields': ('email', 'phone',)
        }),
        ('Über', {
            'fields': ('image',)
        }),
        ('Intern', {
            'fields': ('date_created', 'date_modified'),
            'classes': ('collapse',),
        }),
    )
    
admin.site.register(EventSponsor, EventSponsorAdmin)

# generating link to event pdf 
def admin_event_pdf(obj):
    return mark_safe('<a href="{}">Pdf</a>'.format(
        reverse('admin-event-pdf', args=[obj.id])
    ))

admin_event_pdf.short_description = 'Pdf'


class EventAdmin(InlineActionsModelAdminMixin, admin.ModelAdmin):
    change_list_template = "admin/event_change_list.html"
    change_form_template = "admin/event_change_form.html"

    list_display = (
        'name', 
        'label',
        "registration_over",
        'get_start_date',
        'get_end_date',
        "view_members_link",
        "capacity",
        'eventformat',
        'category',
        'status',
        admin_event_pdf
    )
    list_filter = ('eventformat', 'category', 'status')
    ordering = ('name',)
    search_fields = ('=name',)
    readonly_fields = ('uuid', 'slug', 'moodle_id', 'moodle_course_created', 'date_created', 'date_modified')
    #readonly_fields = ('uuid', 'label', 'slug', 'date_created', 'date_modified')
    exclude = ('start_date', 'end_date',)
    fieldsets = (
        ('Name, Kurztitel, Format', {
            'fields': ('name', 'label', 'category', 'eventformat')
        }),
        ('Inhaltliche Angaben', {
            'fields': ('description', 'target_group', 'prerequisites', 'objectives', 'methods', )
        }),
        ('Ort, Kosten, Dauer', {
            'fields': ('location', 'duration', 'fees', 'catering', 'lodging', 'total_costs', )
        }),
        ('Kapazität, Anmeldung, Hinweise, Status', {
            'fields': ('capacity', 'registration', 'close_date', 'scheduled_status', 'status', 'notes', )
        }),
        ('Moodle', {
            'fields': ('moodle_id', 'moodle_course_created'),
        }),
        ('Intern', {
            'fields': ('slug', 'uuid', 'date_created', 'date_modified'),
            'classes': ('collapse',),
        }),
    )
    inlines = (EventDayInline, EventSpeakerThroughInline, EventSponsorThroughInline, EventAgendaInline, EventImageInline, EventMemberInline)
    actions = ('copy_event',)
    inline_actions = []

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _start_date_min=Min("event_days__start_date"),
            _start_date_max=Max("event_days__start_date"),
        )
        
        return queryset

    def get_start_date(self, obj):
        """
        wenn das Event ein Moodle-Kurs ist,
        werden start_date und end_date angezeigt.
        Beide Daten werden (Stand 16.3.21) in Moodle gepflegt
        geandert 21.3.21
        immer start_date_min und max der model instance
        """
        """
        if obj.moodle_id > 0:
            return obj.start_date
        else:
            if obj._start_date_min:
                return obj._start_date_min.strftime("%d.%m.%y")
            return "-"
        """
        if obj._start_date_min:
            return obj._start_date_min.strftime("%d.%m.%y")
        return "-"

    get_start_date.admin_order_field = '_start_date_min'
    get_start_date.short_description = 'Beginn'

    def get_end_date(self, obj):
        # siehe Bem. zu get_start_date
        """
        if obj.moodle_id > 0:
            return obj.end_date
        else:
            if obj._start_date_max:
                return obj._start_date_max.strftime("%d.%m.%y")
            return "-"
        """
        if obj._start_date_max:
            return obj._start_date_max.strftime("%d.%m.%y")
        return "-"

    get_end_date.admin_order_field = '_start_date_max'
    get_end_date.short_description = 'Ende'

    def view_members_link(self, obj):
        count = obj.get_number_of_members()
        url = (
            reverse("admin:events_eventmember_changelist")
            + "?"
            + urlencode({'event__id': f"{obj.id}"})
        )
        return format_html('<a href="{}">{}</a>', url, count)

    view_members_link.short_description = 'Teilnehmer*innen'

    def get_inline_actions(self, request, obj=None):
        actions = super(EventAdmin, self).get_inline_actions(request, obj)
        if obj.moodle_id == 0 and obj.category.name == 'Onlineseminare':
            actions.append('create_course_in_moodle')
        if not obj.moodle_id == 0 and obj.category.name == 'Onlineseminare' and not obj.members.exists():
            actions.append('delete_course_in_moodle')
        return actions


    def create_course_in_moodle(self, request, obj, parent_obj=None):
        #obj.save()
        category = 3 # wird in Kurse in Planung angelegt
        if not obj.get_first_day():
            self.message_user(request, "Kurs hat kein Startdatum und kann nicht angelegt werden", messages.ERROR)
            return None
        else:
            response = create_moodle_course(obj.name, obj.label, category, obj.speaker.all(), obj.get_first_day(), obj.get_last_day())
        if type(response) == dict:
            if 'warnings' in response and response['warnings']:
                self.message_user(request, response['warnings'], messages.WARNING)
            if 'exception' in response or 'errorcode' in response:
                self.message_user(
                    request, 
                    f"Moodle-Kurs konnte nicht angelegt werden: {response.get('exception', '')}, {response.get('errorcode','')}, {response.get('message','')}", messages.ERROR)
        else:
            new_course_id = response[0].get('id', 0) # moodle id of the new course
            obj.moodle_id = new_course_id
            obj.moodle_course_created = True
            obj.save()
            self.message_user(request, f"neuer Moodle-Kurs mit ID {new_course_id} angelegt", messages.SUCCESS)


    create_course_in_moodle.short_description = ">M"

    def delete_course_in_moodle(self, request, obj, parent_obj=None):
        if obj.moodle_id == 0:
            self.message_user(request, "Kurs ist kein Moodle-Kurs und kann nicht gelöscht werden", messages.ERROR)
            return None
        elif obj.members.exists():
            self.message_user(request, "Kurs hat Teilnehmer und kann nicht gelöscht werden", messages.ERROR)
            return None
        else:
            response = delete_moodle_course(obj.moodle_id)

        if type(response) == dict:
            print(response)
            if 'warnings' in response and not response['warnings']:
                self.message_user(request, f"Moodle-Kurs mit ID {obj.moodle_id} wurde gelöscht, im EventManager ist er aber weiterhin vorhanden.", messages.SUCCESS)
                obj.moodle_id = 0
                obj.moodle_course_created = False
                obj.save()
            if 'exception' in response or 'errorcode' in response:
                self.message_user(
                    request, 
                    f"Moodle-Kurs konnte nicht gelöscht werden: {response.get('exception', '')}, {response.get('errorcode','')}, {response.get('message','')}", messages.ERROR)
        else:
            return None
            
    
    delete_course_in_moodle.short_description = "xM"

    def copy_event(self, request, queryset):
        #TODO: handling of fk's , ref: https://stackoverflow.com/questions/32234986/duplicate-django-model-instance-and-all-foreign-keys-pointing-to-it
        for event in queryset:
            # fk's to copy
            old_agendas = event.agendas.all()
            # m2m to copy
            old_speakers = event.speaker.all()
            event.pk = None
            event.slug = None
            event.label = None
            event.save()
            # many-to-one relationships are preserved when the parent object is copied,
            # so they don't need to be copied separately.

            # Many to many fields are relationships where many parent objects can be related to many
            # child objects. Because of this the child objects don't need to be copied when we copy
            # the parent, we just need to re-create the relationship to them on the copied parent.
            event.speaker.set(old_speakers)

            # fk's = One to many fields are backward relationships where many child objects are related to the
            # parent. We create a dictionary with related objects and make a bulk create afterwards 
            # to avoid calling fk.save() and hitting the database once per iteration of this loop
            new_agendas = {}
            for fk in old_agendas:
                fk.pk = None
                try:
                # Use fk.__class__ here to avoid hard-coding the class name
                    new_agendas[fk.__class__].append(fk)
                except KeyError:
                    new_agendas[fk.__class__] = [fk]

            # Now we can issue just two calls to bulk_create,
            # one for fkeys_a and one for fkeys_b
            for cls, list_of_fks in new_agendas.items():
                cls.objects.bulk_create(list_of_fks)

    copy_event.short_description = "Copy Event"
            
            
            
       

    

admin.site.register(EventCategory)
admin.site.register(EventFormat)
admin.site.register(Event, EventAdmin)


class EventLocationAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', )
    list_filter = ('city',)
    ordering = ('city', 'title')
    readonly_fields = ('date_created', 'date_modified')
    fieldsets = (
        ('Details', {
            'fields': ('title', 'url', )
        }),
        ('Adresse', {
            'fields': ('address_line', 'street', 'city', 'postcode', 'state',)
        }),
        ('Änderungen', {
            'fields': ('date_created', 'date_modified'),
            'classes': ('collapse',),
        }),
    )


admin.site.register(EventLocation, EventLocationAdmin)

class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'text_template', 'counter')
    ordering = ('name',)
    search_fields = ('=name',)
    readonly_fields = ('date_created', 'date_modified', 'counter')
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'counter'),
        }),
        ('Templates', {
            'fields': ('text_template', 'html_template',),
        }),
        ('Änderungen', {
            'fields': ('date_created', 'date_modified',),
            'classes': ('collapse',),
        }),
    )


admin.site.register(EmailTemplate, EmailTemplateAdmin)

