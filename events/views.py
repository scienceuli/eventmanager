import os
import csv
import json
import ast
from datetime import date, datetime
import pandas as pd
from decimal import Decimal
from itertools import chain

from openpyxl import Workbook
from .export_excel import ExportExcelAction
from openpyxl.styles import Font
from unidecode import unidecode

import markdown

from django.db import transaction
from django.db.models import Max, Q, Sum, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import request, HttpResponse, Http404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse_lazy, reverse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from django.contrib.auth.models import User, Group

from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth.mixins import UserPassesTestMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied

from django.contrib.auth.decorators import login_required, user_passes_test

from django.conf import settings

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
    FormView,
)

from hitcount.views import HitCountDetailView

from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalUpdateView,
    BSModalReadView,
    BSModalDeleteView,
    BSModalFormView,
)

from django_tables2 import SingleTableView

from meta.views import Meta

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response

from events.filter import EventFilter
from events.actions import style_output_file, convert_boolean_field
from events.decorators import check_user_able_to_see_page

from events.utils import (
    send_email_after_registration,
    boolean_translate,
    yes_no_to_boolean,
    make_bar_plot_from_dict,
    get_utilisations,
    update_boolean_values,
    convert_data_date,
    convert_boolean_field,
    no_duplicate_check,
    convert_html_to_text,
    remove_linebreaks,
)

# logging
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

logging.basicConfig(filename="eventmanager.log", encoding="utf-8", level=logging.ERROR)

from .models import (
    Home,
    EventCategory,
    EventCollection,
    Event,
    EventLocation,
    EventOrganizer,
    EventImage,
    EventMember,
    EventHighlight,
    EventSponsor,
)

from shop.models import OrderItem

from .tables import EventMembersTable, FTEventMembersTable, MVEventMembersTable

from .forms import (
    EventDayFormSet,
    EventLocationModelForm,
    EventLocationNMModelForm,
    EventOrganizerModelForm,
    EventOrganizerNMModelForm,
    EventModelForm,
    EventMemberForm,
    EventDocumentFormSet,
    Symposium2022Form,
    Symposium2024Form,
    SymposiumForm,
    MV2023Form,
    AddMemberForm,
    MemberForm,
    EventUpdateCapacityForm,
    EventCategoryFilterForm,
    FTEventMemberForm,
    FT24EventMemberForm,
    WelcomeMemberForm,
)

from events.admin import EventMemberAdmin
from shop.admin import OrderItemAdmin

from shop.forms import CartAddEventForm

from .api import call

from .serializers import EventSerializer

from .choices import (
    MEMBERSHIP_CHOICES,
    MEMBERSHIP_CHOICES_24_FULL,
    MEMBER_TYPE_CHOICES,
    FOOD_PREFERENCE_CHOICES,
    BOOKING_CHOICES_27,
    BOOKING_CHOICES_28,
)

import itertools

from wkhtmltopdf.views import PDFTemplateResponse

from vfllnl.models import NewsletterSubscription

import locale

yes_no_dict = {
    "y": True,
    "n": False,
}

# for German locale
locale.setlocale(locale.LC_TIME, "de_DE")


def is_member_of_mv_orga(user):
    return user.groups.filter(name="mv_orga").exists()


def is_member_of_ft_orga(user):
    return user.groups.filter(name="ft_orga").exists()


def choices_to_string(choices_list, choices):
    label_list = [label for value, label in choices if value in choices_list]
    return ", ".join(label_list)


def choices_to_display(choice, choices):
    return choices[choice]


class MVOrgaGroupTestMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name="mv_orga").exists()


class FTOrgaGroupTestMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name="ft_orga").exists()


def user_in_testing_group(user):
    if not user.is_authenticated:
        return False

    testing_group = getattr(settings, "TESTING_GROUP", None)
    if testing_group and user.groups.filter(name=testing_group).exists():
        return True
    return False


def registration_possible_for_this_event(label):
    if label in settings.EVENTS_WITH_REGISTRATION_POSSIBLE:
        return True
    return False


def home(request):
    home = Home.objects.all().first()
    if not home:
        home = Home.objects.create(name=settings.HOME_NAME,
            title=settings.HOME_TITLE,
            text=settings.HOME_TEXT)
                            
    event_highlight_query = EventHighlight.objects.filter(id=1).filter(
        event__first_day__gte=date.today()
    )
    if event_highlight_query:
        event_highlight = event_highlight_query[0]
    else:
        event_highlight = None

    _metadata = {
        'title': 'title',
        'description': 'text',
        'image': 'get_meta_image',
    }

    meta = Meta(
        title=home.title,
        description=home.text if home.text else settings.DEFAULT_META_DESCRIPTION,
        keywords=[kw.strip() for kw in home.keywords.split(",") ] if home.keywords else settings.DEFAULT_META_KEYWORDS,
    )

    context = {
        "event_highlight": event_highlight,
        "home": home,
        "all_events_headline": settings.ALL_EVENTS_HEADLINE,
        'meta': meta
    }

    return render(request, "events/home.html", context)


def maintenance(request):
    context = {"maintenance_end_date": settings.MAINTENANCE_END_DATE}
    return render(request, "events/maintenance.html", context)


@login_required(login_url="users:login")
def dashboard(request):
    event_ctg_count = EventCategory.objects.count()
    event_count = Event.objects.count()
    events = Event.objects.all()
    context = {
        "event_ctg_count": event_ctg_count,
        "event_count": event_count,
        "events": events,
    }
    return render(request, "events/dashboard.html", context)


class EventListInternalView(LoginRequiredMixin, ListView):
    model = Event
    context_object_name = "events"
    template_name = "events/bootstrap/event_list_internal.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if "category" in self.request.GET:
            qs = qs.filter(category__name=self.request.GET["category"])
        if "search" in self.request.GET:
            qs = qs.filter(name__icontains=self.request.GET["search"])
        return qs

    def get_context(self):
        context = super().get_context()
        context["can_delete"] = self.request.user.has_perm("events.delete_event")
        return context


class EventListFilterInternalView(LoginRequiredMixin, BSModalFormView):
    template_name = "events/bootstrap/filter_category.html"
    form_class = EventCategoryFilterForm

    def form_valid(self, form):
        self.filter = "?category=" + form.cleaned_data["category"].name
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse_lazy("event-list-internal") + self.filter


class EventReadView(LoginRequiredMixin, BSModalReadView):
    model = Event
    template_name = "events/bootstrap/read_event.html"


class EventListView(ListView):
    model = Event
    template_name = "events/event_list_filter.html"

    def get_queryset(self):
        queryset = super().get_queryset()

        # only upcoming and not cancelled events and only events with show_date flag
        queryset = (
            Event.objects.all()
            .filter(first_day__gte=date.today())
            .filter(pub_status="PUB")
            .exclude(status="cancel")
            .exclude(event_days=None)
        )  # unsorted

        if self.request.GET.get("cat"):
            queryset = queryset.filter(category__name=self.request.GET.get("cat"))

        # return qs
        return queryset.order_by("first_day")

    def get_context_data(self, **kwargs):
        # get moodle courses
        # fname = 'core_course_get_courses'
        # courses_list = call(fname)
        print("called")

        # events from database
        context = super().get_context_data(**kwargs)

        events_with_date = self.get_queryset().filter(show_date=True)

        # eventcollections from database
        event_collections = EventCollection.objects.all().filter(
            first_day__gte=date.today()
        )

        # sorting events and event_collections

        events_sorted = sorted(
            chain(events_with_date, event_collections),
            key=lambda t: t.get_first_day_start_date(),
        )

        # Version 1
        events_dict = {}

        for year, group in itertools.groupby(
            events_sorted, lambda e: e.get_first_day_start_date().strftime("%Y")
        ):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(
                group, lambda e: e.get_first_day_start_date().strftime("%B")
            ):
                events_dict[year][month] = list(inner_group)

        # print(events_dict)

        # context['events_grouped_list'] = events_grouped_list
        context["events_dict"] = events_dict

        # events without date
        events_without_date = self.get_queryset().filter(show_date=False)
        context["events_without_date"] = events_without_date
        print("events_without_date:", events_without_date)
        return context


class FilteredEventListView(ListView):
    """
    ref: https://www.caktusgroup.com/blog/2018/10/18/filtering-and-pagination-django/
    """

    model = Event
    filterset_class = EventFilter
    template_name = "events/event_list_filter.html"
    strict = False

    def get_queryset(self):
        search = self.request.GET.get("search")
        cat = self.request.GET.get("cat", None)
        # qs of published events without cancelled events
        queryset = (
            super()
            .get_queryset()
            .filter(pub_status="PUB")
            .exclude(event_days=None)
            .exclude(status="cancel")
            .order_by("first_day")
        )

        # search
        if search:
            queryset = queryset.filter(name__icontains=search)

        if cat and cat == "onlyvfll":
            queryset = queryset.filter(category__belongs_to_all_events=True)

        # Then use the query parameters and the queryset to
        # instantiate a filterset and save it as an attribute
        # on the view instance for later.

        # if no date_range_min is given, queryset is filtered by actual date
        date_min = self.request.GET.get("first_day_min", None)
        if date_min is None:
            queryset = queryset.filter(first_day__gte=date.today())

        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)

        # has the request any filters?
        self.has_filter = any(
            field in self.request.GET for field in set(self.filterset.get_fields())
        )
        # filter parameters string
        # set(filterset.get_fields) returs list of fieldnames

        filter_data = self.request.GET.dict()

        filter_translate_dict = {
            "first_day_min": "Datum von",
            "first_day_max": "Datum bis",
            "category": "Kategorie",
            "search": search,  # without this there is a key error
            "cat": cat,  # without this there is a key error
        }

        def get_value_in_readable_form(key, value):
            if key == "first_day_min" or key == "first_day_max":
                return (
                    f"{value.split('-')[2]}.{value.split('-')[1]}.{value.split('-')[0]}"
                )
            if key == "category":
                cat = EventCategory.objects.get(id=value)
                return cat.name

        self.filter_string = ", ".join(
            [
                f"{filter_translate_dict[key]} {get_value_in_readable_form(key, value)}"
                for key, value in filter_data.items()
                if value
            ]
        )

        # Return the filtered queryset

        return self.filterset.qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # filtered_queryset = self.filterset.qs.distinct()

        events_with_date = self.filterset.qs.filter(show_date=True)

        filterset_sorted = sorted(
            events_with_date, key=lambda t: t.get_first_day_start_date()
        )

        events_dict = {}

        for year, group in itertools.groupby(
            filterset_sorted, lambda e: e.get_first_day_start_date().strftime("%Y")
        ):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(
                group, lambda e: e.get_first_day_start_date().strftime("%B")
            ):
                events_dict[year][month] = list(inner_group)

        # Pass the filterset to the template - it provides the form.
        context["filterset"] = self.filterset
        context["events_dict"] = events_dict
        context["has_filter"] = self.has_filter
        context["filter_string"] = self.filter_string

        events_without_date = self.filterset.qs.filter(show_date=False)
        context["events_without_date"] = events_without_date
        context["show_registration_date"] = (
            settings.REGISTRATION_DATE_SHOWN_IN_EVENT_LIST
        )

        return context


class EventCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "events.add_event"
    form_class = EventModelForm
    template_name = "events/bootstrap/create_event_nm.html"
    success_message = "Erfolg: Veranstaltung wurde angelegt."
    success_url = reverse_lazy("event-list-internal")

    def get_form_class(self):
        modelform = super().get_form_class()
        # salon_group = Group.objects.get(name="salon")
        if self.request.user.groups.filter(name="salon"):
            modelform.base_fields["category"].limit_choices_to = {
                "name": settings.SALON_CATEGORY
            }
        return modelform

    def get_initial(self):
        # get the max position value of categories
        max_position = EventCategory.objects.aggregate(Max("position")).get(
            "position__max"
        )
        # get the category salon or create it
        if self.request.user.groups.filter(name="salon"):
            if EventCategory.objects.filter(name=settings.SALON_CATEGORY).exists():
                cat = EventCategory.objects.filter(name=settings.SALON_CATEGORY)
            else:
                cat = None
        else:
            if EventCategory.objects.filter(name=settings.MESSEN_CATEGORY).exists():
                cat = EventCategory.objects.get(name=settings.MESSEN_CATEGORY)
            else:
                cat = None
        return {"pub_status": "UNPUB", "category": cat, "registration_possible": True}

    def get_context_data(self, **kwargs):
        data = super(EventCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["documents"] = EventDocumentFormSet(
                self.request.POST, self.request.FILES
            )
            data["days"] = EventDayFormSet(self.request.POST)
        else:
            data["documents"] = EventDocumentFormSet()
            data["days"] = EventDayFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        documents = context["documents"]
        days = context["days"]

        with transaction.atomic():
            # form.instance.created_by = self.request.user
            self.object = form.save()
            if documents.is_valid():
                documents.instance = self.object
                documents.save()
            if days.is_valid():
                days.instance = self.object
                days.save()
            else:
                print("ERROR", days.errors)
                messages.error(self.request, "ERROR")
        return super(EventCreateView, self).form_valid(form)


class EventUpdateModalView(LoginRequiredMixin, BSModalUpdateView):
    model = Event
    template_name = "events/bootstrap/update_event.html"
    form_class = EventModelForm
    success_message = "Erfolg: Veranstaltung wurde aktualisiert."
    success_url = reverse_lazy("event-list-internal")


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    template_name = "events/bootstrap/update_event_nm.html"
    form_class = EventModelForm
    success_message = "Veranstaltung wurde aktualisiert."
    success_url = reverse_lazy("event-list-internal")

    def get_context_data(self, **kwargs):
        data = super(EventUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["documents"] = EventDocumentFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
            data["days"] = EventDayFormSet(self.request.POST, instance=self.object)
        else:
            data["documents"] = EventDocumentFormSet(instance=self.object)
            data["days"] = EventDayFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        documents = context["documents"]
        days = context["days"]

        with transaction.atomic():
            # form.instance.created_by = self.request.user
            self.object = form.save()
            if documents.is_valid():
                documents.instance = self.object
                documents.save()
            if days.is_valid():
                days.instance = self.object
                days.save()
            else:
                print("ERROR", days.errors)
                messages.error(request, "ERROR")
        return super(EventUpdateView, self).form_valid(form)


class EventCollectionDetailView(DetailView):
    model = EventCollection
    # template_name = "events/event_collection_detail.html"
    template_name = "events/event_collection_detail_V2.html"
    context_object_name = "event_collection"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # due to settings.ONLY_NOT_FULL_EVENTS_CAN_HAVE_ACTION the has_action method
        # returns True also if one of events is full or only if none of events is full
        context["show_action"] = self.object.has_action()[0]
        # and all(
        #    [not event.is_full() for event in self.object.events.all()]
        # )
        # print(self.object.has_action()[0])
        context["payless_collection"] = self.object.has_action()[1]
        context["events"] = self.object.events.all().order_by("first_day")
        # print(self.object.has_action()[1].type)
        return context


# class EventDetailView(LoginRequiredMixin, DetailView):
class EventDetailView(HitCountDetailView):
    login_url = "login"
    model = Event
    # template_name = "events/event_detail_V2.html"
    template_name = "events/event_detail_V3.html"
    context_object_name = "event"

    count_hit = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        event = self.get_object()
        registration_text = ""
        registration_button = ""
        show_button = False
        show_registration = True
        additional_text = ""

        # exception if user is authenticated and belongs to testing group
        # in this case registration possible is set to true
        show = user_in_testing_group(
            self.request.user
        ) or registration_possible_for_this_event(event.label)

        if show:
            event.registration_possible = True
            event.category.registration = True

        if event.category.registration == False:
            if event.registration:
                registration_text = event.registration
            else:
                show_registration = False
            show_button = False
        elif event.registration_possible:
            show_button = True
            show_registration = True
            registration_text = event.registration

            if event.registration_message:
                registration_text += f"<span class='font-medium'>{event.registration_message}</span><br/>"
                registration_button = "Online anmelden"
            else:
                if event.close_date:
                    registration_text += "<span class='font-medium'>Anmeldeschluss: {:%d. %B %Y}</span><br/>".format(
                        event.close_date
                    )
                    if event.is_closed_for_registration():
                        if not event.is_full():
                            if event.few_remaining_places():
                                registration_text += "<span class='text-vfllred'>Anmeldung möglich, da noch wenige freie Plätze</span>"
                            else:
                                registration_text += "<span class='text-vfllred'>Anmeldung möglich, da noch freie Plätze</span>"

                            registration_button = "Online anmelden"
                        else:
                            registration_text += (
                                "<span class='italic'>Leider ausgebucht</span>"
                            )
                            registration_button = "Auf die Warteliste"
                            additional_text = "Nach Abschluss des Bestellvorgangs werden Sie auf die Warteliste gesetzt."
                    else:
                        if not event.is_full():
                            if event.few_remaining_places():
                                registration_text += "<span class='text-vfllred'>Nur noch wenige freie Plätze!</span>"
                            registration_button = "Online anmelden"
                        else:
                            registration_text += (
                                "<span class='italic'>Leider ausgebucht</span> "
                            )
                            registration_button = "Auf die Warteliste"
                            additional_text = "*Nach Abschluss des Bestellvorgangs werden Sie auf die Warteliste gesetzt."

                else:
                    registration_button = "Online anmelden"
        else:
            show_registration = False

        cart_event_form = CartAddEventForm()

        # event belongs to PayLessAction?

        payless_collection = event.payless_collection
        pc_events = []
        context["show_action_button"] = False
        if payless_collection:
            pc_events = payless_collection.events.all()
            show_action_button = payless_collection.action_is_possible()
            context["show_action_button"] = show_action_button

        context["registration_text"] = registration_text
        context["registration_button"] = registration_button
        context["additional_text"] = additional_text
        context["show_button"] = show_button
        context["show_registration"] = show_registration
        context["cart_event_form"] = cart_event_form
        context["pc_events"] = pc_events
        context["payless_collection"] = payless_collection
        context["event_documents"] = event.event_documents.all()
        # context["show_action_button"] = show_action_button

        # meta
        if self.get_object().meta_description:
            description=self.get_object().meta_description
        elif self.get_object().description:
            description=convert_html_to_text(self.get_object().description)
        else:
            description = settings.DEFAULT_META_DESCRIPTION
        description = remove_linebreaks(description)

        meta = Meta(
            title=self.get_object().name,
            description=description,
            keywords=[kw.strip() for kw in self.get_object().keywords.split(",") ] if self.get_object().keywords else settings.DEFAULT_META_KEYWORDS,
        )
        context["meta"] = meta
        return context


class EventDeleteView(LoginRequiredMixin, PermissionRequiredMixin, BSModalDeleteView):
    permission_required = "events.delete_event"
    model = Event
    template_name = "events/bootstrap/delete_event.html"
    success_message = "Erfolg: Veranstaltung wurde gelöscht."
    success_url = reverse_lazy("event-list-internal")


class EventCategoryListView(LoginRequiredMixin, ListView):
    login_url = "login"
    model = EventCategory
    template_name = "events/event_category.html"
    context_object_name = "event_category"


class EventCategoryCreateView(LoginRequiredMixin, CreateView):
    login_url = "login"
    model = EventCategory
    fields = [
        "name",
    ]
    template_name = "events/create_event_category.html"

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class EventLocationListView(LoginRequiredMixin, ListView):
    model = EventLocation
    template_name = "events/bootstrap/location_list.html"
    context_object_name = "locations"


class EventLocationCreateView(LoginRequiredMixin, BSModalCreateView):
    login_url = "login"
    form_class = EventLocationModelForm
    template_name = "events/bootstrap/create_location.html"
    success_message = "Location erfolgreich angelegt"
    success_url = reverse_lazy("event-location-list")


class EventLocationReadView(LoginRequiredMixin, BSModalReadView):
    model = EventLocation
    template_name = "events/bootstrap/read_event_location.html"


class EventLocationUpdateView(LoginRequiredMixin, UpdateView):
    model = EventLocation
    template_name = "events/bootstrap/update_event_location_nm.html"
    form_class = EventLocationNMModelForm
    success_message = "Veranstaltungsort (Location) wurde aktualisiert."
    success_url = reverse_lazy("event-location-list")


class EventLocationDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = EventLocation
    template_name = "events/bootstrap/delete_event_location.html"
    success_message = "Erfolg: Veranstaltungsort (Location) wurde gelöscht."
    success_url = reverse_lazy("event-location-list")


class EventOrganizerCreateView(LoginRequiredMixin, BSModalCreateView):
    login_url = "login"
    form_class = EventOrganizerModelForm
    template_name = "events/bootstrap/create_organizer.html"
    success_message = "Veranstalter erfolgreich angelegt"
    success_url = reverse_lazy("event-list-internal")


class EventOrganizerUpdateView(LoginRequiredMixin, UpdateView):
    model = EventOrganizer
    template_name = "events/bootstrap/update_event_organizer_nm.html"
    form_class = EventOrganizerNMModelForm
    success_message = "Veranstalter wurde aktualisiert."
    success_url = reverse_lazy("event-list-internal")


def search_event(request):
    if request.method == "POST":
        data = request.POST["search"]

        event_queryset_unsorted = (
            Event.objects.all()
            .exclude(event_days=None)
            .filter(pub_status="PUB")
            .filter(name__icontains=data)
        )  # unsorted

        event_queryset = sorted(
            event_queryset_unsorted, key=lambda t: t.get_first_day_start_date()
        )

        events_dict = {}

        for year, group in itertools.groupby(
            event_queryset, lambda e: e.get_first_day_start_date().strftime("%Y")
        ):
            events_dict[year] = {}
            for month, inner_group in itertools.groupby(
                group, lambda e: e.get_first_day_start_date().strftime("%B")
            ):
                events_dict[year][month] = list(inner_group)
        context = {"events_dict": events_dict}

        return render(request, "events/event_list_filter.html", context)
    return render(request, "events/event_list_filter.html")


def get_mail_to_admin_template_name(registration_form):
    if registration_form == "s":
        mail_to_admin_template_name = "anmeldung"
    elif registration_form == "w":
        mail_to_admin_template_name = "wc_anmeldung"
    elif registration_form == "m":
        mail_to_admin_template_name = "mv_anmeldung"
    elif registration_form == "f":
        mail_to_admin_template_name = "ft_anmeldung"
    elif registration_form == "f24":
        mail_to_admin_template_name = "ft_24_anmeldung"
    return mail_to_admin_template_name


def get_mail_to_member_template_name(registration_form, attend_status):
    if registration_form == "s":
        if attend_status == "waiting":
            mail_to_member_template_name = "warteliste"
        else:
            mail_to_member_template_name = "bestaetigung"
    elif registration_form == "w":
        mail_to_member_template_name = "wc_bestaetigung"
    elif registration_form == "m":
        mail_to_member_template_name = "mv_bestaetigung"
    elif registration_form == "f":
        mail_to_member_template_name = "ft_bestaetigung"
    elif registration_form == "f24":
        mail_to_member_template_name = "ft_24_bestaetigung"
    return mail_to_member_template_name


def get_question_link(eventmember):
    full_url = f"{settings.EMAIL_LINK_DOMAIN}{eventmember.get_secure_url()}"
    number_of_questions = eventmember.event.questions.count()
    print("number_of_questions:", number_of_questions)
    if number_of_questions == 0:
        return ""
    elif number_of_questions == 1:
        question_string = "eine Frage"
    else:
        question_string = "einige Fragen"
    additional_message = f"Zur Vorbereitung der Veranstaltung möchten wir Sie bitten, unter dem Link {full_url} {question_string} zu beantworten. Der Link ist drei Tage lang gültig."
    return additional_message


def get_form_template(registration_form):
    if registration_form == "s":
        form_template = "events/add_event_member_tw.html"
    elif registration_form == "w":
        form_template = "events/add_event_member_wc.html"
    elif registration_form == "m":
        form_template = "events/add_event_member_mv.html"
    elif registration_form == "f":
        form_template = "events/add_event_member_ft.html"
    elif registration_form == "f24":
        form_template = "events/add_event_member_ft_2024.html"
    return form_template


def get_personal_form_data(form):
    data_dict = {}
    data_dict["firstname"] = form.cleaned_data["firstname"]
    data_dict["lastname"] = form.cleaned_data["lastname"]
    data_dict["email"] = form.cleaned_data["email"]
    return data_dict


def get_additional_form_data(form, event, form_type):
    data_dict = {}
    if form_type == "s":
        data_dict["address_line"] = form.cleaned_data["address_line"]
        data_dict["street"] = form.cleaned_data["street"]
        data_dict["city"] = form.cleaned_data["city"]
        data_dict["state"] = form.cleaned_data["state"]
        data_dict["postcode"] = form.cleaned_data["postcode"]
        data_dict["phone"] = form.cleaned_data["phone"]
        # make name of this registration from event label and date
        data_dict["name"] = f"{event.label} | {timezone.now()}"
        data_dict["academic"] = form.cleaned_data["academic"]
        data_dict["company"] = form.cleaned_data["company"]
        data_dict["message"] = form.cleaned_data["message"]
        data_dict["vfll"] = form.cleaned_data["vfll"]
        data_dict["memberships"] = form.cleaned_data["memberships"]
        data_dict["attention"] = form.cleaned_data["attention"]
        data_dict["attention_other"] = form.cleaned_data["attention_other"]
        data_dict["education_bonus"] = form.cleaned_data["education_bonus"]
        data_dict["free_text_field"] = form.cleaned_data["free_text_field"]
        data_dict["agree"] = form.cleaned_data["agree"]
        if event.is_full():
            data_dict["attend_status"] = "waiting"
        else:
            data_dict["attend_status"] = "registered"
    elif form_type == "w":
        data_dict["member_type"] = form.cleaned_data.get("member_type")
        data_dict["attend_status"] = "registered"
    elif form_type == "f24":
        data_dict["address_line"] = form.cleaned_data["address_line"]
        data_dict["street"] = form.cleaned_data["street"]
        data_dict["city"] = form.cleaned_data["city"]
        data_dict["postcode"] = form.cleaned_data["postcode"]
        data_dict["phone"] = form.cleaned_data["phone"]
        data_dict["member_type"] = (
            "o"
            if "vv" in form.cleaned_data["memberships_full"]
            else "k" if "vk" in form.cleaned_data["memberships_full"] else None
        )
        if data_dict["member_type"]:
            data_dict["vfll"] = True
        data_dict["memberships"] = [
            item
            for item in form.cleaned_data["memberships_full"]
            if item not in ["vv", "vk"]
        ]
        # make name of this registration from event label and date
        data_dict["name"] = f"{event.label} | {timezone.now()}"

    return data_dict


def get_mv_form_data(form):
    data_dict = {}
    vote_transfer = form.cleaned_data.get("vote_transfer")
    data_dict["vote_transfer"] = vote_transfer
    data_dict["vote_transfer_check"] = form.cleaned_data.get("vote_transfer_check")
    data_dict["check"] = form.cleaned_data.get("mv_check")
    data_dict["member_type"] = form.cleaned_data.get("member_type")
    data_dict["attend_status"] = "registered"
    return data_dict


def get_f24_form_data(form):
    food_pref_list = []
    food_pref_list.append(form.cleaned_data.get("food_preferences"))
    booking27_list = []
    booking27_list.append(form.cleaned_data.get("booking27"))
    booking28_list = []
    booking28_list.append(form.cleaned_data.get("booking28"))

    data_dict = {}
    data_dict["memberships_full"] = form.cleaned_data.get("memberships_full")
    data_dict["nomember"] = form.cleaned_data.get("nomember")
    data_dict["takes_part_in_mv"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_mv")
    )
    data_dict["takes_part_in_ft"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_ft")
    )
    data_dict["having_lunch"] = boolean_translate(form.cleaned_data.get("having_lunch"))
    data_dict["networking"] = boolean_translate(form.cleaned_data.get("networking"))
    data_dict["yoga"] = boolean_translate(form.cleaned_data.get("yoga"))
    data_dict["ideas"] = boolean_translate(form.cleaned_data.get("ideas"))
    data_dict["celebration"] = boolean_translate(form.cleaned_data.get("celebration"))
    data_dict["food_preferences"] = choices_to_string(
        food_pref_list, FOOD_PREFERENCE_CHOICES
    )
    data_dict["food_remarks"] = form.cleaned_data.get("food_remarks")
    data_dict["booking27"] = choices_to_string(booking27_list, BOOKING_CHOICES_27)
    data_dict["booking28"] = choices_to_string(booking28_list, BOOKING_CHOICES_28)

    data_dict["remarks"] = form.cleaned_data.get("remarks")

    return data_dict


def make_event_registration(request, form, event):
    personal_data_dict = get_personal_form_data(form)
    if event.registration_form == "s":
        s_data_dict = get_additional_form_data(form, event, "s")
        new_member = EventMember.objects.create(
            event=event, **personal_data_dict, **s_data_dict
        )
    elif event.registration_form == "w":
        w_data_dict = get_additional_form_data(form, event, "w")
        new_member = EventMember.objects.create(
            event=event, **personal_data_dict, **w_data_dict
        )
    elif event.registration_form == "m":
        m_data_dict = get_mv_form_data(form)
        new_member = EventMember.objects.create(
            event=event, **personal_data_dict, **m_data_dict
        )
    elif event.registration_form == "f24":
        f24_additional_data = get_additional_form_data(form, event, "f24")
        f24_data_dict = get_f24_form_data(form)
        new_member = EventMember.objects.create(
            agree=True,
            data=f24_data_dict,
            attend_status="registered",
            event=event,
            **personal_data_dict,
            **f24_additional_data,
        )

    """
    zusätzlich wird ein eindeutiges Label für diese Anmeldung kreiert, um das Label
    für Mailversand zu haben.
    Das wird in models.py in der save method hinzugefügt
    """

    member_label = EventMember.objects.latest("date_created").label

    if event.registration_form == "s" or event.registration_form == "w":
        # attend_status = get_additional_form_data(form, event, "s")["attend_status"]
        attend_status = new_member.attend_status
    elif event.registration_form == "m":
        attend_status = "registered"
    elif event.registration_form == "f24":
        attend_status = "registered"

    mail_to_admin_template_name = get_mail_to_admin_template_name(
        event.registration_form
    )
    mail_to_member_template_name = get_mail_to_member_template_name(
        event.registration_form, attend_status
    )
    formatting_dict = get_personal_form_data(form)

    if event.registration_form == "s":
        formatting_dict.update(get_additional_form_data(form, event, "s"))
    if event.registration_form == "w":
        formatting_dict.update(get_additional_form_data(form, event, "w"))
    elif event.registration_form == "m":
        formatting_dict.update(get_mv_form_data(form))
        if formatting_dict["vote_transfer"]:
            transfer_string = f"Du nimmst an der Mitgliederversammlung nicht teil und überträgst deine Stimme für alle Abstimmungen und Wahlen inhaltlich unbegrenzt an: {formatting_dict['vote_transfer']}"
        else:
            transfer_string = ""
        formatting_dict.update({"transfer_string": transfer_string})
    elif event.registration_form == "f24":
        formatting_dict.update(get_additional_form_data(form, event, "f24"))
        formatting_dict.update(get_f24_form_data(form))

    update_boolean_values(formatting_dict)
    if event.registration_form == "m" or event.registration_form == "w":
        formatting_dict["member_type"] = dict(form.fields["member_type"].choices).get(
            formatting_dict["member_type"]
        )
    if event.registration_form == "f24":
        memberships_list = []
        for item in form.cleaned_data["memberships_full"]:
            memberships_list.append(
                dict(form.fields["memberships_full"].choices).get(item)
            )
        formatting_dict["memberships"] = ", ".join(memberships_list)

    # set the right attend status in the formatting_dict
    formatting_dict["attend_status"] = attend_status

    if event.registration_form == "s" :
        formatting_dict["question_link"] = get_question_link(new_member)

    print("question link:", formatting_dict["question_link"])

    vfll_mail_sent = send_email_after_registration(
        "vfll", event, form, mail_to_admin_template_name, formatting_dict
    )

    if settings.SEND_EMAIL_AFTER_REGISTRATION_TO_MEMBER:
        member_mail_sent = send_email_after_registration(
            "member", event, form, mail_to_member_template_name, formatting_dict
        )
    else:
        member_mail_sent = False

    messages_dict = {
        "s": (
            "Vielen Dank für Ihre Anmeldung. Wir melden uns bei Ihnen mit weiteren Informationen.",
            "Vielen Dank für Ihre Anmeldung. Sie wurden auf die Warteliste gesetzt und werden benachrichtigt, wenn ein Platz frei wird.",
        )[attend_status == "waiting"],
        "w": "Vielen Dank für Ihre Anmeldung. Wir melden uns bei Ihnen mit weiteren Informationen.",
        "m": "Vielen Dank für deine Anmeldung. Weitere Informationen und der Zugangscode für das Wahltool werden nach dem Anmeldeschluss, wenige Tage vor den Veranstaltungen, versandt.",
        "f": "Vielen Dank für deine Anmeldung. Weitere Informationen werden nach dem Anmeldeschluss versandt.",
        "f24": "Vielen Dank für deine Anmeldung. Weitere Informationen werden nach dem Anmeldeschluss versandt.",
    }
    # only for registrations with non direct payment events
    if not event.direct_payment:
        messages.success(
            request, messages_dict[event.registration_form], fail_silently=True
        )

    # save new member
    new_member = EventMember.objects.latest("date_created")
    new_member.save()

    if vfll_mail_sent:
        new_member.mail_to_admin = True
        new_member.save()

    if member_mail_sent:
        new_member.mail_to_member = True
        new_member.save()


def add_to_newsletter(email):
    try:
        newsletter = NewsletterSubscription.objects.get(email=email)
    except NewsletterSubscription.DoesNotExist:
        newsletter = NewsletterSubscription(email=email)
        newsletter.save()


def handle_form_submission(request, form, event):
    if form.is_valid():
        newsletter = form.cleaned_data.get("newsletter", None)
        personal_data_dict = get_personal_form_data(form)
        if no_duplicate_check(personal_data_dict.get("email"), event):

            if newsletter:
                add_to_newsletter(personal_data_dict.get("email"))
            make_event_registration(request, form, event)

        elif not event.direct_payment:
            messages.error(
                request,
                "Es gibt bereits eine Anmeldung mit dieser E-Mail-Adresse!",
                fail_silently=True,
            )

    return form.is_valid()


# @login_required(login_url="login")
def event_add_member(request, slug):
    event = get_object_or_404(Event, slug=slug)

    show = user_in_testing_group(request.user)
    if show:
        event.registration_possible = True

    if not event.registration_possible:
        messages.add_message(
            request, messages.ERROR, "keine Anmeldung möglich", fail_silently=True
        )
        return redirect("event-detail", event.slug)

    if event.direct_payment:
        payment_button_text = settings.PAY_NOW_TEXT
    else:
        if event.price == Decimal("0.00"):
            payment_button_text = settings.REGISTER_NOW_FREE_TEXT
        else:
            payment_button_text = settings.REGISTER_NOW_TEXT

    # if event is full both texts are overwritten
    if event.is_full():
        payment_button_text = settings.REGISTER_NOW_TEXT_WAITING

    form_template = get_form_template(event.registration_form)

    # get the workshop and tour capacity utilisations for fachtagung
    if event.label == "ffl_mv_2022":
        ws_utilisations, tour_utilisations = get_utilisations(event)

    # forms with labels  m and f no longer needed
    if request.method == "GET":
        if event.registration_form == "s":
            form = EventMemberForm(initial={"country": "DE"})
        elif event.registration_form == "w":
            form = WelcomeMemberForm(initial={"country": "DE"})
        elif event.registration_form == "m":
            # print(f"event label: {event.label}")
            # form = SymposiumForm(event_label=event.label)
            form = MV2023Form(event_label=event.label)
        elif event.registration_form == "f":
            # print("ws to form:", ws_utilisations)
            form = Symposium2022Form(
                event_label=event.label,
                ws_utilisations=ws_utilisations,
                tour_utilisations=tour_utilisations,
            )
        elif event.registration_form == "f24":
            # print("ws to form:", ws_utilisations)
            form = Symposium2024Form(
                event_label=event.label,
            )

    if request.method == "POST":
        if event.registration_form == "s":
            form = EventMemberForm(request.POST)
        elif event.registration_form == "w":
            form = WelcomeMemberForm(request.POST)
        elif event.registration_form == "m":
            form = MV2023Form(request.POST, event_label=event.label)
        elif event.registration_form == "f":
            form = Symposium2022Form(
                request.POST,
                event_label=event.label,
                ws_utilisations=ws_utilisations,
                tour_utilisations=tour_utilisations,
            )
        elif event.registration_form == "f24":
            form = Symposium2024Form(
                request.POST,
                event_label=event.label,
            )

        form_is_valid = handle_form_submission(request, form, event)
        if form_is_valid:
            return redirect("event-detail", event.slug)

    return render(
        request,
        form_template,
        {"form": form, "event": event, "payment_button_text": payment_button_text},
    )


# moodle
def moodle(request):
    fname = "core_course_get_courses"
    courses_list = call(fname)
    context = {"courses": courses_list}
    return render(request, "events/moodle_list.html", context)


@login_required(login_url="login")
def get_moodle_data(request):
    get_and_save_courses_from_moodle.delay()
    return HttpResponse("moodle Daten aktualisiert")


@login_required(login_url="login")
def admin_event_pdf(request, event_id):
    """Idea to solve static url problem with wkhtmltopdf:
    https://gist.github.com/renyi/f02b4322590e9288ac679545df4748d3"""

    STATIC_URL = settings.STATIC_URL

    event = get_object_or_404(Event, id=event_id)
    context = {"event": event}

    if "http" not in STATIC_URL:
        # wkhtmltopdf requires full uri to load css
        from urllib.parse import urlparse

        parsed = urlparse(request.META.get("HTTP_REFERER"))
        parsed = "{uri.scheme}://{uri.netloc}".format(uri=parsed)
        context["STATIC_URL"] = "{}{}".format(parsed, settings.STATIC_URL)
    else:
        context["STATIC_URL"] = settings.STATIC_URL
    response = PDFTemplateResponse(
        request=request,
        context=context,
        template="admin/event_pdf_template.html",
        filename=f"event-{event.label}.pdf",
        show_content_in_browser=True,
        cmd_options={
            "encoding": "utf8",
            "quiet": True,
            "orientation": "portrait",
        },
    )

    return response


class EventApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        if request.GET.get("start"):
            start = request.GET.get("start")
        else:
            start = "2023-01-01"
        if request.GET.get("end"):
            end = request.GET.get("end")
        else:
            end = "2023-12-31"
        events = (
            Event.objects.exclude(event_days=None)
            .filter(first_day__gt=start, first_day__lt=end)
            .filter(pub_status="PUB")
            .order_by("first_day")
        )
        serializer = EventSerializer(events, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventMembersListView(MVOrgaGroupTestMixin, ListView):
    """
    View to see Members of Event
    Permission: request.user has to be in group mv_orga
    Event is given by event_label
    """

    model = EventMember
    template_name = "events/members_list.html"
    context_object_name = "event_members"
    # template_name = "events/test.html"

    def dispatch(self, request, *args, **kwargs):
        from .parameters import has_vote_transfer

        self.event_label = self.kwargs["event"]
        self.show_vote_transfer = has_vote_transfer.get(self.event_label, None)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        event_members = EventMember.objects.filter(
            event__label=self.event_label
        ).order_by("lastname")
        query_ln = self.request.GET.get("member_lastname")
        query_fn = self.request.GET.get("member_firstname")
        query_email = self.request.GET.get("member_email")

        if self.show_vote_transfer:
            query_vote_transfer_yes = self.request.GET.get("member_vote_transfer_yes")
            query_vote_transfer_no = self.request.GET.get("member_vote_transfer_no")

        flag = self.request.GET.get("flag")
        # print(f"flag: {flag}")
        # print(f"vt: {query_vote_transfer_yes}")

        if query_fn:
            event_members = event_members.filter(firstname__icontains=query_fn)
        if query_ln:
            event_members = event_members.filter(lastname__icontains=query_ln)
        if query_email:
            event_members = event_members.filter(email__icontains=query_email)

        if self.show_vote_transfer:
            if query_vote_transfer_yes:
                event_members = event_members.exclude(vote_transfer__exact="")
            if query_vote_transfer_no:
                event_members = event_members.filter(vote_transfer__exact="")
        if flag == "duplicates":
            duplicate_email_list = Event.objects.get(
                label=self.kwargs["event"]
            ).get_duplicate_members()
            event_members = event_members.filter(email__in=duplicate_email_list)

        return event_members

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add a context
        context["event"] = Event.objects.get(label=self.event_label)
        context["show_vote_transfer"] = self.show_vote_transfer
        # print(context)
        return context


@login_required
def get_members_list(request, event):
    event_obj = Event.objects.get(label=event)
    user = request.user
    user_groups = user.groups.all()
    allowed_groups = event_obj.visible_to_groups.all()

    common_group_exists = user_groups.filter(
        id__in=allowed_groups.values_list("id", flat=True)
    ).exists()

    if not common_group_exists:
        raise PermissionDenied
    event_members = EventMember.objects.filter(event__label=event).order_by("lastname")
    context = {}
    context["event"] = Event.objects.get(label=event)
    context["event_members"] = event_members
    return render(request, "events/members_list.html", context)


@login_required
def search_members_list(request, event):
    query = request.GET.get("search", "")
    event_members = EventMember.objects.filter(event__label=event).order_by("lastname")

    if query:
        event_members = event_members.filter(
            Q(lastname__icontains=query)
            | Q(firstname__icontains=query)
            | Q(email__icontains=query)
        )

    context = {}
    context["event_members"] = event_members

    return render(request, "events/includes/member_list.html", context)


@login_required
def edit_member(request, member_pk):
    member = EventMember.objects.get(pk=member_pk)
    context = {}
    context["member"] = member
    context["form"] = MemberForm(
        initial={
            "firstname": member.firstname,
            "lastname": member.lastname,
            "email": member.email,
            "attend_status": member.attend_status,
        }
    )
    return render(request, "events/includes/edit_member.html", context)


@login_required
def edit_member_submit(request, member_pk):
    context = {}
    member = EventMember.objects.get(pk=member_pk)
    context["member"] = member
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
        else:
            return render(request, "events/includes/edit_member.html", context)
    return render(request, "events/includes/member_row.html", context)


class FTEventMembersListView(FTOrgaGroupTestMixin, SingleTableView):
    model = EventMember
    table_class = FTEventMembersTable
    template_name = "events/ft_members_list.html"

    def get_queryset(self):
        event_members = EventMember.objects.filter(event__label=self.kwargs["event"])
        query_ln = self.request.GET.get("member_lastname")
        query_fn = self.request.GET.get("member_firstname")
        query_email = self.request.GET.get("member_email")
        query_remark = self.request.GET.get("member_remark")

        if query_fn:
            event_members = event_members.filter(firstname__icontains=query_fn)
        if query_ln:
            event_members = event_members.filter(lastname__icontains=query_ln)
        if query_email:
            event_members = event_members.filter(email__icontains=query_email)
        if query_remark:
            if query_remark.strip() == "*":
                event_members = event_members.exclude(data__remark="")
            else:
                event_members = event_members.filter(
                    data__remark__icontains=query_remark
                )

        return event_members

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add a context
        context["event_label"] = self.kwargs["event"]
        # print(context)
        return context


class MVEventMembersListView(MVOrgaGroupTestMixin, SingleTableView):
    model = EventMember
    table_class = MVEventMembersTable
    template_name = "events/mv_members_list.html"

    def get_queryset(self):
        event_members = EventMember.objects.filter(
            event__name="Digitale Mitgliederversammlung 2023"
        )
        query_ln = self.request.GET.get("member_lastname")
        query_fn = self.request.GET.get("member_firstname")
        query_email = self.request.GET.get("member_email")

        if query_fn:
            event_members = event_members.filter(firstname__icontains=query_fn)
        if query_ln:
            event_members = event_members.filter(lastname__icontains=query_ln)
        if query_email:
            event_members = event_members.filter(email__icontains=query_email)

        return event_members

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add a context
        context["event_label"] = self.kwargs["event"]
        # print(context)
        return context


class EventMemberDetailView(MVOrgaGroupTestMixin, DetailView):
    model = EventMember
    template_name = "events/member_detail.html"


class FTEventMemberDetailView(FTOrgaGroupTestMixin, DetailView):
    model = EventMember
    template_name = "events/ft24_member_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super(FTEventMemberDetailView, self).get_context_data(*args, **kwargs)
        obj = self.get_object()
        # convert jsonfield = string in db to real json
        data = obj.data
        context["data"] = data
        return context


class MVEventMemberDetailView(MVOrgaGroupTestMixin, DetailView):
    model = EventMember
    template_name = "events/mv_member_detail.html"


class EventMemberUpdateView(MVOrgaGroupTestMixin, UpdateView):
    model = EventMember
    fields = [
        "firstname",
        "lastname",
        "email",
        "member_type",
        "attend_status",
        "vote_transfer",
        "vote_transfer_check",
    ]
    template_name = "events/member_update.html"

    def get_success_url(self):
        pk = self.kwargs["pk"]

        label = EventMember.objects.get(pk=pk).event.label
        return reverse("members", kwargs={"event": label})


class FTEventMemberUpdateView(MVOrgaGroupTestMixin, UpdateView):
    model = EventMember

    form_class = FT24EventMemberForm

    template_name = "events/ft_member_update.html"

    def get_success_url(self):
        pk = self.kwargs["pk"]

        label = EventMember.objects.get(pk=pk).event.label
        return reverse("ft-members", kwargs={"event": label})

    def form_valid(self, form):
        data = form.cleaned_data["data"]
        self.object.firstname = data["firstname"]
        self.object.lastname = data["lastname"]
        self.object.email = data["email"]
        return super(FTEventMemberUpdateView, self).form_valid(form)


class MVEventMemberUpdateView(MVOrgaGroupTestMixin, UpdateView):
    model = EventMember
    template_name = "events/mv_member_update.html"
    fields = ["lastname", "firstname", "email", "vote_transfer", "vote_transfer_check"]

    def get_success_url(self):
        pk = self.kwargs["pk"]

        label = EventMember.objects.get(pk=pk).event.label
        return reverse("mv-members", kwargs={"event": label})


class EventMemberCreateView(MVOrgaGroupTestMixin, CreateView):
    model = EventMember
    template_name = "events/create_member_form.html"
    form_class = AddMemberForm

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, label=kwargs["event"])
        self.event_members = EventMember.objects.filter(
            event__label=kwargs["event"]
        ).filter(attend_status="registered")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.takes_part = True
        self.object.agree = True
        self.object.event = self.event
        if self.event_members.count() >= self.event.capacity:
            self.object.attend_status = "waiting"
        else:
            self.object.attend_status = "registered"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("members", kwargs={"event": self.event.label})


class EventMemberDeleteView(MVOrgaGroupTestMixin, DeleteView):
    model = EventMember
    success_url = reverse_lazy("members-dashboard")
    template_name = "events/confirm_member_delete.html"


class EventUpdateCapacityView(MVOrgaGroupTestMixin, UpdateView):
    model = Event
    template_name = "events/update_capacity_form.html"
    form_class = EventUpdateCapacityForm

    def get_success_url(self):
        return reverse_lazy("members-dashboard")


@login_required
@check_user_able_to_see_page("can_export")
def export_members_csv(request, event):
    # check group
    logger.info("event label = %s" % (event,))
    event_obj = Event.objects.get(label=event)
    user = request.user
    user_groups = user.groups.all()
    allowed_groups = event_obj.visible_to_groups.all()

    common_group_exists = user_groups.filter(
        id__in=allowed_groups.values_list("id", flat=True)
    ).exists()

    if not common_group_exists:
        raise PermissionDenied

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{event}_TN_{date.today()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Vorname",
            "Nachname",
            "E-Mail",
            "Datum",
            "Mitgliedschaft",
        ]
    )

    members = EventMember.objects.filter(event__label=event).values_list(
        "firstname",
        "lastname",
        "email",
        "date_created",
        "member_type",
    )

    for member in members:
        member = list(member)
        member[3] = member[3].strftime("%d.%m.%y %H:%M")

        writer.writerow(member)

    return response


@login_required
@user_passes_test(is_member_of_mv_orga)
def export_mv_members_csv(request, event):
    # print(f"request: {request.GET}")
    query_ln = request.GET.get("member_lastname")
    query_fn = request.GET.get("member_firstname")
    query_email = request.GET.get("member_email")

    query_vote_transfer_yes = request.GET.get("member_vote_transfer_yes")
    query_vote_transfer_no = request.GET.get("member_vote_transfer_no")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="teilnehmer_{date.today()}.csv"'
    )

    writer = csv.writer(response)
    writer_list = ["Vorname", "Nachname", "E-Mail", "Status", "Datum", "Mitgliedschaft"]
    from .parameters import has_vote_transfer

    if has_vote_transfer.get(event, None):
        writer_list.extend(
            ["Stimmübertragung", "Check Stimmübertragung", "Einverständnis MV"]
        )
    writer.writerow(writer_list)

    members_mv = EventMember.objects.filter(event__label=event)
    if query_fn:
        members_mv = members_mv.filter(firstname__icontains=query_fn)
    if query_ln:
        members_mv = members_mv.filter(lastname__icontains=query_ln)
    if query_email:
        members_mv = members_mv.filter(email__icontains=query_email)
    if query_vote_transfer_yes:
        members_mv = members_mv.exclude(vote_transfer__exact="")
    if query_vote_transfer_no:
        members_mv = members_mv.filter(vote_transfer__exact="")

    members_mv = members_mv.values_list(
        "firstname",
        "lastname",
        "email",
        "attend_status",
        "date_created",
        "member_type",
    )
    if has_vote_transfer.get(event, None):
        members_mv.extend(
            members_mv.values_list(
                "vote_transfer",
                "vote_transfer_check",
                "agree",
            )
        )

    for member in members_mv:
        member = list(member)
        member[4] = member[4].strftime("%d.%m.%y %H:%M")

        writer.writerow(member)

    return response


def download(request, path):
    download_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(download_path):
        with open(download_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/pdf_file")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                download_path
            )
            return response
    raise Http404


@login_required
@user_passes_test(is_member_of_mv_orga)
def members_dashboard_view(request):
    context = {
        "count_members_of_mv": EventMember.objects.filter(
            event__label="Online-MV2021"
        ).count(),
        "count_members_of_zw": EventMember.objects.filter(
            event__label="zukunft2021"
        ).count(),
        "count_members_of_zw_waiting": EventMember.objects.filter(
            event__label="zukunft2021"
        )
        .filter(attend_status="waiting")
        .count(),
        "count_members_of_zw_registered": EventMember.objects.filter(
            event__label="zukunft2021"
        )
        .filter(attend_status="registered")
        .count(),
        "capacity_of_zw": Event.objects.get(label="zukunft2021").capacity,
        "list_of_mv_member_duplicates": Event.objects.get(
            label="Online-MV2021"
        ).get_duplicate_members(),
        "list_of_zw_member_duplicates": Event.objects.get(
            label="zukunft2021"
        ).get_duplicate_members(),
        "zw_event_id": Event.objects.get(label="zukunft2021").id,
    }
    return render(request, "events/members_dashboard.html", context)


@login_required
@user_passes_test(is_member_of_mv_orga)
def ft_members_dashboard_view(request):
    from .parameters import ws_limits

    ws_dict = {}
    ws_utilisation = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0, "VI": 0}

    tour_dict = {}
    tour_utilisation = {"I": 0, "II": 0}

    for member in EventMember.objects.filter(event__label="ffl_mv_2024"):
        if member.data.get("ws2022"):
            if member.data["ws2022"] in settings.WS_LIMITS.keys():
                ws_utilisation[member.data["ws2022"]] = (
                    ws_utilisation[member.data["ws2022"]] + 1
                )
    for key in ws_utilisation.keys():
        ws_dict[key] = (
            str(ws_utilisation[key]) + " (" + str(settings.WS_LIMITS[key]) + ")"
        )

    # dict with free places: dict comprehension
    ws_free_places = {
        key: settings.WS_LIMITS[key] - ws_utilisation.get(key, 0)
        for key in settings.WS_LIMITS
    }
    ws_combined = {
        key: [ws_utilisation[key], ws_free_places[key]] for key in ws_utilisation
    }

    del ws_combined["VI"]

    for member in EventMember.objects.filter(event__label="ffl_mv_2024"):
        if member.data.get("tour"):
            if member.data["tour"] in settings.TOUR_LIMITS.keys():
                tour_utilisation[member.data["tour"]] = (
                    tour_utilisation[member.data["tour"]] + 1
                )
    for key in tour_utilisation.keys():
        tour_dict[key] = (
            str(tour_utilisation[key]) + " (" + str(settings.TOUR_LIMITS[key]) + ")"
        )

    # dict with free places: dict comprehension
    tour_free_places = {
        key: settings.TOUR_LIMITS[key] - tour_utilisation.get(key, 0)
        for key in settings.TOUR_LIMITS
    }
    tour_combined = {
        key: [tour_utilisation[key], tour_free_places[key]] for key in tour_utilisation
    }

    # create bar plot of  utilisations
    ws_plot_div = make_bar_plot_from_dict(ws_combined, "Teilnehmer")
    tour_plot_div = make_bar_plot_from_dict(tour_combined, "Teilnehmer")
    context = {
        "count_members_of_mv": EventMember.objects.filter(
            event__label="ffl_mv_2024"
        ).count(),
        "ws_dict": ws_dict,
        "tour_dict": tour_dict,
        "now": datetime.now(),
        "ws_plot_div": ws_plot_div,
        "tour_plot_div": tour_plot_div,
    }
    return render(request, "events/ft_members_dashboard.html", context)


@staff_member_required
def ft_report(request):
    qs = EventMember.objects.filter(event__label="ffl_mv_2024")
    template_name = "admin/events/ft_report.html"
    return render(request, template_name, {"members": qs, "number_members": len(qs)})


@login_required
def export_ft_members_csv(request):
    response = HttpResponse(content_type="text/csv")
    date = datetime.today().strftime("%Y-%m-%d")
    response["Content-Disposition"] = f"attachment; filename='members_ft_{date}.csv'"

    writer = csv.writer(response)
    writer.writerow(
        [
            "Vorname",
            "Nachname",
            "E-Mail",
            "Adresszusatz",
            "Straße",
            "PLZ",
            "Ort",
            "Tel.",
            "Anmeldedatum",
            "Workshop",
            "WS-Alternative",
            "MV",
            "Mittagessen",
            "Führung",
            "Netzwerkabend",
            "Yoga",
            "Feier",
            "Essenswunsch",
            "Mitgliedschaft",
            "kein Mitglied",
            "Bemerkung",
        ]
    )

    members_ft = EventMember.objects.filter(event__label="ffl_mv_2024")

    data_list = members_ft.values_list(
        "data",
    )

    for member in members_ft:
        json_object = member.data
        values = list(json_object.values())
        writer.writerow(values)

    return response


@login_required
@user_passes_test(is_member_of_ft_orga)
def export_ft_members_xls(request):
    # content type
    # response = HttpResponse(content_type="application/ms-excel")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # create filename
    date = datetime.today().strftime("%Y-%m-%d")
    output_name = f"members_ft_{date}.xlsx"
    response["Content-Disposition"] = f"attachment; filename={output_name}"

    # get the members
    ftm = EventMember.objects.filter(event__label="ffl_mv_2024").values(
        "lastname",
        "firstname",
        "email",
        "address_line",
        "street",
        "postcode",
        "city",
        "data",
    )

    # the data json objects are returned as strings, so convert to list of dicts
    # with json.loads
    # ftm_list = [json.loads(j) for j in list(ftm)] # no more needed

    # make dict from values
    result = [
        {
            **{
                "lastname": item["lastname"],
                "firstname": item["firstname"],
                "email": item["email"],
                "address_line": item["address_line"],
                "street": item["street"],
                "postcode": item["postcode"],
                "city": item["city"],
            },
            **item["data"],
        }
        for item in ftm
    ]

    # creating pandas Data Frame
    df = pd.DataFrame(result)
    # reordering
    df = df[
        [
            "lastname",
            "firstname",
            "email",
            "address_line",
            "street",
            "postcode",
            "city",
            "takes_part_in_mv",
            "takes_part_in_ft",
            "having_lunch",
            "networking",
            "yoga",
            "ideas",
            "celebration",
            "food_preferences",
            "food_remarks",
            "booking27",
            "booking28",
            "memberships_full",
            "nomember",
            "remarks",
        ]
    ]
    # renaming
    df.columns = [
        "Nachname",
        "Vorname",
        "E-Mail",
        "Adresszusatz",
        "Strasse",
        "PLZ",
        "Stadt",
        "Teilnahme MV",
        "Teilname FT",
        "Mittagessen",
        "TN Networking",
        "TN Fuehrung",
        "TN Erfahrungsaustausch",
        "TN Feier",
        "Essenswuensche",
        "Essen Bem.",
        "Buchung 27./28.9.",
        "Buchung 28./29.9.",
        "Mitgliedschaften",
        "kein Mitglied",
        "Bem.",
    ]
    df.to_excel(response)

    return response


def export_moodle_participants(request, event_id):
    if not request.user.is_staff:
        raise PermissionDenied
    event = Event.objects.get(id=event_id)
    participants = event.members.all().filter(attend_status="registered")
    today = date.today()
    filename = f"members_{event.label}_{today}.csv"
    response = HttpResponse(content_type="text/csv")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    fields_to_export = [
        "email",
        "firstname",
        "lastname",
        "email",
    ]
    header_list = ["username", "firstname", "lastname", "email", "course1", "role1"]
    writer.writerow(header_list)
    # Write data rows
    print("event label: ", event.label)
    for member in participants:
        row = [getattr(member, field) for field in fields_to_export]
        print("row: ", row)
        row.append(event.label)
        row.append("student")
        writer.writerow(row)
    return response


def export_participants(request, event_id, version):
    if not request.user.is_staff:
        raise PermissionDenied

    event = Event.objects.get(id=event_id)

    if version == "controlling":
        field_names = [
            "lastname",
            "firstname",
            "academic",
            "company",
            "street",
            "postcode",
            "city",
            "phone",
            "email",
            "get_memberships_boolean",
            "get_no_memberships_boolean",
            # "vfll",
            # "agree",
            "date_created",
            "get_order_nr",
            "get_order_price",
            "get_payment_receipt",
        ]
        file_name = f"Controlling_{event.label}_{datetime.now().date()}"
        sheet_title = "Controlling"
    elif version == "participants":
        field_names = [
            "lastname",
            "firstname",
            "academic",
            "phone",
            "email",
        ]
        file_name = f"TeilnehmerInnen_{event.label}_{datetime.now().date()}"
        sheet_title = "TeilnehmerInnen"

    # invoice_items_list = ["get_cost_property", "order", "get_invoice_number"]

    blank_line = []
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title

    ws.append(
        ExportExcelAction.generate_header(EventMemberAdmin, EventMember, field_names)
    )

    # if version == "participants":
    #     ws.append(
    #         ExportExcelAction.generate_header(
    #             EventMemberAdmin, EventMember, field_names
    #         )
    #     )
    # elif version == "controlling":
    #     ws.append(
    #         ExportExcelAction.generate_header(
    #             OrderItemAdmin, OrderItem, invoice_items_list
    #         )
    #     )

    def iterate(ws, queryset, admin_cls, field_names):
        from django.contrib import admin

        # get model for admin_cls
        model_class = EventMember
        # crate instance of admin_cls
        admin_cls_instance = admin_cls(model_class, admin.site)
        counter = 1
        for obj in queryset:
            row = [str(counter)]
            for field in field_names:
                is_admin_field = hasattr(admin_cls, field)
                if (
                    is_admin_field and not field == "check"
                ):  # check is also admin_field, but we need model field
                    # if field == "get_order":
                    #     get_order = getattr(admin_cls_instance, field)
                    #     value = get_order(obj)
                    # else:
                    #     value = getattr(admin_cls, field)(obj)
                    method = getattr(admin_cls_instance, field)
                    value = method(obj)
                    if isinstance(value, bool):
                        value = convert_boolean_field(value)
                else:
                    value = getattr(obj, field)
                    if isinstance(value, datetime) or isinstance(value, date):
                        value = convert_data_date(value)
                    elif isinstance(value, bool):
                        value = convert_boolean_field(value)
                    elif value == None:
                        value = ""

                row.append(str(value))

            ws.append(row)
            counter += 1

    # all data
    qs_event_members = event.members.all()
    qs_event_members_registered = qs_event_members.filter(
        Q(attend_status="registered")
    ).annotate(vfll_true=Count("vfll", filter=Q(vfll=True)))
    admin_cls = EventMemberAdmin
    # registered participants
    iterate(ws, qs_event_members_registered, admin_cls, field_names)
    if version == "controlling":
        qs_event_members_waiting = qs_event_members.filter(Q(attend_status="waiting"))
        ws.append(blank_line)
        # waiting participants on same sheet
        ws.append(["", "Warteliste"])
        iterate(ws, qs_event_members_waiting, admin_cls, field_names)
        # Speakers
        ws.append(blank_line)
        ws.append(["", "Referentinnen"])
        for speaker in event.speaker.all():
            ws.append(["", speaker.last_name, speaker.first_name, speaker.email])
        # Event Details
        ws.append(blank_line)
        ws.append(["", "Veranstaltungsdaten"])
        ws.append(["", "Veranstaltungstitel:", event.name])
        ws.append(["", "Veranstaltungsformat:", event.eventformat.name])
        ws.append(
            [
                "",
                "Termin:",
                (
                    datetime.strftime(event.first_day, "%d.%m.%Y")
                    if event.first_day
                    else ""
                ),
            ]
        )
        ws.append(["", "Ort:", event.location.title])
        ws.append(
            ["", "Veranstalter:", event.organizer.name if event.organizer else ""]
        )
        # for field_name in field_names:
        #     value = getattr(event, field_name)
        #     if isinstance(value, datetime) or isinstance(value, date):
        #         value = convert_data_date(value)
        #     elif isinstance(value, bool):
        #         value = convert_boolean_field(value)
        #     ws.append(["", field_name, value])

    # invoices items on next sheet
    # qs_order_items = OrderItem.objects.filter(event=event)
    # admin_cls = OrderItemAdmin
    # iterate(ws2, qs_order_items, admin_cls, invoice_items_list)

    # sum of costs
    # total_costs = sum(item.get_cost_property for item in qs_order_items)

    # ws2.append(blank_line)
    # ws2.append(["Summe", total_costs])

    ws = style_output_file(ws)
    # ws1 = style_output_file(ws1)
    # ws2 = style_output_file(ws1)

    # Controlling
    # ws3.append(["Veranstaltung:", event.name])
    # ws3.append(["Anz. TN:", len(qs_event_members_registered)])
    # ws3.append(["Einnahmen:", total_costs])
    # total_vfll_true = sum(obj.vfll_true for obj in qs_event_members_registered)
    # ws3.append(["vfll Mitglieder:", total_vfll_true])
    # memberships_list = []  #
    # # obj.memberships is str repr of list so it must be converted to list
    # for obj in qs_event_members_registered:
    #     if not obj.vfll:
    #         memberships_list.extend(ast.literal_eval(obj.memberships))
    # for ms_short, ms_long in MEMBERSHIP_CHOICES:
    #     ws3.append([ms_long, memberships_list.count(ms_short)])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={file_name}.xlsx"
    wb.save(response)
    return response


@login_required
def documentation_view(request):
    # Read the Markdown content from the file
    with open("eventmanager/static/docs/documentation.md", "r") as f:
        documentation_content = f.read()

    # Render the Markdown content using the markdown library
    rendered_content = markdown.markdown(documentation_content)

    return render(
        request,
        "admin/documentation_view.html",
        {"documentation_content": rendered_content},
    )
