from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.http import urlencode
from django.utils.html import format_html
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, path
from django.utils.encoding import force_text
from django import forms
from django.db.models import Min, Max
from django.forms.models import BaseInlineFormSet
from django.contrib.admin.models import LogEntry


from django.contrib.admin import SimpleListFilter


import io, csv

from mapbox_location_field.admin import MapAdmin

# for inline actions, from 3rd party module
from inline_actions.admin import InlineActionsMixin
from inline_actions.admin import InlineActionsModelAdminMixin

from fieldsets_with_inlines import FieldsetsInlineMixin

from .actions import export_as_xls, import_from_csv

from .validators import csv_content_validator

from .models import (
    Home,
    EventCategory,
    EventFormat,
    Event,
    EventDay,
    EventHighlight,
    EventImage,
    EventDocument,
    EventOrganizer,
    EventSpeaker,
    EventSpeakerThrough,
    EventSponsor,
    EventExternalSponsor,
    EventSponsorThrough,
    EventExternalSponsorThrough,
    EventLocation,
    EventAgenda,
    EventMember,
    EventMemberRole,
    MemberRole,
    EventHighlight,
)

from .admin_views import hitcount_view

from .email_template import EmailTemplate

from moodle.management.commands.moodle import (
    enrol_user_to_course,
    unenrol_user_from_course,
    create_moodle_course,
    delete_moodle_course,
    assign_roles_to_enroled_user,
)

# setting date format in admin page
from django.conf.locale.de import formats as de_formats

de_formats.DATETIME_FORMAT = "d.m.y H:i"


class HomeAdmin(admin.ModelAdmin):
    model = Home

    def has_add_permission(self, request):
        # if there's already an entry, do not allow adding
        count = Home.objects.all().count()
        if count == 0:
            return True

        return False


admin.site.register(Home, HomeAdmin)


class EventCategoryAdmin(admin.ModelAdmin):
    model = EventCategory

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(EventCategoryAdmin, self).formfield_for_dbfield(
            db_field, **kwargs
        )
        if db_field.name == "title":
            formfield.widget = forms.Textarea(attrs=formfield.widget.attrs)
        return formfield

    def has_delete_permission(self, request, obj=None):
        return False


class EventOrganizerAdmin(admin.ModelAdmin):
    model = EventOrganizer


class InlineWithoutDelete(BaseInlineFormSet):
    """
    is needed to provide Inlines without Delete Checkbox
    """

    def __init__(self, *args, **kwargs):
        super(InlineWithoutDelete, self).__init__(*args, **kwargs)
        self.can_delete = False


class EventImageInline(admin.StackedInline):
    model = EventImage


class EventDocumentInline(admin.StackedInline):
    model = EventDocument
    extra = 0
    verbose_name = "Dokument"
    verbose_name_plural = "Dokumente"


class EventAgendaInline(admin.StackedInline):
    model = EventAgenda
    extra = 0
    verbose_name = "Programm"
    verbose_name_plural = "Programme"


class EventDayAdmin(admin.ModelAdmin):
    list_display = ["start_date", "start_time", "end_time"]


admin.register(EventDay, EventDayAdmin)


class EventDayInline(admin.StackedInline):
    model = EventDay
    extra = 0
    verbose_name = "Veranstaltungstag"
    verbose_name_plural = "Veranstaltungstage"


class CsvImportForm(forms.Form):
    """
    For for importing Course Participants
    """

    csv_file = forms.FileField(
        label="CSV-Datei für Import auswählen:",
        validators=[csv_content_validator],
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all())


class EventMemberRoleInline(admin.TabularInline):
    model = EventMemberRole
    extra = 0


class EventMemberAdmin(admin.ModelAdmin):

    list_display = [
        "lastname",
        "firstname",
        "academic",
        "email",
        "event",
        "date_created",
        "via_form",
        "mail_to_admin",
    ]
    list_filter = [
        "event",
    ]
    search_fields = ("lastname", "firstname", "email")
    readonly_fields = ["name", "mail_to_admin", "via_form"]
    inlines = [
        EventMemberRoleInline,
    ]

    change_list_template = "admin/event_member_list.html"
    fieldsets = (
        ("Veranstaltung", {"fields": ("event", "name")}),
        ("Name/Email/Tel", {"fields": ("firstname", "lastname", "email", "phone")}),
        ("Status", {"fields": ("attend_status",)}),
        (
            "Anschrift",
            {"fields": ("address_line", "street", "postcode", "city", "state")},
        ),
        (
            "weitere Angaben",
            {
                "classes": ("collapse",),
                "fields": (
                    "vfll",
                    "memberships",
                    "check",
                    "attention",
                    "attention_other",
                    "education_bonus",
                ),
            },
        ),
        (
            "intern",
            {
                "classes": ("collapse",),
                "fields": ("mail_to_admin", "via_form"),
            },
        ),
    )
    actions = [export_as_xls, import_from_csv]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(f"import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def response_change(self, request, obj):
        return HttpResponseRedirect("../../../event/%s/change" % obj.event.id)

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            event_id = request.POST["event"]
            print(f"event: {event_id}")

            # let's check if it is a csv file
            if not csv_file.name.endswith(".csv"):
                messages.error(request, "Keine CSV-Datei")

            data_set = csv_file.read().decode("UTF-8")
            # setup a stream which is when we loop through each line we are able to handle a data in a stream
            io_string = io.StringIO(data_set)
            next(io_string)

            bulk_create_list = []

            for row in csv.reader(io_string, delimiter=";"):
                # Here's how the row list looks like:
                # ['firstname', 'lastname', 'email']
                # username will be calculated when exported to moodle
                # preparing bulk crate
                bulk_create_list.append(
                    EventMember(
                        firstname=row[0],
                        lastname=row[1],
                        email=row[2],
                        event=Event.objects.get(id=event_id),
                    )
                )

                print(row[0])
                print(row[1])
                print(row[2])

            objs = EventMember.objects.bulk_create(bulk_create_list)
            self.message_user(request, "CSV-Datei wurde importiert")
            # EventMember
            return redirect("..")

        form = CsvImportForm()
        context = {
            "form": form,
            "message": "CSV-Datei MIT Kopfzeile, Bezeichnung und Reihenfolge der Spalten in der CSV-Datei: firstname; lastname; email",
        }
        return render(request, "admin/csv_form.html", context)


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
    fields = (
        "academic",
        "firstname",
        "lastname",
        "email",
        "attend_status",
        "vfll",
        "get_memberships_string",
        "check",
        "education_bonus",
        "get_registration_date",
        "change_link",
        "enroled",
        "moodle_id",
    )
    # inline_actions = ['enrol_to_moodle_course']
    readonly_fields = (
        "change_link",
        "get_registration_date",
        "get_memberships_string",
        "enroled",
        "attend_status",
        "moodle_id",
    )

    # def has_add_permission(self, request, obj=None):
    #    if obj and obj.is_past():
    #        return False
    #    return True

    # def get_short_attend_status(self, obj):
    #    if obj.attend_status:
    #        return obj.attend_status[0]
    #    return "-"

    # get_short_attend_status.short_description = "St"

    def change_link(self, obj):
        return mark_safe(
            '<a href="%s">Edit</a>'
            % reverse("admin:events_eventmember_change", args=(obj.id,))
        )

    change_link.short_description = "Edit"

    def get_inline_actions(self, request, obj=None):
        actions = super(EventMemberInline, self).get_inline_actions(request, obj)
        if obj and obj.attend_status == "registered":
            actions.append("change_attend_status_to_waiting")
        elif obj and obj.attend_status == "waiting":
            actions.append("change_attend_status_to_registered")

        if obj and obj.event.moodle_id > 0:
            if obj.enroled == False:
                actions.append("enrol_to_moodle_course")
            elif obj.enroled == True:
                actions.append("unenrol_from_moodle_course")
                actions.append("update_role_to_moodle_course")
        if obj and obj.enroled == False:
            actions.append("delete_user")
        return actions

    def enrol_to_moodle_course(self, request, obj, parent_obj=None):
        obj.enroled = True
        obj.roles.add(MemberRole.objects.get(roleid=5))
        obj.save()
        # get
        response = enrol_user_to_course(
            obj.email,
            obj.event.moodle_id,
            obj.event.moodle_new_user_flag,
            obj.event.moodle_standard_password,
            5,
            obj.firstname,
            obj.lastname,
        )  # 5: student
        if type(response) == dict:
            if "warnings" in response and response["warnings"]:
                messages.warning(request, response["warnings"])
            if "exception" in response or "errorcode" in response:
                messages.error(
                    request,
                    f"Teilnehmer*in konnte nicht eingeschrieben werden: {response.get('exception', '')}, {response.get('errorcode','')}, {response.get('message','')}",
                )
        else:
            messages.success(
                request, f"Teilnehmer*in wurde in den Moodle-Kurs eingeschrieben"
            )
        return True

    enrol_to_moodle_course.short_description = "T>M"

    def unenrol_from_moodle_course(self, request, obj, parent_obj=None):
        obj.enroled = False
        obj.save()
        unenrol_user_from_course(obj.moodle_id, obj.event.moodle_id)

    unenrol_from_moodle_course.short_description = "TxM"

    def update_role_to_moodle_course(self, request, obj, parent_obj=None):
        # list of role ids
        role_id_list = [item.roleid for item in obj.roles.all()]
        assign_roles_to_enroled_user(obj.event.moodle_id, obj.moodle_id, role_id_list)

    update_role_to_moodle_course.short_description = "UR"

    def delete_user(self, request, obj, parent_obj):
        obj.delete()

    delete_user.short_description = "DEL"

    def change_attend_status_to_waiting(self, request, obj, parent_obj):
        obj.attend_status = "waiting"
        obj.save()

    change_attend_status_to_waiting.short_description = ">W"

    def change_attend_status_to_registered(self, request, obj, parent_obj):
        obj.attend_status = "registered"
        obj.save()

    change_attend_status_to_registered.short_description = ">A"


class EventSpeakerThroughInline(admin.TabularInline):
    model = EventSpeakerThrough
    extra = 0


class EventSponsorThroughInline(admin.TabularInline):
    model = EventSponsorThrough
    extra = 0


class EventExternalSponsorThroughInline(admin.TabularInline):
    model = EventExternalSponsorThrough
    extra = 0


class EventSpeakerAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "email")
    ordering = (
        "last_name",
        "first_name",
    )
    search_fields = (
        "=last_name",
        "=first_name",
    )  # case insensitive searching
    readonly_fields = ("date_created", "date_modified")
    inlines = (EventSpeakerThroughInline,)
    fieldsets = (
        (
            "Name",
            {
                "fields": (
                    (
                        "first_name",
                        "last_name",
                    ),
                )
            },
        ),
        (
            "Kontakt",
            {
                "fields": (
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Über",
            {
                "fields": (
                    "bio",
                    (
                        "url",
                        "social_url",
                    ),
                    "image",
                )
            },
        ),
        (
            "Änderungen",
            {
                "fields": ("date_created", "date_modified"),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EventSpeaker, EventSpeakerAdmin)


class EventSponsorAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "email")
    ordering = (
        "last_name",
        "first_name",
    )
    search_fields = (
        "=last_name",
        "=first_name",
    )  # case insensitive searching
    readonly_fields = ("date_created", "date_modified")
    inlines = (EventSponsorThroughInline,)
    fieldsets = (
        (
            "Name",
            {
                "fields": (
                    (
                        "first_name",
                        "last_name",
                    ),
                )
            },
        ),
        (
            "Kontakt",
            {
                "fields": (
                    "email",
                    "phone",
                )
            },
        ),
        ("Über", {"fields": ("image",)}),
        (
            "Intern",
            {
                "fields": ("date_created", "date_modified"),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EventSponsor, EventSponsorAdmin)


class EventExternalSponsorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "url")
    ordering = ("name",)
    search_fields = (
        "=name",
        "=text",
    )  # case insensitive searching
    readonly_fields = ("date_created", "date_modified")
    inlines = (EventExternalSponsorThroughInline,)
    fieldsets = (
        (
            "Name, Beschreibung",
            {
                "fields": (
                    (
                        "name",
                        "text",
                    ),
                )
            },
        ),
        (
            "Kontakt",
            {
                "fields": (
                    "email",
                    "url",
                )
            },
        ),
        ("Bild", {"fields": ("image",)}),
        (
            "Intern",
            {
                "fields": ("date_created", "date_modified"),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EventExternalSponsor, EventExternalSponsorAdmin)

# generating link to event pdf
def admin_event_pdf(obj):
    return mark_safe(
        '<a href="{}">Pdf</a>'.format(reverse("admin-event-pdf", args=[obj.id]))
    )


admin_event_pdf.short_description = "Pdf"


# admin filter: per default only future events
class PeriodFilter(SimpleListFilter):
    """
    Filter the Events Happening in the Past and Future
    ref: https://stackoverflow.com/questions/851636/default-filter-in-django-admin
    """

    default_value = "future"
    title = "Zeitraum"
    parameter_name = "period"

    def lookups(self, request, model_admin):
        """
        List the Choices available for this filter.
        """
        return (
            ("all", "Alle"),
            ("future", "noch nicht gestartet"),
            ("past", "abgeschlossen"),
        )

    def choices(self, changelist):
        """
        Overwrite this method to prevent the default "All".
        """
        value = self.value() or self.default_value
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == force_text(lookup),
                "query_string": changelist.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        """
        Returns the Queryset depending on the Choice.
        """
        value = self.value() or self.default_value
        now = timezone.now()
        if value == "future":
            return queryset.filter(first_day__gte=now) | queryset.filter(first_day=None)
        if value == "past":
            return queryset.filter(first_day__lt=now)
        return queryset.all()


class EventAdmin(InlineActionsModelAdminMixin, admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<object_id>/hitcount/",
                self.admin_site.admin_view(self.schema),
                name="event_hitcount",
            )
        ]
        return my_urls + urls

    def schema(self, request, object_id):
        event = get_object_or_404(Event, id=int(object_id))
        return hitcount_view(request, self, event)

    change_list_template = "admin/event_change_list.html"
    change_form_template = "admin/event_change_form.html"

    list_display = (
        "name",
        "label",
        "registration_over",
        "get_start_date",
        "get_end_date",
        "view_members_link",
        "capacity",
        "eventformat",
        "category",
        "status",
        admin_event_pdf,
    )
    list_filter = (PeriodFilter, "eventformat", "category", "status")
    ordering = ("name",)
    search_fields = ("name",)
    readonly_fields = (
        "uuid",
        "slug",
        "moodle_id",
        "moodle_course_created",
        "date_created",
        "date_modified",
    )
    # readonly_fields = ('uuid', 'label', 'slug', 'date_created', 'date_modified')
    exclude = (
        "start_date",
        "end_date",
    )
    fieldsets = (
        (
            "Name, Kurztitel, Format",
            {"fields": ("name", "label", "category", "eventformat", "pub_status")},
        ),
        (
            "Inhaltliche Angaben",
            {
                "fields": (
                    "description",
                    "target_group",
                    "prerequisites",
                    "objectives",
                    "methods",
                )
            },
        ),
        (
            "Ort, Kosten, Dauer, Regio, Veranstalter",
            {
                "fields": (
                    "location",
                    "duration",
                    "regio_group",
                    "organizer",
                    "fees",
                    "catering",
                    "lodging",
                    "total_costs",
                )
            },
        ),
        (
            "Kapazität, Anmeldung, Hinweise, Freitextfeld, Status",
            {
                "fields": (
                    "capacity",
                    "registration_form",
                    "registration",
                    "registration_possible",
                    "registration_recipient",
                    "close_date",
                    "status",
                    "free_text_field_intro",
                    "notes",
                )
            },
        ),
        (
            "Video",
            {
                "fields": (
                    "video",
                    "show_video",
                    "video_comment",
                )
            },
        ),
        (
            "Programm als Pdf",
            {"fields": ("pdf_file",)},
        ),
        (
            "Moodle",
            {
                "fields": (
                    "moodle_course_type",
                    "moodle_id",
                    "moodle_course_created",
                    "moodle_new_user_flag",
                    "moodle_standard_password",
                ),
            },
        ),
        (
            "Intern",
            {
                "fields": ("slug", "uuid", "date_created", "date_modified"),
                "classes": ("collapse",),
            },
        ),
    )
    inlines = (
        EventDayInline,
        EventSpeakerThroughInline,
        EventSponsorThroughInline,
        EventExternalSponsorThroughInline,
        EventAgendaInline,
        EventImageInline,
        EventDocumentInline,
        EventMemberInline,
    )
    actions = ("copy_event",)
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

    get_start_date.admin_order_field = "_start_date_min"
    get_start_date.short_description = "Beginn"

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

    get_end_date.admin_order_field = "_start_date_max"
    get_end_date.short_description = "Ende"

    def view_members_link(self, obj):
        count = obj.get_number_of_members()
        url = (
            reverse("admin:events_eventmember_changelist")
            + "?"
            + urlencode({"event__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{}</a>', url, count)

    view_members_link.short_description = "Teilnehmer*innen"

    def get_inline_actions(self, request, obj=None):
        actions = super(EventAdmin, self).get_inline_actions(request, obj)
        if obj.moodle_id == 0 and obj.category.name == "Onlineseminare":
            actions.append("create_course_in_moodle")
        if (
            not obj.moodle_id == 0
            and obj.category.name == "Onlineseminare"
            and not obj.members.exists()
        ):
            actions.append("delete_course_in_moodle")
        return actions

    def create_course_in_moodle(self, request, obj, parent_obj=None):
        # obj.save()
        category = (
            obj.moodle_course_type
        )  # wird in defaultmäßig als Fortbildung angelegt
        if not obj.get_first_day():
            self.message_user(
                request,
                "Kurs hat kein Startdatum und kann nicht angelegt werden",
                messages.ERROR,
            )
            return None
        else:
            # check, which speakers have no email address
            speakers = obj.speaker.all()
            for speaker in speakers:
                if speaker.last_name and not speaker.email:
                    self.message_user(
                        request,
                        f"Dozent*in {speaker.last_name} hat keine E-Mail-Adresse und wird deshalb dem Kurs in Moodle nicht zugeordnet",
                        messages.WARNING,
                    )
            response = create_moodle_course(
                obj.name,
                obj.label,
                obj.description,
                obj.moodle_new_user_flag,
                obj.moodle_standard_password,
                category,
                speakers,
                obj.get_first_day(),
                obj.get_last_day(),
            )
        if type(response) == dict:
            if "warnings" in response and response["warnings"]:
                self.message_user(request, response["warnings"], messages.WARNING)
            if "exception" in response or "errorcode" in response:
                self.message_user(
                    request,
                    f"Moodle-Kurs konnte nicht angelegt werden: {response.get('exception', '')}, {response.get('errorcode','')}, {response.get('message','')}",
                    messages.ERROR,
                )
        else:
            new_course_id = response[0].get("id", 0)  # moodle id of the new course
            obj.moodle_id = new_course_id
            obj.moodle_course_created = True
            obj.save()
            self.message_user(
                request,
                f"neuer Moodle-Kurs mit ID {new_course_id} angelegt",
                messages.SUCCESS,
            )

    create_course_in_moodle.short_description = ">M"

    def delete_course_in_moodle(self, request, obj, parent_obj=None):
        if obj.moodle_id == 0:
            self.message_user(
                request,
                "Kurs ist kein Moodle-Kurs und kann nicht gelöscht werden",
                messages.ERROR,
            )
            return None
        elif obj.members.exists():
            self.message_user(
                request,
                "Kurs hat Teilnehmer und kann nicht gelöscht werden",
                messages.ERROR,
            )
            return None
        else:
            response = delete_moodle_course(obj.moodle_id)

        if type(response) == dict:
            print(response)
            if "warnings" in response and not response["warnings"]:
                self.message_user(
                    request,
                    f"Moodle-Kurs mit ID {obj.moodle_id} wurde gelöscht, im EventManager ist er aber weiterhin vorhanden.",
                    messages.SUCCESS,
                )
                obj.moodle_id = 0
                obj.moodle_course_created = False
                obj.save()
            if "exception" in response or "errorcode" in response:
                self.message_user(
                    request,
                    f"Moodle-Kurs konnte nicht gelöscht werden: {response.get('exception', '')}, {response.get('errorcode','')}, {response.get('message','')}",
                    messages.ERROR,
                )
        else:
            return None

    delete_course_in_moodle.short_description = "xM"

    def copy_event(self, request, queryset):
        # TODO: handling of fk's , ref: https://stackoverflow.com/questions/32234986/duplicate-django-model-instance-and-all-foreign-keys-pointing-to-it
        for event in queryset:
            # fk's to copy
            old_agendas = event.agendas.all()
            # m2m to copy
            old_speakers = event.speaker.all()
            # alter Name
            old_name = event.name
            new_name = "Kopie von " + old_name
            event.name = new_name
            event.pk = None
            event.slug = None
            event.label = None
            event.moodle_id = 0
            event.moodle_course_created = False
            event.moodle_new_user_flag = False
            event.students_number = 0

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

    def save_model(self, request, obj, form, change):
        print("save_model called")
        # pass
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        print("save_related called")
        form.save_m2m()
        for formset in formsets:
            # print(formset)
            self.save_formset(request, form, formset, change=change)
        # super().save_related(request, form, formsets, change)
        super(EventAdmin, self).save_model(request, form.instance, form, change)


admin.site.register(EventCategory, EventCategoryAdmin)
admin.site.register(EventFormat)
admin.site.register(Event, EventAdmin)


class EventLocationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "city",
    )
    list_filter = ("city",)
    ordering = ("city", "title")
    readonly_fields = ("date_created", "date_modified")
    fieldsets = (
        (
            "Details",
            {
                "fields": (
                    "title",
                    "url",
                )
            },
        ),
        (
            "Adresse",
            {
                "fields": (
                    "address_line",
                    "street",
                    "city",
                    "postcode",
                    "state",
                )
            },
        ),
        (
            "Änderungen",
            {
                "fields": ("date_created", "date_modified"),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EventLocation, EventLocationAdmin)


class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = ("name", "contact", "url")


admin.site.register(EventOrganizer, EventOrganizerAdmin)


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "text_template", "counter")
    ordering = ("name",)
    search_fields = ("=name",)
    readonly_fields = ("date_created", "date_modified", "counter")
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": ("name", "counter"),
            },
        ),
        (
            "Templates",
            {
                "fields": (
                    "text_template",
                    "html_template",
                ),
            },
        ),
        (
            "Änderungen",
            {
                "fields": (
                    "date_created",
                    "date_modified",
                ),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EmailTemplate, EmailTemplateAdmin)


class EventHighlightAdmin(admin.ModelAdmin):
    model = EventHighlight


admin.site.register(EventHighlight, EventHighlightAdmin)

from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.utils.html import escape
from django.urls import reverse
from django.utils.safestring import mark_safe


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "action_time"

    list_filter = ["user", "content_type", "action_flag"]

    search_fields = ["object_repr", "change_message"]

    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_link",
        "action_flag",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = '<a href="%s">%s</a>' % (
                reverse(
                    "admin:%s_%s_change" % (ct.app_label, ct.model),
                    args=[obj.object_id],
                ),
                escape(obj.object_repr),
            )
        return mark_safe(link)

    object_link.admin_order_field = "object_repr"
    object_link.short_description = "object"
