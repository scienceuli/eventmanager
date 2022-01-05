import datetime

from django.db import IntegrityError
from django.test import RequestFactory, TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib import messages
from django.core import mail
from django.http import HttpRequest


from events.models import (
    Event,
    EventDay,
    EventFormat,
    EventLocation,
    EventOrganizer,
    EventCategory,
    EventSpeaker,
    EventSponsor,
    EventMember,
)

from events.forms import SymposiumForm, EventModelForm

from events.views import event_add_member, EventMembersListView
from events.email_template import EmailTemplate


# class EventHighlightTests(TestCase):
#    def test_single_instance(self):
#        constraint_name = "events_eventhighlight_single_instance"
#        with self.assertRaisesMessage(IntegrityError, constraint_name):
#            EventHighlight.objects.create(
#                id=2,
#                event=Event.objects.all().first(),
#
#
#         )

#################
# setup
#################


#################
# Models
#################


class EventCategoryTest(TestCase):
    def setUp(self) -> None:
        self.eventcategory = EventCategory(
            name="name",
            title="title",
            description="description",
            singular="singular",
            position=3,
        )
        self.eventcategory.save()

    def test_update_eventcategory_position(self):
        self.eventcategory.position = 4
        self.eventcategory.save()
        self.assertEqual(self.eventcategory.position, 4)


#################
# Forms
#################


class SymposiumFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test", password="12test12", email="test@example.com"
        )
        self.user.save()

    def test_mv_check_missing(self):
        form = SymposiumForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "takes_part_in_mv": "y",
                "takes_part_in_zw": "n",
                "mv_check": False,
                "zw_check": True,
            }
        )

        self.assertEqual(
            form.errors["mv_check"],
            ["Bestätigung der Einverständniserklärung notwendig für Teilnahme"],
        )

    def test_zw_check_missing(self):
        form = SymposiumForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "takes_part_in_mv": "n",
                "takes_part_in_zw": "y",
                "zw_check": False,
                "mv_check": True,
            }
        )

        self.assertEqual(
            form.errors["zw_check"],
            ["Bestätigung der Einverständniserklärung notwendig für Teilnahme"],
        )

    def test_vote_transfer(self):
        form = SymposiumForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "takes_part_in_mv": "y",
                "vote_transfer": "Lisa",
                "takes_part_in_zw": "n",
                "mv_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer"],
            ["Stimmübertragung nur bei Nichtteilnahme möglich"],
        )

    def test_vote_transfer_only_for_standard_members(self):
        form = SymposiumForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "k",
                "takes_part_in_mv": "n",
                "vote_transfer": "Lisa",
                "vote_transfer_check": True,
                "takes_part_in_zw": "y",
                "mv_check": True,
                "zw_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer"],
            ["Stimmübertragung nur für ordentliche Mitglieder möglich"],
        )

    def test_takes_part(self):
        form = SymposiumForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "takes_part_in_mv": "n",
                "takes_part_in_zw": "n",
                "mv_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer"],
            [
                "Bitte mindestens eine Teilnahme (MV oder Zukunftswerkstatt) angeben oder für die MV eine Stimmübertragung festlegen!"
            ],
        )


############
# views
############


class SigninTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test", password="12test12", email="test@example.com"
        )
        self.user.save()

    def tearDown(self):
        self.user.delete()

    def test_correct(self):
        user = authenticate(username="test", password="12test12")
        self.assertTrue((user is not None) and user.is_authenticated)

    def test_wrong_username(self):
        user = authenticate(username="wrong", password="12test12")
        self.assertFalse(user is not None and user.is_authenticated)

    def test_wrong_pssword(self):
        user = authenticate(username="test", password="wrong")
        self.assertFalse(user is not None and user.is_authenticated)


class EventViewsTests(TestCase):
    def setUp(self) -> None:
        self.eventcategory = EventCategory(
            name="name",
            title="title",
            description="description",
            singular="singular",
            position=3,
        )
        self.eventcategory.save()

        self.eventformat = EventFormat(
            name="name",
            description="description",
        )
        self.eventformat.save()

        self.eventlocation = EventLocation(
            title="title",
            url="testlocation@locations.de",
        )
        self.eventlocation.save()

        self.eventspeaker = EventSpeaker(
            first_name="first_name",
            last_name="last_name",
            email="eventspeaker@speakers.de",
        )
        self.eventspeaker.save()

        self.eventsponsor = EventSponsor(
            first_name="first_name",
            last_name="last_name",
            email="eventsponsor@sponsors.de",
        )
        self.eventsponsor.save()

        self.event = Event(
            category=self.eventcategory,
            eventformat=self.eventformat,
            name="name",
            label="label",
            description="description",
            target_group="target_group",
            prerequisites="prerequisites",
            objectives="objectives",
            location=self.eventlocation,
            fees="fees",
            registration="registration",
        )
        self.event.save()
        self.m_event = Event(
            category=self.eventcategory,
            eventformat=self.eventformat,
            name="m_name",
            label="Online-MV2021",
            description="description",
            target_group="target_group",
            prerequisites="prerequisites",
            objectives="objectives",
            location=self.eventlocation,
            fees="fees",
            registration="registration",
            registration_form="m",
        )
        self.m_event.save()

        self.z_event = Event(
            category=self.eventcategory,
            eventformat=self.eventformat,
            name="z_name",
            label="zukunft2021",
            description="description",
            target_group="target_group",
            prerequisites="prerequisites",
            objectives="objectives",
            location=self.eventlocation,
            fees="fees",
            registration="registration",
            registration_form="m",
        )
        self.z_event.save()

        self.event.speaker.add(self.eventspeaker)
        self.event.sponsors.add(self.eventsponsor)

        self.eventmember = EventMember(
            event=self.event,
            firstname="firstname",
            lastname="lastname",
            email="newmember@members.de",
            phone="12345",
            vfll=True,
            attend_status="registered",
        )

        self.anmeldung = EmailTemplate(
            name="anmeldung",
            text_template="standard test",
            html_template="<p>test</p>",
        )
        self.anmeldung.save()
        self.mv_zw_anmeldung = EmailTemplate(
            name="mv_zw_anmeldung",
            text_template="mv zw test",
            html_template="<p>mv zw test</p>",
        )
        self.mv_zw_anmeldung.save()
        self.mv_zw_bestaetigung = EmailTemplate(
            name="mv_zw_bestaetigung",
            text_template="mv zw bestaetigung test",
            html_template="<p>mv zw bestaetigung test</p>",
        )
        self.mv_zw_bestaetigung.save()

        # ref for using messages in tests
        # https://stackoverflow.com/questions/15852317/you-cannot-add-messages-without-installing-django-contrib-messages-middleware-me

        settings.MESSAGE_STORAGE = (
            "django.contrib.messages.storage.cookie.CookieStorage"
        )
        self.factory = RequestFactory()

        self.client = Client()

    def test_update_event_capacity(self):
        event = self.event
        event.capacity = 20
        event.save()
        self.assertEqual(event.capacity, 20)

    def test_update_attend_status(self):
        event = self.event
        event.attend_status = "waiting"
        event.save()
        self.assertEqual(event.attend_status, "waiting")

    def test_form_valid_on_add_member_view(self):
        event = self.event
        client = Client()
        data = {
            "firstname": "Timo",
            "lastname": "Test",
            "street": "Teststraße 5",
            "city": "Teststadt",
            "postcode": "12345",
            "email": "timo@test.de",
            "phone": "999999",
            "vfll": True,
            "check": True,
        }
        print(f"event slug: {event.slug}")
        path = reverse("event-add-member", kwargs={"slug": event.slug})
        self.request = self.factory.post(path, data=data)
        self.request._messages = messages.storage.default_storage(self.request)

        # self.request = self.factory.get(path)
        self.response = event_add_member(self.request, slug=event.slug)
        # self.response = event_add_member(self.request) # this will submit the form and run the form_valid.

        # assert self.response.status_code == 200, "Should be status code 200"
        assert True

        member = EventMember.objects.get(lastname="Test")
        # response = client.get(member.email)
        assert member.email == "timo@test.de"

    def test_form_valid_on_add_member_to_mv_event_view(self):
        mevent = self.m_event
        print(mevent.registration_form)
        m_data = {
            "firstname": "Timo",
            "lastname": "MVTest",
            "email": "mvtimo@test.de",
            "takes_part_in_mv": "y",
            "takes_part_in_zw": "n",
            "member_type": "o",
            "mv_check": True,
            "zw_check": True,
        }
        print(f"mevent slug: {mevent.slug}")

        path = reverse("event-add-member", kwargs={"slug": mevent.slug})
        self.request = self.factory.post(path, data=m_data)
        self.request._messages = messages.storage.default_storage(self.request)

        # self.request = self.factory.get(path)
        self.response = event_add_member(self.request, slug=mevent.slug)
        # self.response = event_add_member(self.request) # this will submit the form and run the form_valid.

        # assert self.response.status_code == 200, "Should be status code 200"
        assert True

        mvmember = EventMember.objects.get(lastname="MVTest")
        # response = client.get(member.email)
        assert mvmember.email == "mvtimo@test.de"
        assert mvmember.vote_transfer_check == False

        # ref for email testing
        # https://timonweb.com/django/testing-emails-in-django/

        assert len(mail.outbox) == 1  # "Inbox is not empty"
        assert mail.outbox[0].subject == "Anmeldung zur MV / Zukunftswerkstatt"
        assert mail.outbox[0].body == "mv zw bestaetigung test"

    # assert mail.outbox[0].from_email == "from@example.com"
    # assert mail.outbox[0].to == ["to@example.com"]

    def test_form_valid_on_add_member_to_mv_and_zw_event_view(self):
        mevent = self.m_event
        zevent = self.z_event
        m_data = {
            "firstname": "Timo",
            "lastname": "MVTest",
            "email": "mvtimo@test.de",
            "takes_part_in_mv": "y",
            "takes_part_in_zw": "y",
            "member_type": "o",
            "mv_check": True,
            "zw_check": True,
        }

        path = reverse("event-add-member", kwargs={"slug": mevent.slug})
        self.request = self.factory.post(path, data=m_data)
        self.request._messages = messages.storage.default_storage(self.request)

        # self.request = self.factory.get(path)
        self.response = event_add_member(self.request, slug=mevent.slug)
        # self.response = event_add_member(self.request) # this will submit the form and run the form_valid.

        # assert self.response.status_code == 200, "Should be status code 200"
        assert True

        mvmember = EventMember.objects.filter(lastname="MVTest")
        assert len(mvmember) == 2

        assert mvmember[0].event.label == "Online-MV2021"
        assert mvmember[1].event.label == "zukunft2021"

        # response = client.get(member.email)
        # assert mvmember.email == "mvtimo@test.de"

        # assert len(mail.outbox) == 1  # "Inbox is not empty"
        # assert mail.outbox[0].subject == "Anmeldung zur MV / Zukunftswerkstatt"
        # assert mail.outbox[0].body == "mv zw test"

    # assert mail.outbox[0].from_email == "from@example.com"
    # assert mail.outbox[0].to == ["to@example.com"]

    def test_listview_mv_members_url_exists_at_desired_location(self):
        request = self.factory.get("/members/Online-MV2021")
        response = EventMembersListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_lists_all_mv_members(self):
        # Get second page and confirm it has (exactly) remaining 3 items
        response = self.client.get("/members/Online-MV2021/")
        table = response.context["object_list"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell("lastname"), "MVTest")


##################################################
# test of views and forms for internal vfll-events
##################################################


class TestEventModelForm(TestCase):
    def setUp(self):
        EventCategory.objects.create(
            name="name",
            title="title",
            description="description",
            singular="singular",
            position=1,
        )
        # create event format
        EventFormat.objects.create(name="Testformat")
        # create location
        EventLocation.objects.create(title="Testlocation")
        # create organizer
        EventOrganizer.objects.create(
            name="Test Organizer", url="https://www.testorganizer.de"
        )

    def test_empty_form(self):
        form = EventModelForm()
        # testing one field
        self.assertIn("name", form.fields)
        # assertInHtml raises Error, use assertIn instead
        self.assertIn('<input type="text" name="name"', str(form))

    def test_full_form_with_two_days(self):
        response = self.client.get(reverse("event-create-nm"))
        self.assertEqual(response.status_code, 200)
        # print(response.context["days"].management_form)
        data = {
            "name": "event 2 just for testing",
            "category": EventCategory.objects.get(id=1),
            "eventformat": EventFormat.objects.get(id=1),
            "pub_status": "UNPUB",
            "fees": "no costs",
            "location": EventLocation.objects.get(id=1),
            "organizer": EventOrganizer.objects.get(id=1),
            "event_days-TOTAL_FORMS": "2",
            "event_days--INITIAL_FORMS": "0",
            "event_days--MIN_NUM_FORMS": "0",
            "event_days--MAX_NUM_FORMS": "1000",
            "event_days-0-start_date": datetime.date(2022, 2, 5),
            "event_days-0-start_time": datetime.time(8, 0),
            "event_days-0-end_time": datetime.time(12, 0),
            "event_days-0-start_date": datetime.date(2022, 2, 6),
            "event_days-1-start_time": datetime.time(8, 0),
            "event_days-1-end_time": datetime.time(12, 0),
        }
        response = self.client.post(reverse("event-create-nm"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(EventDay.objects.count(), 2)

    def test_can_create_event(self):
        request = HttpRequest()
        request.POST = {
            "name": "event just for testing",
            "category": EventCategory.objects.get(id=1),
            "eventformat": EventFormat.objects.get(id=1),
            "pub_status": "UNPUB",
            "fees": "no costs",
            "location": EventLocation.objects.get(id=1),
            "organizer": EventOrganizer.objects.get(id=1),
            "event_days-TOTAL_FORMS": "1",
            "event_days--INITIAL_FORMS": "0",
            "event_days--MIN_NUM_FORMS": "0",
            "event_days--MAX_NUM_FORMS": "1000",
            "event_days-0-start_date": datetime.date(2022, 2, 5),
            "event_days-0-start_time": datetime.time(8, 0),
            "event_days-0-end_time": datetime.time(12, 0),
        }
        form = EventModelForm(request.POST)
        form.save()
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(EventDay.objects.count(), 1)
