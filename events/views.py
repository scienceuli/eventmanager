import ast
import csv
import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from itertools import chain

import markdown
import pandas as pd
from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalDeleteView,
    BSModalFormView,
    BSModalReadView,
    BSModalUpdateView,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.mail import BadHeaderError, send_mail
from django.db import transaction
from django.db.models import Count, F, Max, Q, Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect, request
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_tables2 import SingleTableView
from hitcount.views import HitCountDetailView
from meta.views import Meta
from openpyxl import Workbook
from openpyxl.styles import Font
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from unidecode import unidecode

from events.actions import convert_boolean_field, style_output_file
from events.decorators import check_user_able_to_see_page
from events.filter import EventFilter
from events.services.export_service import ExportService
from events.services.notification_service import NotificationService
from events.services.pre_registration_service import PreRegistrationService
from events.services.registration import EventRegistrationService
from events.services.registration_display_service import RegistrationDisplayService
from events.services.strategies import get_strategy
from events.utils import form_utils
from events.utils.email_utils import (
    send_email_after_registration,
    send_registration_emails,
)
from events.utils.member_utils import create_member
from events.utils.messages_utils import add_error, add_success
from events.utils.utils import (
    add_to_newsletter,
    boolean_translate,
    convert_boolean_field,
    convert_data_date,
    convert_html_to_text,
    get_utilisations,
    make_bar_plot_from_dict,
    remove_linebreaks,
    update_boolean_values,
    yes_no_to_boolean,
)

from .export_excel import ExportExcelAction

# Get an instance of a logger
logger = logging.getLogger(__name__)

logging.basicConfig(filename="eventmanager.log", encoding="utf-8", level=logging.ERROR)

import itertools
import locale

from wkhtmltopdf.views import PDFTemplateResponse

from events.admin import EventMemberAdmin
from shop.admin import OrderItemAdmin
from shop.forms import CartAddEventForm
from shop.models import OrderItem

from .api import call
from .choices import (
    BOOKING_CHOICES_27,
    BOOKING_CHOICES_28,
    FOOD_PREFERENCE_CHOICES,
    MEMBER_TYPE_CHOICES,
    MEMBERSHIP_CHOICES,
    MEMBERSHIP_CHOICES_24_FULL,
)
from .core_models import SiteSettings
from .forms import (
    AddMemberForm,
    EventCategoryFilterForm,
    EventDayFormSet,
    EventDocumentFormSet,
    EventLocationModelForm,
    EventLocationNMModelForm,
    EventMemberForm,
    EventModelForm,
    EventOrganizerModelForm,
    EventPreRegistrationForm,
    EventOrganizerNMModelForm,
    EventUpdateCapacityForm,
    FT24EventMemberForm,
    FTEventMemberForm,
    MemberForm,
    MV2023Form,
    MV2025Form,
    MV2026MemberEditForm,
    Symposium2022Form,
    Symposium2024Form,
    SymposiumForm,
    WelcomeMemberForm,
)
from .models import (
    Event,
    EventCategory,
    EventCollection,
    EventHighlight,
    EventImage,
    EventLocation,
    EventMember,
    EventOrganizer,
    EventSpeaker,
    EventSponsor,
    HeroSliderImage,
    Home,
)
from .serializers import EventSerializer
from .tables import EventMembersTable, FTEventMembersTable, MVEventMembersTable

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
        home = Home.objects.create(
            name=settings.HOME_NAME, title=settings.HOME_TITLE, text=settings.HOME_TEXT
        )

    event_highlight_query = EventHighlight.objects.filter(id=1).filter(
        event__first_day__gte=date.today()
    )
    if event_highlight_query:
        event_highlight = event_highlight_query[0]
    else:
        event_highlight = None

    # next four events — exclude full events (registered members >= capacity)
    # and events of partners
    next_events = (
        Event.objects.filter(
            category__belongs_to_all_events=True,
            status="active",
            first_day__gte=date.today(),
        )
        .annotate(
            registered_count=Count(
                "members", filter=Q(members__attend_status="registered")
            )
        )
        .filter(Q(capacity__isnull=True) | Q(registered_count__lt=F("capacity")))
        .exclude(category__name__in=settings.PARTNER_CATEGORIES)
        .order_by("first_day")[:4]
    )

    # Get active hero slider images ordered by sequence
    hero_slider_images = HeroSliderImage.objects.filter(is_active=True).order_by(
        "order"
    )

    _metadata = {
        "title": "title",
        "description": "text",
        "image": "get_meta_image",
    }

    meta = Meta(
        title=home.title,
        description=home.text if home.text else settings.DEFAULT_META_DESCRIPTION,
        keywords=[kw.strip() for kw in home.keywords.split(",")]
        if home.keywords
        else settings.DEFAULT_META_KEYWORDS,
    )

    context = {
        "event_highlight": event_highlight,
        "next_events": next_events,
        "home": home,
        "hero_slider_images": hero_slider_images,
        "all_events_headline": settings.ALL_EVENTS_HEADLINE,
        "meta": meta,
    }

    return render(request, "events/home.html", context)


def flatpage_view(request, page):
    home = Home.objects.first()
    content_map = {
        "contact": home.contact,
        "impressum": home.impressum,
        "legals": home.legals,
        "privacy": home.privacy,
        "about_us": home.about_us,
    }
    title_map = {
        "contact": "Kontakt",
        "impressum": "Impressum",
        "legals": "Rechtliche Hinweise",
        "privacy": "Datenschutz",
        "about_us": "Über uns",
    }
    content = content_map.get(page)
    title = title_map.get(page)
    if not content:
        raise Http404("Page not found")
    return render(request, "events/flatpage.html", {"content": content, "title": title})


def speakers_view(request):
    from datetime import date

    from django.db.models import Count, Prefetch, Q

    future_published_events = Event.objects.filter(
        pub_status="PUB",
        first_day__gte=date.today(),
    ).order_by("first_day")
    speakers = (
        EventSpeaker.objects.filter(show=True)
        .prefetch_related(
            Prefetch(
                "event_set", queryset=future_published_events, to_attr="upcoming_events"
            )
        )
        .annotate(
            event_count=Count(
                "event",
                filter=Q(event__pub_status="PUB", event__first_day__gte=date.today()),
            )
        )
        .distinct()
        .order_by("-event_count", "last_name")
    )
    return render(request, "events/speakers.html", {"speakers": speakers})


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
        sia = self.request.GET.get("sia", None)
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

        if sia and sia == "yes":
            queryset = queryset.filter(show_in_all_events=True)

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
            "sia": sia,  # without this there is a key error
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
    template_name = "events/event_detail_V3.html"
    context_object_name = "event"

    count_hit = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        event = self.get_object()

        # exception if user is authenticated and belongs to testing group
        # in this case registration possible is set to true
        override_registration_possible = user_in_testing_group(
            self.request.user
        ) or registration_possible_for_this_event(event.label)

        display = RegistrationDisplayService().get_display(
            event, override_registration_possible=override_registration_possible
        )

        cart_event_form = CartAddEventForm()

        # event belongs to PayLessAction?

        payless_collection = event.payless_collection
        pc_events = []
        context["show_action_button"] = False
        if payless_collection:
            pc_events = payless_collection.events.all()
            show_action_button = payless_collection.action_is_possible()
            context["show_action_button"] = show_action_button

        context["registration_text"] = display.registration_text
        context["registration_button"] = display.registration_button
        context["additional_text"] = display.additional_text
        context["show_button"] = display.show_button
        context["show_registration"] = display.show_registration
        context["show_pre_registration"] = display.show_pre_registration
        context["cart_event_form"] = cart_event_form
        context["pc_events"] = pc_events
        context["payless_collection"] = payless_collection
        context["event_documents"] = event.event_documents.all()
        # context["show_action_button"] = show_action_button

        # meta
        if self.get_object().meta_description:
            description = self.get_object().meta_description
        elif self.get_object().description:
            description = convert_html_to_text(self.get_object().description)
        else:
            description = settings.DEFAULT_META_DESCRIPTION
        description = remove_linebreaks(description)

        meta = Meta(
            title=self.get_object().name,
            description=description,
            keywords=[kw.strip() for kw in self.get_object().keywords.split(",")]
            if self.get_object().keywords
            else settings.DEFAULT_META_KEYWORDS,
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


def event_add_member(request, slug):
    event = get_object_or_404(Event, slug=slug)
    strategy = get_strategy(event)

    if not event.registration_possible and not user_in_testing_group(request.user):
        add_error(request, "keine Anmeldung möglich")
        return redirect("event-detail", event.slug)

    # button text logic (unchanged)
    if event.direct_payment:
        payment_button_text = settings.PAY_NOW_TEXT
    else:
        if event.price == Decimal("0.00"):
            payment_button_text = settings.REGISTER_NOW_FREE_TEXT
        else:
            payment_button_text = settings.REGISTER_NOW_TEXT

    if event.is_full():
        payment_button_text = settings.REGISTER_NOW_TEXT_WAITING

    form_template = form_utils.get_form_template(event.registration_form)

    # special case (unchanged if needed)
    if event.label == "ffl_mv_2026":
        ws_utilisations, tour_utilisations = get_utilisations(event)

    # -----------------------------
    # POST handling
    # -----------------------------
    if request.method == "POST":
        form = strategy.get_form(event, request.POST)
        if form.is_valid():
            service = EventRegistrationService()
            result = service.register(form, event)

            # apply messages
            for msg in result.successes:
                add_success(request, msg)

            for msg in result.errors:
                add_error(request, msg)

            # send notification emails for non-shop registrations
            if result.success:
                notification_service = NotificationService()
                notification_service.send_notification_emails(
                    event, form, result.member, result.strategy
                )

            # redirect to unified result page
            if result.success:
                return redirect("shop:order-result", status="ready")
            else:
                return redirect("shop:order-result", status="error")
    else:
        form = strategy.get_form(event)

    # -----------------------------
    # GET rendering
    # -----------------------------
    return render(
        request,
        form_template,
        {
            "form": form,
            "event": event,
            "payment_button_text": payment_button_text,
        },
    )

def event_pre_register(request, slug):
    event = get_object_or_404(Event, slug=slug)

    if request.method == "POST":
        form = EventPreRegistrationForm(request.POST, event=event)
        if form.is_valid():
            service = PreRegistrationService()
            result = service.register(form, event)

            for msg in result.successes:
                add_success(request, msg)
            for msg in result.errors:
                add_error(request, msg)

            return redirect("event-detail", event.slug)
    else:
        form = EventPreRegistrationForm(event=event)

    return render(
        request,
        "events/event_pre_register_form.html",
        {"form": form, "event": event},
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
        label = self.kwargs["event"]
        event_members = EventMember.objects.filter(event__label=label)
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


class FTEventMemberDeleteView(FTOrgaGroupTestMixin, DeleteView):
    model = EventMember
    template_name = "events/confirm_member_delete.html"

    def get_success_url(self):
        pk = self.kwargs["pk"]

        label = EventMember.objects.get(pk=pk).event.label
        return reverse("ft-members", kwargs={"event": label})


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


class MV2026MemberUpdateView(MVOrgaGroupTestMixin, UpdateView):
    model = EventMember
    form_class = MV2026MemberEditForm
    template_name = "events/mv2026_member_update.html"

    def get_success_url(self):
        label = EventMember.objects.get(pk=self.kwargs["pk"]).event.label
        return reverse("ft-members", kwargs={"event": label})

    def form_valid(self, form):
        instance = form.save(commit=False)
        if instance.data is None:
            instance.data = {}
        data_fields = [
            "takes_part_in_mv",
            "ws2026",
            "tour",
            "dinner_one",
            "dinner_two",
            "food_preferences",
            "food_remarks",
            "memberships",
            "remarks",
        ]
        for field in data_fields:
            instance.data[field] = form.cleaned_data.get(field)
        instance.save()
        return HttpResponseRedirect(self.get_success_url())


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

    export_service = ExportService()
    return export_service.export_members_csv(event)


@login_required
@user_passes_test(is_member_of_mv_orga)
def export_mv_members_csv(request, event):
    filters = {
        "lastname": request.GET.get("member_lastname"),
        "firstname": request.GET.get("member_firstname"),
        "email": request.GET.get("member_email"),
        "vote_transfer_yes": request.GET.get("member_vote_transfer_yes"),
        "vote_transfer_no": request.GET.get("member_vote_transfer_no"),
    }

    export_service = ExportService()
    return export_service.export_mv_members_csv(event, filters)


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
    from .choices import TOUR_CHOICES_2026, WS2026_CHOICES
    from .parameters import ws_limits

    WS2026_REVERSE = {label: key for key, label in WS2026_CHOICES}
    TOUR_CHOICES_2026_REVERSE = {label: key for key, label in TOUR_CHOICES_2026}

    ws_dict = {}
    ws_utilisation = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0, "VI": 0}

    tour_dict = {}
    tour_utilisation = {"I": 0, "II": 0}

    for member in EventMember.objects.filter(event__label="ffl_mv_2026"):
        if member.data.get("ws2026"):
            ws_key = WS2026_REVERSE.get(member.data["ws2026"])
            if ws_key and ws_key in settings.WS_LIMITS.keys():
                ws_utilisation[ws_key] = ws_utilisation[ws_key] + 1
    for key in ws_utilisation.keys():
        # ws_dict[key] = (
        #     str(ws_utilisation[key]) + " (" + str(settings.WS_LIMITS[key]) + ")"
        # )
        # FT 2026: no limits
        ws_dict[key] = str(ws_utilisation[key])

    # dict with free places: dict comprehension
    ws_free_places = {
        key: settings.WS_LIMITS[key] - ws_utilisation.get(key, 0)
        for key in settings.WS_LIMITS
    }
    ws_combined = {
        key: [ws_utilisation[key], ws_free_places[key]] for key in ws_utilisation
    }

    # del ws_combined["-"]

    for member in EventMember.objects.filter(event__label="ffl_mv_2026"):
        if member.data.get("tour"):
            tour_key = TOUR_CHOICES_2026_REVERSE.get(member.data["tour"])

            if tour_key and tour_key in settings.TOUR_LIMITS.keys():
                tour_utilisation[tour_key] = tour_utilisation[tour_key] + 1
    for key in tour_utilisation.keys():
        # tour_dict[key] = (
        #     str(tour_utilisation[key]) + " (" + str(settings.TOUR_LIMITS[key]) + ")"
        # )
        # FT 2026 no limits
        tour_dict[key] = str(tour_utilisation[key])

    # dict with free places: dict comprehension
    tour_free_places = {
        key: settings.TOUR_LIMITS[key] - tour_utilisation.get(key, 0)
        for key in settings.TOUR_LIMITS
    }
    tour_combined = {
        key: [tour_utilisation[key], tour_free_places[key]] for key in tour_utilisation
    }
    # labels for dashboard
    ws_labels = {label: ws_dict[key] for key, label in WS2026_CHOICES if key != "-"}
    tour_labels = {
        label: tour_dict[key] for key, label in TOUR_CHOICES_2026 if key != "-"
    }

    # create bar plot of  utilisations
    ws_plot_div = make_bar_plot_from_dict(ws_utilisation, "Workshops")
    tour_plot_div = make_bar_plot_from_dict(tour_utilisation, "Rahmenprogramm")
    context = {
        "count_members_of_mv": EventMember.objects.filter(
            event__label="ffl_mv_2026"
        ).count(),
        "ws_dict": ws_dict,
        "ws_labels": ws_labels,
        "tour_labels": tour_labels,
        "tour_dict": tour_dict,
        "now": datetime.now(),
        "ws_plot_div": ws_plot_div,
        "tour_plot_div": tour_plot_div,
    }
    return render(request, "events/ft_members_dashboard.html", context)


@staff_member_required
def ft_report(request):
    qs = EventMember.objects.filter(event__label="ffl_mv_2026")
    template_name = "admin/events/ft_report.html"
    return render(request, template_name, {"members": qs, "number_members": len(qs)})


@login_required
def export_ft_members_csv(request):
    export_service = ExportService()
    return export_service.export_ft_members_csv()


@login_required
@user_passes_test(is_member_of_ft_orga)
def export_ft_members_xls(request):
    export_service = ExportService()
    return export_service.export_ft_members_xls()


def export_moodle_participants(request, event_id):
    if not request.user.is_staff:
        raise PermissionDenied
    event = Event.objects.get(id=event_id)

    export_service = ExportService()
    return export_service.export_moodle_participants(event)


def export_participants(request, event_id, version):
    if not request.user.is_staff:
        raise PermissionDenied

    event = Event.objects.get(id=event_id)

    export_service = ExportService()
    return export_service.export_participants_xls(event, version)


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


@staff_member_required
def create_confirmations(request, event_id):
    from events.services.confirmation_service import ConfirmationService

    event = get_object_or_404(Event, pk=event_id)
    service = ConfirmationService()
    created, updated, errors = service.make_pdfs_for_event(event)

    msg = f"{created} Teilnahmebescheinigung(en) erzeugt."
    if updated:
        msg += f" {updated} neu generiert (bereits vorhanden)."
    if errors:
        msg += f" {len(errors)} Fehler: {'; '.join(errors)}"
        messages.warning(request, msg)
    else:
        messages.success(request, msg)

    return redirect(reverse("admin:events_event_change", args=[event_id]))
