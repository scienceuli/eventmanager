import os
import csv
import json
import pandas as pd
from itertools import chain
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

from django.contrib.auth.models import User, Group

from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth.mixins import UserPassesTestMixin, PermissionRequiredMixin

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

from datetime import date, datetime

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

from .utils import yes_no_to_boolean, make_bar_plot_from_dict, get_utilisations

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

logging.basicConfig(filename="mail_sent.log", encoding="utf-8", level=logging.DEBUG)

#

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

from .tables import EventMembersTable, FTEventMembersTable

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
    SymposiumForm,
    AddMemberForm,
    EventUpdateCapacityForm,
    EventCategoryFilterForm,
    FTEventMemberForm,
)

from shop.forms import CartAddEventForm

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
def old_event_add_member(request, slug):
    event = get_object_or_404(Event, slug=slug)
    mail_to_admin_template_name = get_mail_to_admin_template_name(
        event.registration_form
    )
    mail_to_member_template_name = get_mail_to_member_template_name(
        event.registration_form
    )
    form_template = get_form_template(event.registration_form)

    # get the workshop and tour capacity utilisations for fachtagung
    if event.label == "ffl_mv_2024":
        ws_utilisations, tour_utilisations = get_utilisations(event)

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
