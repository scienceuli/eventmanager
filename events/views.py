import os
import csv
import json
import pandas as pd
from events.actions import convert_boolean_field

from django.db import transaction
from django.db.models import Max
from django.shortcuts import render, get_object_or_404, redirect
from django.http import request, HttpResponse, Http404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse_lazy, reverse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth.mixins import UserPassesTestMixin
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

from datetime import datetime
from datetime import date

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

from .utils import yes_no_to_boolean, make_bar_plot_from_dict

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

logging.basicConfig(filename="mail_sent.log", encoding="utf-8", level=logging.DEBUG)

#

from .models import (
    Home,
    EventCategory,
    Event,
    EventLocation,
    EventImage,
    EventMember,
    EventHighlight,
    EventSponsor,
)

from .tables import EventMembersTable, FTEventMembersTable

from .forms import (
    EventDayFormSet,
    EventLocationModelForm,
    EventLocationNMModelForm,
    EventOrganizerModelForm,
    EventModelForm,
    EventMemberForm,
    EventDocumentFormSet,
    Symposium2022Form,
    SymposiumForm,
    AddMemberForm,
    EventUpdateCapacityForm,
    EventCategoryFilterForm,
    FTEventMemberForm,
)

from .api import call

from .serializers import EventSerializer

from .choices import MEMBERSHIP_CHOICES, FOOD_PREFERENCE_CHOICES

from .utils import send_email, boolean_translate

import itertools

from wkhtmltopdf.views import PDFTemplateResponse

import locale

# for German locale
locale.setlocale(locale.LC_TIME, "de_DE")


def is_member_of_mv_orga(user):
    return user.groups.filter(name="mv_orga").exists()


def choices_to_string(choices_list, choices):
    label_list = [label for value, label in choices if value in choices_list]
    return ", ".join(label_list)


def choices_to_display(choice, choices):
    return choices[choice]


class GroupTestMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name="mv_orga").exists()


def home(request):
    home = Home.objects.all().first()
    event_highlight_query = EventHighlight.objects.filter(id=1).filter(
        event__first_day__gte=date.today()
    )
    if event_highlight_query:
        event_highlight = event_highlight_query[0]
    else:
        event_highlight = None

    context = {"event_highlight": event_highlight, "home": home}

    return render(request, "events/home.html", context)


@login_required(login_url="login")
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
    template_name = "events/event_list_tw.html"

    def get_queryset(self):

        queryset = super().get_queryset()

        # only upcoming events
        queryset = (
            Event.objects.all()
            .filter(first_day__gte=date.today())
            .filter(pub_status="PUB")
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

        # events from database
        context = super().get_context_data(**kwargs)

        events = self.get_queryset()

        # sorting

        events_sorted = sorted(events, key=lambda t: t.get_first_day_start_date())

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
        # Get the queryset however you usually would.  For example:
        queryset = (
            super()
            .get_queryset()
            .filter(pub_status="PUB")
            .exclude(event_days=None)
            .order_by("first_day")
        )
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

        # Return the filtered queryset

        return self.filterset.qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # filtered_queryset = self.filterset.qs.distinct()

        filterset_sorted = sorted(
            self.filterset.qs, key=lambda t: t.get_first_day_start_date()
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

        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    form_class = EventModelForm
    template_name = "events/bootstrap/create_event_nm.html"
    success_message = "Erfolg: Veranstaltung wurde angelegt."
    success_url = reverse_lazy("event-list-internal")

    def get_initial(self):
        # get the max position value of categories
        max_position = EventCategory.objects.aggregate(Max("position")).get(
            "position__max"
        )
        # get the category vfll-intern or create it
        obj, created = EventCategory.objects.get_or_create(
            name="messen",
            defaults={"title": "Messen und Tagungen", "position": max_position + 1},
        )
        return {"pub_status": "UNPUB", "category": obj}

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
            print(days)
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
            print(days)
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


# class EventDetailView(LoginRequiredMixin, DetailView):
class EventDetailView(HitCountDetailView):
    login_url = "login"
    model = Event
    template_name = "events/event_detail_V2.html"
    context_object_name = "event"

    count_hit = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        event = self.get_object()
        registration_text = ""
        registration_button = ""
        show_button = False
        show_registration = True
        if event.category.name == "Fortbildungen unserer Kooperationspartner*innen":
            if event.registration:
                registration_text = event.registration
            else:
                show_registration = False
            show_button = False
        elif event.registration_possible:
            show_button = True
            show_registration = True
            registration_text = event.registration

            if event.close_date:
                registration_text += "<span class='font-medium'>Anmeldeschluss: {:%d. %B %Y}</span><br/>".format(
                    event.close_date
                )
                if event.is_closed_for_registration():
                    if not event.is_full():
                        registration_text += "<span class='text-vfllred'>Anmeldung möglich, da noch wenige freie Plätze</span>"
                        registration_button = "Online anmelden"
                    else:
                        registration_text += (
                            "<span class='italic'>Leider ausgebucht</span>"
                        )
                        registration_button = "Auf die Warteliste"
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
            else:
                registration_button = "Online anmelden"
        else:
            show_registration = False

        context["registration_text"] = registration_text
        context["registration_button"] = registration_button
        context["show_button"] = show_button
        context["show_registration"] = show_registration
        return context


class EventDeleteView(LoginRequiredMixin, BSModalDeleteView):
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

        return render(request, "events/event_list_tw.html", context)
    return render(request, "events/event_list_tw.html")


def get_mail_to_admin_template_name(registration_form):
    if registration_form == "s":
        mail_to_admin_template_name = "anmeldung"
    elif registration_form == "m":
        mail_to_admin_template_name = "mv_zw_anmeldung"
    elif registration_form == "f":
        mail_to_admin_template_name = "ft_anmeldung"
    return mail_to_admin_template_name


def get_mail_to_member_template_name(registration_form):
    if registration_form == "s":
        mail_to_member_template_name = "bestaetigung"
    elif registration_form == "m":
        mail_to_member_template_name = "mv_zw_bestaetigung"
    elif registration_form == "f":
        mail_to_member_template_name = "ft_bestaetigung"
    return mail_to_member_template_name


def get_form_template(registration_form):
    if registration_form == "s":
        form_template = "events/add_event_member_tw.html"
    elif registration_form == "m":
        form_template = "events/add_event_member_mv.html"
    elif registration_form == "f":
        form_template = "events/add_event_member_ft.html"
    return form_template


# @login_required(login_url="login")
def event_add_member(request, slug):
    event = get_object_or_404(Event, slug=slug)
    mail_to_admin_template_name = get_mail_to_admin_template_name(
        event.registration_form
    )
    mail_to_member_template_name = get_mail_to_member_template_name(
        event.registration_form
    )
    form_template = get_form_template(event.registration_form)

    # get the workshop capacity utilisations for fachtagung
    if event.label == "ffl_mv_2022":
        # ws_capacities = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0, "VI": 0}
        from .parameters import ws_limits

        # print("ws_limits:", ws_limits)
        ws_utilisations = settings.WS_LIMITS.copy()
        for member in event.members.all():
            if member.data.get("ws2022"):
                if member.data["ws2022"] in ws_utilisations.keys():
                    ws_utilisations[member.data["ws2022"]] = (
                        ws_utilisations[member.data["ws2022"]] - 1
                    )
        # print("ws_utilisations: ", ws_utilisations)

        tour_utilisations = settings.TOUR_LIMITS.copy()
        for member in event.members.all():
            if member.data.get("tour"):
                if member.data["tour"] in tour_utilisations.keys():
                    tour_utilisations[member.data["tour"]] = (
                        tour_utilisations[member.data["tour"]] - 1
                    )

    if request.method == "GET":
        if event.registration_form == "s":
            form = EventMemberForm(initial={"country": "DE"})
        elif event.registration_form == "m":
            # print(f"event label: {event.label}")
            form = SymposiumForm(event_label=event.label)
        elif event.registration_form == "f":
            # print("ws to form:", ws_utilisations)
            form = Symposium2022Form(
                event_label=event.label,
                ws_utilisations=ws_utilisations,
                tour_utilisations=tour_utilisations,
            )
    else:
        if event.registration_form == "s":
            form = EventMemberForm(request.POST)
        elif event.registration_form == "m":
            form = SymposiumForm(request.POST, event_label=event.label)
        elif event.registration_form == "f":
            form = Symposium2022Form(
                request.POST,
                event_label=event.label,
                ws_utilisations=ws_utilisations,
                tour_utilisations=tour_utilisations,
            )
        if form.is_valid():
            if event.registration_form == "s":
                academic = form.cleaned_data["academic"]
                firstname = form.cleaned_data["firstname"]
                lastname = form.cleaned_data["lastname"]

                address_line = form.cleaned_data["address_line"]
                company = form.cleaned_data["company"]
                street = form.cleaned_data["street"]
                city = form.cleaned_data["city"]
                state = form.cleaned_data["state"]
                postcode = form.cleaned_data["postcode"]

                email = form.cleaned_data["email"]
                phone = form.cleaned_data["phone"]
                message = form.cleaned_data["message"]
                vfll = form.cleaned_data["vfll"]
                memberships = form.cleaned_data["memberships"]
                memberships_labels = form.selected_memberships_labels()
                attention = form.cleaned_data["attention"]
                attention_other = form.cleaned_data["attention_other"]
                education_bonus = form.cleaned_data["education_bonus"]
                free_text_field = form.cleaned_data["free_text_field"]
                check = form.cleaned_data["check"]
                if event.is_full():
                    attend_status = "waiting"
                else:
                    attend_status = "registered"

                # make name of this registration from event label and date

                name = f"{event.label} | {timezone.now()}"

                new_member = EventMember.objects.create(
                    name=name,
                    event=event,
                    academic=academic,
                    firstname=firstname,
                    lastname=lastname,
                    company=company,
                    street=street,
                    address_line=address_line,
                    city=city,
                    postcode=postcode,
                    state=state,
                    email=email,
                    phone=phone,
                    message=message,
                    vfll=vfll,
                    memberships=memberships,
                    attention=attention,
                    attention_other=attention_other,
                    education_bonus=education_bonus,
                    free_text_field=free_text_field,
                    check=check,
                    attend_status=attend_status,
                )

            elif event.registration_form == "m":
                firstname = form.cleaned_data["firstname"]
                lastname = form.cleaned_data["lastname"]
                email = form.cleaned_data["email"]
                takes_part_in_mv = form.cleaned_data["takes_part_in_mv"]
                member_type = form.cleaned_data["member_type"]
                member_type_label = form.member_type_label()
                takes_part_in_zw = form.cleaned_data["takes_part_in_zw"]
                mv_check = form.cleaned_data["mv_check"]
                zw_check = form.cleaned_data["zw_check"]
                vote_transfer = form.cleaned_data["vote_transfer"]
                vote_transfer_check = form.cleaned_data["vote_transfer_check"]

                yes_no_dict = {
                    "y": True,
                    "n": False,
                }

                if takes_part_in_mv == "y" or vote_transfer:
                    name = f"MV 2021 | {timezone.now()}"
                    try:
                        event = Event.objects.get(label="Online-MV2021")
                        if event.is_full():
                            attend_status = "waiting"
                        else:
                            attend_status = "registered"
                        new_member = EventMember.objects.create(
                            name=name,
                            event=event,
                            firstname=firstname,
                            lastname=lastname,
                            email=email,
                            takes_part=yes_no_dict[takes_part_in_mv],
                            member_type=member_type,
                            vote_transfer=vote_transfer,
                            vote_transfer_check=vote_transfer_check,
                            check=mv_check,
                            attend_status=attend_status,
                        )
                    except Event.DoesNotExist:
                        logger.error("Event does not exist")

                if takes_part_in_zw == "y":
                    name = f"ZW 2021 | {timezone.now()}"
                    try:
                        event = Event.objects.get(label="zukunft2021")
                        if event.is_full():
                            attend_status = "waiting"
                        else:
                            attend_status = "registered"
                        new_member = EventMember.objects.create(
                            name=name,
                            event=event,
                            firstname=firstname,
                            lastname=lastname,
                            email=email,
                            takes_part=True,
                            check=zw_check,
                            attend_status=attend_status,
                        )
                    except Event.DoesNotExist:
                        logger.error("Event does not exist")

            elif event.registration_form == "f":
                firstname = form.cleaned_data["firstname"]
                lastname = form.cleaned_data["lastname"]
                email = form.cleaned_data["email"]
                address_line = form.cleaned_data["address_line"]
                street = form.cleaned_data["street"]
                city = form.cleaned_data["city"]
                postcode = form.cleaned_data["postcode"]
                phone = form.cleaned_data["phone"]
                ws2022 = form.cleaned_data["ws2022"]
                ws_alter = form.cleaned_data["ws_alter"]
                takes_part_in_mv = form.cleaned_data["takes_part_in_mv"]
                # takes_part_in_ft = form.cleaned_data["takes_part_in_ft"]
                having_lunch = form.cleaned_data["having_lunch"]
                tour = form.cleaned_data["tour"]
                networking = form.cleaned_data["networking"]
                yoga = form.cleaned_data["yoga"]
                celebration = form.cleaned_data["celebration"]
                food_preferences = form.cleaned_data["food_preferences"]
                remarks = form.cleaned_data["remarks"]
                memberships = form.cleaned_data["memberships"]
                nomember = form.cleaned_data["nomember"]

                if event.is_full():
                    attend_status = "waiting"
                else:
                    attend_status = "registered"

                bools = ("nein", "ja")

                data_dict = {
                    "firstname": firstname,
                    "lastname": lastname,
                    "email": email,
                    "address_line": address_line,
                    "street": street,
                    "postcode": postcode,
                    "city": city,
                    "phone": phone,
                    "date": timezone.now().strftime("%d.%m.%Y"),
                    "ws2022": ws2022,
                    "ws_alter": ws_alter,
                    "takes_part_in_mv": bools[takes_part_in_mv],
                    # "takes_part_in_ft": bools[takes_part_in_ft],
                    "having_lunch": bools[having_lunch],
                    "tour": tour,
                    "networking": bools[networking],
                    "yoga": bools[yoga],
                    "celebration": bools[celebration],
                    "food_preferences": food_preferences,
                    "memberships": choices_to_string(memberships, MEMBERSHIP_CHOICES),
                    # "memberships": memberships,
                    "nomember": bools[nomember],
                    "remarks": remarks,
                }

                name = f"{event.label} | {timezone.now()}"

                new_member = EventMember.objects.create(
                    name=name,
                    event=event,
                    firstname=firstname,
                    lastname=lastname,
                    email=email,
                    address_line=address_line,
                    street=street,
                    postcode=postcode,
                    city=city,
                    attend_status=attend_status,
                    data=data_dict,
                )

            """
            zusätzlich wird ein eindeutiges Label für diese Anmeldung kreiert, um das Label
            für Mailversand zu haben.
            Das wird in models.py in der save method hinzugefügt
            """

            member_label = EventMember.objects.latest("date_created").label

            ## mail preparation
            if event.registration_form == "s":
                subject = f"Anmeldung am Kurs {event.name}"
            elif event.registration_form == "m":
                subject = f"Anmeldung zur MV / Zukunftswerkstatt"
            elif event.registration_form == "f":
                subject = f"Anmeldung zur Fachtagung Freies Lektorat 2022"

            # mails to vfll
            addresses_list = []
            if event.sponsors:
                for sponsor in event.sponsors.all().exclude(email__isnull=True):
                    addresses_list.append(sponsor.email)
            if len(addresses_list) == 0:
                if event.registration_recipient:
                    addresses_list.append(event.registration_recipient)
                else:
                    addresses_list.append(settings.EVENT_RECEIVER_EMAIL)

            addresses = {"to": addresses_list}

            addresses_string = " oder ".join(addresses_list)

            # Dozenten - nur bei Fortbildungen
            if event.registration_form == "s":
                speaker_list = []
                if event.speaker:
                    for sp in event.speaker.all():
                        speaker_list.append(sp.full_name)

                if len(speaker_list) == 0:
                    speaker_string = "NN"
                else:
                    speaker_string = ", ".join(speaker_list)

                formatting_dict = {
                    "academic": academic,
                    "firstname": firstname,
                    "lastname": lastname,
                    "address_line": address_line,
                    "company": company,
                    "street": street,
                    "city": city,
                    "postcode": postcode,
                    "state": state,
                    "email": email,
                    "phone": phone,
                    "vfll": boolean_translate(vfll),
                    "memberships": memberships_labels,
                    "education_bonus": boolean_translate(education_bonus),
                    "free_text_field": free_text_field,
                    "message": message,
                    "check": boolean_translate(check),
                    "event": event.name,
                    "attend_status": attend_status,
                    "label": event.label,
                    "start": event.get_first_day_start_date(),
                    "addresses_string": addresses_string,
                    "speaker_string": speaker_string,
                }
            elif event.registration_form == "m":

                if takes_part_in_mv == "n" and vote_transfer:
                    transfer_string = f"Du nimmst an der Mitgliederversammlung nicht teil und überträgst deine Stimme für alle Abstimmungen und Wahlen inhaltlich unbegrenzt an: {vote_transfer}"
                else:
                    transfer_string = ""

                if takes_part_in_mv == "y":
                    member_type_string = "Du bist " + " ".join(member_type_label) + "."
                else:
                    member_type_string = ""

                waiting_string = ""
                if takes_part_in_zw and attend_status == "waiting":
                    waiting_string = "Die Zukunftswerkstatt ist bereits ausgebucht, wir führen deinen Namen gern auf einer Warteliste. Sobald ein Platz frei wird, informieren wir dich."

                event_list = []
                info_string = ""
                if takes_part_in_mv == "y":
                    event_list.append("Mitgliederversammlung, 17.9.2021")
                    info_string = "Weitere Informationen und der Zugangscode für das Wahltool werden nach dem Anmeldeschluss, wenige Tage vor den Veranstaltungen, versandt."
                if takes_part_in_zw == "y":
                    event_list.append("Zukunftswerkstatt, 18./19.9.2021")
                    if takes_part_in_mv != "y":
                        info_string = "Weitere Informationen werden nach dem Anmeldeschluss, wenige Tage vor der Veranstaltung, versandt."

                if takes_part_in_mv == "n" and takes_part_in_zw == "n":
                    event_list.append("Keine der beiden Veranstaltungen.")
                formatting_dict = {
                    "firstname": firstname,
                    "lastname": lastname,
                    "event": " / ".join(event_list),
                    "start": event.get_first_day_start_date(),
                    "email": email,
                    "takes_part_in_mv": takes_part_in_mv,
                    "member_type": member_type_string,
                    "transfer_string": transfer_string,
                    "info_string": info_string,
                    "waiting_string": waiting_string,
                    "takes_part_in_zw": takes_part_in_zw,
                    "mv_check": mv_check,
                    "zw_check": zw_check,
                    "vote_transfer": vote_transfer,
                    "vote_transfer_check": vote_transfer_check,
                    "attend_status": attend_status,
                }

            elif event.registration_form == "f":

                food_pref_list = []

                food_pref_list.append(food_preferences)

                # print("food: ", food_preferences, food_pref_list)

                formatting_dict = {
                    "firstname": firstname,
                    "lastname": lastname,
                    "event": "Fachtagung Freies Lektorat 2022",
                    "start": event.get_first_day_start_date().strftime("%d.%m.%Y"),
                    "address_line": address_line,
                    "street": street,
                    "postcode": postcode,
                    "city": city,
                    "email": email,
                    "phone": phone,
                    "ws2022": ws2022 if ws2022 else "-",
                    "ws_alter": ws_alter if ws_alter else "-",
                    "takes_part_in_mv": boolean_translate(takes_part_in_mv),
                    # "takes_part_in_ft": boolean_translate(takes_part_in_ft),
                    "having_lunch": boolean_translate(having_lunch),
                    "tour": tour,
                    "networking": boolean_translate(networking),
                    "yoga": boolean_translate(yoga),
                    "celebration": boolean_translate(celebration),
                    "food_preferences": choices_to_string(
                        food_pref_list, FOOD_PREFERENCE_CHOICES
                    ),
                    "remarks": remarks,
                    "memberships": choices_to_string(memberships, MEMBERSHIP_CHOICES),
                    "nomember": boolean_translate(nomember),
                }

            messages_dict = {
                "s": (
                    "Vielen Dank für Ihre Anmeldung. Wir melden uns bei Ihnen mit weiteren Informationen.",
                    "Vielen Dank für Ihre Anmeldung. Sie wurden auf die Warteliste gesetzt und werden benachrichtigt, wenn ein Platz frei wird.",
                )[attend_status == "waiting"],
                "m": "Vielen Dank für deine Anmeldung. Weitere Informationen und der Zugangscode für das Wahltool (falls du an der MV teilnimmst) werden nach dem Anmeldeschluss, wenige Tage vor den Veranstaltungen, versandt. Falls die Zukunftswerkstatt ausgebucht ist, setzen wir dich gerne auf die Warteliste.",
                "f": "Vielen Dank für deine Anmeldung. Weitere Informationen werden nach dem Anmeldeschluss versandt.",
            }
            messages.success(request, messages_dict[event.registration_form])

            # save new member
            new_member = EventMember.objects.latest("date_created")
            new_member.save()
            if event.registration_form == "s" or event.registration_form == "f":
                try:
                    send_email(
                        addresses,
                        subject,
                        settings.DEFAULT_FROM_EMAIL,
                        mail_to_admin_template_name,
                        formatting_dict=formatting_dict,
                    )
                    # print("mail to event admin sent")
                    new_member.mail_to_admin = True
                    new_member.save()
                except BadHeaderError:
                    return HttpResponse("Invalid header found.")

            # mail to member

            # TODO auch für FoBis freischalten, wenn Fobis einverstanden
            if event.registration_form == "m" or event.registration_form == "f":
                # print(f"member email: {email}")
                logger.debug(f"Anmeldung email: {email}")
                member_addresses_list = []
                member_addresses_list.append(email)
                member_addresses = {"to": member_addresses_list}
                try:
                    send_email(
                        member_addresses,
                        subject,
                        settings.FT_FROM_EMAIL,
                        mail_to_member_template_name,
                        formatting_dict=formatting_dict,
                    )
                    # print("mail to event member sent")
                    logger.info(f"{datetime.now()}: Mail an {email} verschickt")
                    new_member.mail_to_member = True
                    new_member.save()
                except BadHeaderError:
                    return HttpResponse("Invalid header found.")

            return redirect("event-detail", event.slug)
    return render(
        request,
        form_template,
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
            start = "2022-01-01"
        if request.GET.get("end"):
            end = request.GET.get("end")
        else:
            end = "2022-12-01"
        events = (
            Event.objects.exclude(event_days=None)
            .filter(first_day__gt=start, first_day__lt=end)
            .filter(pub_status="PUB")
            .order_by("first_day")
        )
        print("Events:", events)
        serializer = EventSerializer(events, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventMembersListView(GroupTestMixin, SingleTableView):
    model = EventMember
    table_class = EventMembersTable
    template_name = "events/members_list.html"

    def get_queryset(self):
        event_members = EventMember.objects.filter(event__label=self.kwargs["event"])
        query_ln = self.request.GET.get("member_lastname")
        query_fn = self.request.GET.get("member_firstname")
        query_email = self.request.GET.get("member_email")
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
        context["event_label"] = self.kwargs["event"]
        # print(context)
        return context


class FTEventMembersListView(GroupTestMixin, SingleTableView):
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


class EventMemberDetailView(GroupTestMixin, DetailView):
    model = EventMember
    template_name = "events/member_detail.html"


class FTEventMemberDetailView(GroupTestMixin, DetailView):
    model = EventMember
    template_name = "events/ft_member_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super(FTEventMemberDetailView, self).get_context_data(*args, **kwargs)
        obj = self.get_object()
        # convert jsonfield = string in db to real json
        data = obj.data
        context["data"] = data
        return context


class EventMemberUpdateView(GroupTestMixin, UpdateView):
    model = EventMember
    fields = ["firstname", "lastname", "email", "attend_status"]
    template_name = "events/member_update.html"

    def get_success_url(self):
        pk = self.kwargs["pk"]

        label = EventMember.objects.get(pk=pk).event.label
        return reverse("members", kwargs={"event": label})


class FTEventMemberUpdateView(GroupTestMixin, UpdateView):
    model = EventMember

    form_class = FTEventMemberForm

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


class EventMemberCreateView(GroupTestMixin, CreateView):
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
        self.object.check = True
        self.object.event = self.event
        if self.event_members.count() >= self.event.capacity:
            self.object.attend_status = "waiting"
        else:
            self.object.attend_status = "registered"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("members", kwargs={"event": self.event.label})


class EventMemberDeleteView(GroupTestMixin, DeleteView):
    model = EventMember
    success_url = reverse_lazy("members-dashboard")
    template_name = "events/confirm_member_delete.html"


class EventUpdateCapacityView(GroupTestMixin, UpdateView):
    model = Event
    template_name = "events/update_capacity_form.html"
    form_class = EventUpdateCapacityForm

    def get_success_url(self):
        return reverse_lazy("members-dashboard")


@login_required
@user_passes_test(is_member_of_mv_orga)
def export_members_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Vorname",
            "Nachname",
            "E-Mail",
            "Datum",
            "Mitgliedschaft",
            "MV",
            "Stimmübertragung",
            "Check Stimmübertragung",
            "Einverständnis MV",
            "ZW",
            "Einverständnis ZW",
            "Status",
        ]
    )

    members_mv = EventMember.objects.filter(event__label="Online-MV2021").values_list(
        "firstname",
        "lastname",
        "email",
        "date_created",
        "member_type",
        "vote_transfer",
        "vote_transfer_check",
        "check",
    )
    members_zw = EventMember.objects.filter(event__label="zukunft2021").values_list(
        "firstname",
        "lastname",
        "email",
        "date_created",
        "member_type",
        "check",
        "attend_status",
    )
    for member in members_mv:
        member = list(member)
        member[3] = member[3].strftime("%d.%m.%y %H:%M")
        member.insert(5, "x")
        if (
            EventMember.objects.filter(event__label="zukunft2021")
            .filter(email=member[2])
            .exists()
        ):
            member.append("x")
            member.append(
                EventMember.objects.filter(event__label="zukunft2021")
                .filter(email=member[2])[0]
                .check
            )
            member.append(
                EventMember.objects.filter(event__label="zukunft2021")
                .filter(email=member[2])[0]
                .attend_status
            )

        writer.writerow(member)
    for member in members_zw:
        member = list(member)
        member[3] = member[3].strftime("%d.%m.%y %H:%M")

        if (
            not EventMember.objects.filter(event__label="Online-MV2021")
            .filter(email=member[2])
            .exists()
        ):
            member.insert(5, "")
            member.insert(6, "")
            member.insert(7, "")
            member.insert(8, "")
            member.insert(9, "x")

            writer.writerow(member)

    return response


@login_required
@user_passes_test(is_member_of_mv_orga)
def export_mv_members_csv(request):
    # print(f"request: {request.GET}")
    query_ln = request.GET.get("member_lastname")
    query_fn = request.GET.get("member_firstname")
    query_email = request.GET.get("member_email")
    query_vote_transfer_yes = request.GET.get("member_vote_transfer_yes")
    query_vote_transfer_no = request.GET.get("member_vote_transfer_no")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members_mv.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Vorname",
            "Nachname",
            "E-Mail",
            "Datum",
            "Mitgliedschaft",
            "Stimmübertragung",
            "Check Stimmübertragung",
            "Einverständnis MV",
        ]
    )

    members_mv = EventMember.objects.filter(event__label="Online-MV2021")
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
        "date_created",
        "member_type",
        "vote_transfer",
        "vote_transfer_check",
        "check",
    )

    for member in members_mv:
        member = list(member)
        member[3] = member[3].strftime("%d.%m.%y %H:%M")

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

    for member in EventMember.objects.filter(event__label="ffl_mv_2022"):
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

    for member in EventMember.objects.filter(event__label="ffl_mv_2022"):
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
            event__label="ffl_mv_2022"
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
    qs = EventMember.objects.filter(event__label="ffl_mv_2022")
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

    members_ft = EventMember.objects.filter(event__label="ffl_mv_2022")

    data_list = members_ft.values_list(
        "data",
    )

    for member in members_ft:
        json_object = member.data
        values = list(json_object.values())
        writer.writerow(values)

    return response


@login_required
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
    ftm = EventMember.objects.filter(event__label="ffl_mv_2022").values_list(
        "data", flat=True
    )

    # the data json objects are returned as strings, so convert to list of dicts
    # with json.loads
    # ftm_list = [json.loads(j) for j in list(ftm)] # no more needed
    ftm_list = list(ftm)

    # creating pandas Data Frame
    df = pd.DataFrame(ftm_list)
    df.to_excel(response)

    return response
