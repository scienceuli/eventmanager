import markdown
import io, csv
from datetime import date, datetime

from django.contrib import admin, messages
from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.utils.http import urlencode
from django.utils.html import format_html
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, path
from django import forms
from django.db.models import Min, Max, Q, Sum

from django.forms.models import BaseInlineFormSet
from django.forms import inlineformset_factory

from django.contrib.admin.models import LogEntry

from django.contrib.admin import SimpleListFilter

from mapbox_location_field.admin import MapAdmin
from admin_export_action.admin import export_selected_objects

# for inline actions, from 3rd party module
from inline_actions.admin import InlineActionsMixin
from inline_actions.admin import InlineActionsModelAdminMixin

from fieldsets_with_inlines import FieldsetsInlineMixin

from .actions import (
    export_as_xls,
    import_from_csv,
    copy_member_instances,
    export_members_to_csv,
)

from .validators import csv_content_validator

from .models import (
    Home,
    PayLessAction,
    EventCategory,
    EventFormat,
    EventCollection,
    Event,
    EventDay,
    EventHighlight,
    EventImage,
    EventDocument,
    PrivateDocument,
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
    EventMemberChangeDate,
    EventMemberRole,
    MemberRole,
    EventHighlight,
)

from .event_q_and_a import EventQuestion

from events.filter import PeriodFilter, DateRangeFilter

from shop.models import Order, OrderItem

from payment.utils import update_order, check_order_date_in_future
from payment.views import get_payment_date
from events.utils import send_email

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


class MyAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        app_list += [
            {
                "name": "My Custom App",
                "app_label": "my_test_app",
                # "app_url": "/admin/test_view",
                "models": [
                    {
                        "name": "tcptraceroute",
                        "object_name": "tcptraceroute",
                        "admin_url": "/admin/test_view",
                        "view_only": True,
                    }
                ],
            }
        ]
        return app_list


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

    list_display = [
        "name",
        "title",
        "description",
        "singular",
        "position",
        "show",
        "registration",
    ]

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


class PayLessActionForm(forms.ModelForm):
    """Form is needed to select existing Events to PayLessAction,
    because standard inline is for creating new events but not
    for selecting exiting events
    ref: https://stackoverflow.com/questions/6034047/one-to-many-inline-select-with-django-admin
    """

    # events = forms.ModelMultipleChoiceField(
    #     queryset=Event.objects.filter(first_day__gte=date.today())
    #     .filter(pub_status="PUB")
    #     .exclude(event_days=None)
    #     .order_by("name"),
    #     widget=forms.CheckboxSelectMultiple,
    #     required=True,
    # )
    events = forms.ModelMultipleChoiceField(
        queryset=Event.objects.none(),  # We'll define this queryset in the __init__ method
        widget=forms.CheckboxSelectMultiple,
        required=True,  # Make it optional
    )
    name = forms.CharField(max_length=255)
    title = forms.Textarea()
    type = forms.ChoiceField(choices=PayLessAction.TYPE_CHOICES)
    percents = forms.IntegerField(required=False, label="Prozentsatz")

    price_premium = forms.DecimalField(
        max_digits=10, decimal_places=2, label="normaler Preis", required=False
    )
    price_members = forms.DecimalField(
        max_digits=10, decimal_places=2, label="Mitgliederpreis", required=False
    )

    class Meta:
        model = PayLessAction
        fields = [
            "events",
            "title",
            "name",
            "type",
            "percents",
            "price_premium",
            "price_members",
        ]

    def __init__(self, *args, **kwargs):
        super(PayLessActionForm, self).__init__(*args, **kwargs)
        current_time = date.today()

        if self.instance and self.instance.pk:  # Editing an existing instance
            # Get events related to this PayLessAction (past and future) + all future events
            self.fields["events"].queryset = (
                Event.objects.filter(
                    (Q(first_day__gte=current_time) & Q(pub_status="PUB"))
                    | Q(payless_collection=self.instance)
                )
                .exclude(event_days=None)
                .order_by("name")
            )
            # Pre-select events already assigned to this PayLessCollection
            pay_less_events = self.instance.events.all()
            self.fields["events"].initial = pay_less_events
            events_with_collection = pay_less_events.filter(
                event_collection__isnull=False
            )
            collection_events = []
            if events_with_collection:
                collection_events = list(
                    events_with_collection[0]
                    .event_collection.events.all()
                    .values_list("name", flat=True)
                )
                help_text = (
                    f"Bitte folgende Veranstaltungen wählen: {collection_events}"
                )
            else:
                help_text = "Bitte alle Veranstaltungen wählen, die zu einer Event Collection gehören"

            self.fields["events"].help_text = help_text

        else:  # Creating a new instance
            # Show only future events
            self.fields["events"].queryset = (
                Event.objects.filter(
                    (Q(first_day__gte=current_time) & Q(pub_status="PUB"))
                )
                .exclude(event_days=None)
                .order_by("name")
            )

        # if self.instance and self.instance.pk:
        #     pay_less_events = self.instance.events.all()
        #     events_with_collection = pay_less_events.filter(
        #         event_collection__isnull=False
        #     )
        #     collection_events = []
        #     if events_with_collection:
        #         collection_events = list(
        #             events_with_collection[0]
        #             .event_collection.events.all()
        #             .values_list("name", flat=True)
        #         )
        #         help_text = (
        #             f"Bitte folgende Veranstaltungen wählen: {collection_events}"
        #         )
        #     else:
        #         help_text = "Bitte alle Veranstaltungen wählen, die zu einer Event Collection gehören"

        #     self.fields["events"].help_text = help_text

    def save_m2m(self):
        pass

    def clean(self):
        events = self.cleaned_data["events"]
        # take first event and get its event collection
        events_with_collection = events.filter(event_collection__isnull=False)
        collection_events = []
        if events_with_collection:
            collection_events = (
                events_with_collection.first().event_collection.events.all()
            )
        # the events of this event collection must be the same as events of payless collection
        if set(events) != set(collection_events):
            raise forms.ValidationError(
                "Die Event Collection umfasst nicht die selben Veranstaltungen wie die Payless Collection"
            )
        return self.cleaned_data

    # def save(self, *args, **kwargs):
    #     # import pdb

    #     # pdb.set_trace()
    #     self.fields["events"].initial.update(payless_collection=None)
    #     payless_collection_instance = PayLessAction()
    #     payless_collection_instance.pk = self.instance.pk
    #     payless_collection_instance.name = self.instance.name
    #     payless_collection_instance.title = self.instance.title
    #     payless_collection_instance.type = self.instance.type
    #     payless_collection_instance.percents = self.instance.percents
    #     payless_collection_instance.price_premium = self.instance.price_premium
    #     payless_collection_instance.price_members = self.instance.price_members
    #     payless_collection_instance.save()
    #     self.cleaned_data["events"].update(
    #         payless_collection=payless_collection_instance
    #     )
    #     return payless_collection_instance


class PayLessActionAdmin(admin.ModelAdmin):
    model = PayLessAction
    list_display = (
        "name",
        "type",
        "percents",
        "price_premium",
        "price_members",
        "events_display",
    )
    form = PayLessActionForm

    def events_display(self, obj):
        return ", ".join([ev.name for ev in obj.events.all()])

    events_display.short_description = "Veranstaltungen"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Save the selected events to the PayLessAction instance
        form.instance.events.set(form.cleaned_data["events"])


admin.site.register(PayLessAction, PayLessActionAdmin)


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
    verbose_name = "öffentliches Dokument"
    verbose_name_plural = "öffentliche Dokumente"


class PrivateDocumentInline(admin.StackedInline):
    model = PrivateDocument
    extra = 0
    verbose_name = "nicht-öffentliches Dokument"
    verbose_name_plural = "nicht-öffentliche Dokumente"


class EventAgendaInline(admin.StackedInline):
    model = EventAgenda
    extra = 0
    verbose_name = "Programm"
    verbose_name_plural = "Programme"


class EventDayAdmin(admin.ModelAdmin):
    list_display = ["start_date", "start_time", "end_time"]


admin.register(EventDay, EventDayAdmin)

class EventQuestionInline(admin.StackedInline):
    model = EventQuestion
    extra = 0
    verbose_name = "Zusatzinfo"
    verbose_name_plural = "Zusatzinfos"


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
        "vfll",
        "memberships",
        "event",
        "date_created",
        "via_form",
        "mail_to_admin",
        "get_order_nr",
    ]
    list_filter = [
        "event",
    ]
    search_fields = ("lastname", "firstname", "email", "event__name")
    readonly_fields = ["name", "label", "mail_to_admin", "via_form"]
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
                    "member_type",
                    "memberships",
                    "agree",
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
                "fields": ("mail_to_admin", "via_form", "label"),
            },
        ),
    )
    actions = [
        export_as_xls,
        export_members_to_csv,
        export_selected_objects,
        import_from_csv,
        copy_member_instances,
    ]

    @admin.display(description="RechNr")
    def get_order_nr(self, obj):
        order = (
            Order.objects.filter(
                email=obj.email,
                items__event=obj.event,  # Join through OrderItem to match the event
            )
            .distinct()
            .first()
        )  # Use distinct() to avoid duplicates

        return order.get_order_number if order else ""

    @admin.display(description="Betrag")
    def get_order_price(self, obj):
        # update order
        order = (
            Order.objects.filter(
                email=obj.email,
                items__event=obj.event,  # Join through OrderItem to match the event
            )
            .distinct()
            .first()
        )
        if check_order_date_in_future(order):
            update_order(order)

        order_item = OrderItem.objects.filter(
            event=obj.event, order__email=obj.email
        ).first()

        return order_item.get_cost_property if order_item else ""

    @admin.display(description="Zahlungseingang")
    def get_payment_receipt(self, obj):
        order = (
            Order.objects.filter(
                email=obj.email,
                items__event=obj.event,  # Join through OrderItem to match the event
            )
            .distinct()
            .first()
        )  # Use distinct() to avoid duplicates

        return (
            datetime.strftime(order.payment_date, "%d.%m.%Y")
            if order.payment_receipt
            else ""
        )

    def get_memberships_boolean(self, obj):
        if obj.vfll or obj.memberships != "[]":
            return True
        return False

    get_memberships_boolean.short_description = "Mitglied"

    def get_no_memberships_boolean(self, obj):
        if not obj.vfll and obj.memberships == "[]":
            return True
        return False

    get_no_memberships_boolean.short_description = "Nicht-Mitglied"

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
        "agree",
        "education_bonus",
        "get_registration_date",
        "total_cost",
        "change_link",
        # "enroled",
        # "moodle_id",
    )
    # inline_actions = ['enrol_to_moodle_course']
    readonly_fields = (
        "total_cost",
        "change_link",
        "get_registration_date",
        "get_memberships_string",
        "enroled",
        "attend_status",
        # "moodle_id",
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

    def total_cost(self, obj):
        if obj.attend_status == "registered":
            total = OrderItem.objects.filter(
                order__email=obj.email,
                event=obj.event,
            ).aggregate(total=Sum("cost"))["total"]
        else:
            total = 0

        return total or 0  # Return 0 if None

    total_cost.short_description = "Betrag"

    def change_link(self, obj):
        return mark_safe(
            '<a href="%s">Edit</a>'
            % reverse("admin:events_eventmember_change", args=(obj.id,))
        )

    change_link.short_description = "Edit"

    def get_inline_actions(self, request, obj=None):
        actions = super(EventMemberInline, self).get_inline_actions(request, obj)
        if obj and obj.attend_status == "registered":
            actions.append("change_attend_status_to_cancelled")
            actions.append("change_attend_status_to_waiting")
        elif obj and obj.attend_status == "waiting":
            actions.append("change_attend_status_to_registered")

        if obj and obj.event.moodle_id > 0:
            if obj.enroled == False:
                actions.append("enrol_to_moodle_course")
            elif obj.enroled == True:
                actions.append("unenrol_from_moodle_course")
                actions.append("update_role_to_moodle_course")
        # if obj and obj.enroled == False:
        #    actions.append("delete_user")
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

    def change_attend_status_to_cancelled(self, request, obj, parent_obj):
        old_status = obj.attend_status
        obj.attend_status = "cancelled"
        messages.success(request, f"Teilnahme wurde storniert")

        action = f"Status von {old_status} zu cancelled geändert"
        change_date = EventMemberChangeDate.objects.create(
            change_date=datetime.now(), action=action, event_member=obj
        )
        obj.save()
        event = obj.event
        try:
            order_item = OrderItem.objects.get(event=event, order__email=obj.email)
            order = order_item.order
            if check_order_date_in_future(order):
                order_updated = update_order(order)
            order.storno = True
            order.save()
            if order_updated:
                messages.success(
                    request, "Rechnung wurde geändert (da noch nicht verschickt)"
                )
            else:
                messages.info(
                    request,
                    "Rechnung liegt in Vergangenheit und wurde nicht geändert, bitte individuell klären",
                )
            messages.success(
                request,
                f"Storno-Vermerk für Rechnung wurde hinzugefügt (Achtung: Evtl. bleiben andere Rechnungsposten weiterhin gültig)",
            )

        except:
            messages.error(request, f"keine zugehörige Rechnung gefunden")

    change_attend_status_to_cancelled.short_description = ">S"

    def change_attend_status_to_registered(self, request, obj, parent_obj):
        obj.attend_status = "registered"
        obj.save()
        messages.success(request, "Teilnahmestatus wurde auf angemeldet gesetzt")

        event = obj.event
        # print(
        #     OrderItem.objects.filter(
        #         event=event,
        #         order__email=obj.email,
        #     ).exists()
        # )
        if not OrderItem.objects.filter(
            event=event,
            order__email=obj.email,
        ).exists():
            order = Order.objects.create(
                academic=obj.academic,
                firstname=obj.firstname,
                lastname=obj.lastname,
                address_line=obj.address_line,
                company=obj.company,
                street=obj.street,
                city=obj.city,
                state=obj.state,
                postcode=obj.postcode,
                email=obj.email,
                phone=obj.phone,
                discounted=obj.vfll or (len(obj.memberships) > 0),
                payment_type="r",
            )
            order_item = OrderItem.objects.create(
                order=order,
                event=event,
                price=event.price,
                premium_price=event.premium_price,
                quantity=1,
            )

            order.payment_date = get_payment_date(order)
            order.save()
            messages.success(request, "Rechnung wurde angelegt")

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


class EventCollectionAdmin(admin.ModelAdmin):
    model = EventCollection


admin.site.register(EventCollection, EventCollectionAdmin)


def clean_unique(
    form,
    field,
    exclude_initial=True,
    format="%(value)s wurde für  %(field)s bereits genutzt.",
):
    value = form.cleaned_data.get(field)
    if value:
        qs = form._meta.model._default_manager.filter(**{field: value})
        if exclude_initial and form.initial:
            initial_value = form.initial.get(field)
            qs = qs.exclude(**{field: initial_value})
        if qs.count() > 0:
            field_verbose = form._meta.model._meta.get_field(field).verbose_name
            raise forms.ValidationError(
                format % {"field": field_verbose, "value": value}
            )
    return value


class EventForm(forms.ModelForm):
    def clean(self):
        payless_collection = self.cleaned_data.get("payless_collection")
        event_collection = self.cleaned_data.get("event_collection")
        direct_payment = self.cleaned_data.get("direct_payment")
        if payless_collection and not event_collection:
            raise forms.ValidationError(
                {
                    "event_collection": "Eine Veranstaltung kann nicht zur einer Payless Collection gehören ohne eine Event Collection."
                }
            )
        if payless_collection and not direct_payment:
            raise forms.ValidationError(
                {
                    "direct_payment": "Für eine Veranstaltung mit Payless-Aktion muss die Warenkorb-Funktion geschaltet sein."
                }
            )

    def clean_label(self):
        return clean_unique(self, "label")


class EventAdmin(InlineActionsModelAdminMixin, admin.ModelAdmin):
    form = EventForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            kwargs["queryset"] = EventCategory.shown_event_categories.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super(EventAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["event_collection"].widget.can_delete_related = False
        form.base_fields["payless_collection"].widget.can_delete_related = False
        return form

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<object_id>/hitcount/",
                self.admin_site.admin_view(self.schema),
                name="event_hitcount",
            ),
            path(
                "confirm_test_intermediate/<int:pk>/",
                self.admin_site.admin_view(self.confirm_test_intermediate_action_view),
                name="confirm-test-intermediate",
            ),
            path(
                "confirm_cancel_event/<int:pk>/",
                self.admin_site.admin_view(self.confirm_cancel_event),
                name="confirm-cancel-event",
            ),
        ]
        return my_urls + urls

    def schema(self, request, object_id):
        event = get_object_or_404(Event, id=int(object_id))
        return hitcount_view(request, self, event)

    change_list_template = "admin/event_change_list.html"
    change_form_template = "admin/event_change_form.html"

    list_display = (
        "name_with_status",
        "label",
        "registration_over",
        "get_start_date",
        "get_end_date",
        "price",
        "get_balance_colored",
        "direct_payment",
        "view_members_link",
        "capacity",
        "eventformat",
        "category",
        "status",
        admin_event_pdf,
    )
    list_filter = (
        PeriodFilter,
        "eventformat",
        "category",
        "status",
        "start_date",
        ("first_day", DateRangeFilter),
    )
    filter_horizontal = ("visible_to_groups",)
    ordering = ("name",)
    search_fields = ("name",)
    readonly_fields = (
        "status",
        "full_price",
        "uuid",
        "slug",
        "moodle_id",
        "moodle_course_created",
        "date_created",
        "date_modified",
        "answers_summary_link",
    )
    # readonly_fields = ('uuid', 'label', 'slug', 'date_created', 'date_modified')

    exclude = (
        "start_date",
        "end_date",
    )
    fieldsets = (
        (
            "Name, Kurztitel, Format, Status, Editierbarkeit, SEO",
            {
                "fields": (
                    "name",
                    "label",
                    "category",
                    "eventformat",
                    "status",
                    "pub_status",
                    "edit_in_frontend",
                    "visible_to_groups",
                    "show_in_all_events",
                    "show_date",
                    "keywords",
                    "meta_description",
                )
            },
        ),
        (
            "Übergeordnete Veranstaltung, Bezahlung",
            {
                "fields": (
                    "event_collection",
                    "direct_payment",
                    "price",
                    "full_price",
                    "costs",
                )
            },
        ),
        (
            "PayLess-Aktion",
            {
                "fields": (
                    "payless_collection",
                    "oneliner",
                )
            },
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
                    # "total_costs",
                )
            },
        ),
        (
            "Kapazität, Anmeldung, Hinweise, Freitextfeld, Status",
            {
                "fields": (
                    "vfll_only",
                    "capacity",
                    "registration_form",
                    "registration",
                    "registration_possible",
                    # "registration_message",
                    "registration_recipient",
                    "open_date",
                    "close_date",
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
        # (
        #     "Moodle",
        #     {
        #         "fields": (
        #             "moodle_course_type",
        #             "moodle_id",
        #             "moodle_course_created",
        #             "moodle_new_user_flag",
        #             "moodle_standard_password",
        #         ),
        #     },
        # ),
        (
            "Zusatzinfos",
            {
                "fields": ("answers_summary_link",),
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

    def answers_summary_link(self, obj):
        if obj.questions.exists():
            url = reverse('admin-event-answers-summary', args=[obj.id])
            return format_html(
                '<a class="button" href="{}" target="_blank">Antworten</a>', url
            )
        return "Keine Fragen"
    answers_summary_link.short_description = "Alle Antworten"

    def get_balance_colored(self, obj):
        if obj.get_balance() == 0:
            balance = "-"
            color = "gray"
        else:
            balance = obj.get_balance()
            color = "red" if obj.get_balance() < 0 else "green"
        return format_html('<span style="color: {};">{}</span>', color, balance)

    get_balance_colored.admin_order_field = "get_balance"
    get_balance_colored.short_description = "Marge"

    def name_with_status(self, obj):
        if obj.status == "cancel":
            return f"{obj.name} ABGESAGT"
        return obj.name

    def full_price(self, obj):
        if obj.price:
            return format_html(
                "<div class='c-2'>{}<br><p class='grp-help'>{}</p></div>",
                obj.premium_price,
                "Berechnetes Feld. Unreduzierter Preis für Nicht-Mitglieder, der in der Ausschreibung angezeigt wird. Dieser Preis muss mit der Preisangabe im entsprechenden Textfeld übereinstimmen.",
            )
        return format_html(
            "<div class='c-2'>{}<br><p class='grp-help'>{}</p></div>",
            "-",
            "Berechnetes Feld. Unreduzierter Preis für Nicht-Mitglieder, der in der Ausschreibung angezeigt wird. Dieser Preis muss mit der Preisangabe im entsprechenden Textfeld übereinstimmen.",
        )

    full_price.short_description = "Voller Preis"

    inlines = (
        EventQuestionInline,
        EventDayInline,
        EventSpeakerThroughInline,
        EventSponsorThroughInline,
        EventExternalSponsorThroughInline,
        EventAgendaInline,
        EventImageInline,
        EventDocumentInline,
        PrivateDocumentInline,
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
        # actions.append("test_intermediate")
        if obj and obj.status != "cancel" and not obj.is_past():
            actions.append("cancel_event")
        if obj and obj.status == "cancel" and not obj.is_past():
            actions.append("reactivate_event")
        # if obj.moodle_id == 0 and obj.eventformat.moodle:
        #     actions.append("create_course_in_moodle")
        # if (
        #     not obj.moodle_id == 0
        #     and obj.category.name == "Onlineseminare"
        #     and not obj.members.exists()
        # ):
        #     actions.append("delete_course_in_moodle")
        return actions

    def test_intermediate(self, request, obj, parent_obj=None):
        return redirect("admin:confirm-test-intermediate", obj.pk)

    test_intermediate.short_description = "T"

    def confirm_test_intermediate_action_view(self, request, pk):
        event = Event.objects.get(pk=pk)
        event_list_url = reverse(
            "admin:%s_%s_changelist" % (event._meta.app_label, event._meta.model_name),
        )
        if request.method == "POST":
            self.message_user(request, "Intermediate Test successfully")
            return HttpResponseRedirect(event_list_url)

        context = {"event": Event.objects.get(pk=pk), "cancel_url": event_list_url}
        return TemplateResponse(
            request, "admin/confirm_test_intermediate.html", context
        )

    def cancel_event(self, request, obj, parent_obj=None):
        return redirect("admin:confirm-cancel-event", obj.pk)

    def get_cancel_event_label(self, obj):
        return ">C"

    def get_cancel_event_css(self, obj):
        return "grp-button grp-cancel-link"

    def confirm_cancel_event(self, request, pk):
        obj = Event.objects.get(pk=pk)
        event_list_url = reverse(
            "admin:%s_%s_changelist" % (obj._meta.app_label, obj._meta.model_name),
        )

        if request.method == "POST":
            obj.status = "cancel"
            obj.save()
            for member in obj.members.all():
                old_status = member.attend_status
                member.attend_status = "cancelled"

                action = f"Status von {old_status} zu cancelled geändert"
                EventMemberChangeDate.objects.create(
                    change_date=datetime.now(), action=action, event_member=member
                )
                member.save()
                order_items = OrderItem.objects.filter(
                    event=obj, order__email=member.email
                ).exclude(status="s")
                counter = 0
                for order_item in order_items:
                    order = order_item.order
                    if check_order_date_in_future(order):
                        order_updated = update_order(order)
                    order.storno = True
                    order.save()
                    counter += 1
                if counter == 0:
                    self.message_user(
                        request,
                        f"keine Rechnung für {member} gefunden",
                        messages.ERROR,
                    )
                elif counter > 1:
                    self.message_user(
                        request,
                        f"mehrere Rechnungen für {member} gefunden",
                        messages.ERROR,
                    )
            self.message_user(
                request,
                f"Veranstaltung {obj.name} wurde storniert",
                messages.SUCCESS,
            )
            return HttpResponseRedirect(event_list_url)

        member_list = []
        for member in obj.members.all():
            member_dict = {}
            member_dict["name"] = f"{member.lastname}, {member.firstname}"
            member_dict["email"] = member.email
            order_item = OrderItem.objects.filter(
                event=obj, order__email=member.email
            ).exclude(status="s")

            if len(order_item) == 0:
                self.message_user(
                    request,
                    f"Die Veranstaltung {obj.name} taucht auf keiner Rechnung von {member.lastname}, {member.firstname} auf, bitte bereinigen.",
                    messages.ERROR,
                )
            elif len(order_item) > 1:
                self.message_user(
                    request,
                    f"Die Veranstaltung {obj.name} taucht auf mehreren Rechnungen von {member.lastname}, {member.firstname} auf, bitte bereinigen.",
                    messages.ERROR,
                )
            else:
                order = order_item[0].order
                member_dict["order"] = order
                member_list.append(member_dict)

        context = {"event": obj, "members": member_list, "cancel_url": event_list_url}
        return TemplateResponse(request, "admin/confirm_cancel_event.html", context)

    # cancel_event.short_description = "C"

    def reactivate_event(self, request, obj, parent_obj=None):
        obj.status = "active"
        obj.save()
        event_list_url = reverse(
            "admin:%s_%s_changelist" % (obj._meta.app_label, obj._meta.model_name),
        )
        return HttpResponseRedirect(event_list_url)

    def get_reactivate_event_label(self, obj):
        return ">A"

    def get_reactivate_event_css(self, obj):
        return "grp-button grp-reactivate-link"

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
        # with this
        if settings.COPY_ONLY_ALLOWED_FOR_SINGLE_OBJECT and queryset.count() != 1:
            self.message_user(
                request, "Bitte nur ein Objekt zum Kopieren auswählen.", level="error"
            )
            return

        for event in queryset:
            # fk's to copy
            old_agendas = event.agendas.all()
            print("old_agendas", old_agendas)
            # import pdb

            # pdb.set_trace()
            # m2m to copy
            old_speakers = event.speaker.all()
            # alter Name
            old_name = event.name
            new_name = "Kopie von " + old_name
            event.name = new_name
            event.pk = None
            event.uuid = None
            event.slug = None
            event.label = None
            # set collections to none
            event.event_collection = None
            event.payless_collection = None
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
                new_fk = fk
                new_fk.pk = None
                new_fk.event = event
                new_fk.save()
                # try:
                #     # Use fk.__class__ here to avoid hard-coding the class name
                #     new_agendas[fk.__class__].append(fk)
                # except KeyError:
                #     new_agendas[fk.__class__] = [fk]

            # Now we can issue just two calls to bulk_create,
            # one for fkeys_a and one for fkeys_b
            # for cls, list_of_fks in new_agendas.items():
            #     cls.objects.bulk_create(list_of_fks)

            # go to new object if only one was copied
            # Get the URL of the new object and redirect to it
            if queryset.count() == 1:
                new_object_url = reverse(
                    "admin:%s_%s_change"
                    % (event._meta.app_label, event._meta.model_name),
                    args=[event.pk],
                )
                return HttpResponseRedirect(new_object_url)

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
        return request.user.is_superuser and request.user.username == "scienceuli"

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
