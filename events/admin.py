from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse

from mapbox_location_field.admin import MapAdmin

from .models import (
    EventCategory,
    EventFormat,
    Event,
    EventImage,
    EventSpeaker,
    EventLocation,
    EventAgenda,
    EventMember,
)

from .email_template import (
    EmailTemplate
)

# setting date format in admin page
from django.conf.locale.de import formats as de_formats

de_formats.DATETIME_FORMAT = "d.m.y H:i"


class EventImageInline(admin.StackedInline):
    model = EventImage


class EventAgendaInline(admin.StackedInline):
    model = EventAgenda
    extra = 0
    verbose_name = "Programm"
    verbose_name_plural = "Programme"

class EventMemberAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Veranstaltung', {
            'fields': ('event', 'name')
        }),
         ('TeilnehmerIn', {
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

admin.site.register(EventMember, EventMemberAdmin)
class EventMemberInline(admin.TabularInline):
    model = EventMember
    extra = 0
    # show_change_link = False
    verbose_name = "Anmeldung"
    verbose_name_plural = "Anmeldungen"
    fields = ('firstname', 'lastname', 'vfll', 'education_bonus', 'change_link',)
    readonly_fields = ("firstname", 'lastname', 'change_link',)

    def has_add_permission(self, request, obj=None):
        if obj and obj.is_past():
            return False
        return True

    def change_link(self, obj):
        return mark_safe('<a href="%s">Edit</a>' % \
                        reverse('admin:events_eventmember_change',
                        args=(obj.id,)))

    change_link.short_description = 'Edit'


class EventAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'label',
        "registration_over",
        'start_date',
        'end_date',
        "get_number_of_members",
        "students_number",
        "capacity",
        'eventformat',
        'category',
        'status'
    )
    list_filter = ('eventformat', 'category', 'status')
    ordering = ('start_date', 'name')
    search_fields = ('=name',)
    readonly_fields = ('uuid', 'label', 'slug', 'moodle_id', 'date_created', 'date_modified')
    inlines = (EventAgendaInline, EventImageInline, EventMemberInline)

admin.site.register(EventCategory)
admin.site.register(EventFormat)
admin.site.register(Event, EventAdmin)


class EventSpeakerAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name',)
    ordering = ('last_name', 'first_name',)
    search_fields = ('=last_name', '=first_name',)  # case insensitive searching
    readonly_fields = ('date_created', 'date_modified')
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

