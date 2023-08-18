import datetime

from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


from events.models import (
    Event,
    EventFormat,
    EventLocation,
    EventCategory,
    EventMember,
)

from events.forms import MV2023Form, EventMemberForm

from events.views import event_add_member, EventMembersListView
from events.email_template import EmailTemplate

from contextlib import contextmanager
from django.core.exceptions import ValidationError


##############################
# Validation Error Test Helper
##############################
# ref:


class ValidationAssertionsMixin(SimpleTestCase):
    @contextmanager
    def assertRaisesCode(self, code: str):
        with self.assertRaises(ValidationError) as cm:
            yield cm

        self.assertEqual(code, cm.exception.code)


##################
# MV Form
##################


class MV2023FormTest(ValidationAssertionsMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test", password="12test12", email="test@example.com"
        )
        self.user.save()
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")
        self.event = Event(
            name="mv",
            category=category,
            eventformat=eventformat,
            location=location,
            price="0.00",
        )
        self.event.save()
        self.event_member = EventMember.objects.create(
            event=self.event,
            lastname="Lachmal",
            firstname="Lilly",
            email="lilly@lachmal.de",
            check=True,
            member_type="o",
        )

    def test_mv_form_without_vote_transfer_is_valid(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "mv_check": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_mv_form_with_vote_transfer_is_valid(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "mv_check": False,
                "vote_transfer": "Lilly",
                "vote_transfer_check": True,
            }
        )
        self.assertFalse(form.is_valid())

    def test_mv_form_mv_check_missing(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "mv_check": False,
            }
        )

        self.assertEqual(
            form.errors["mv_check"],
            ["Bestätigung der Einverständniserklärung notwendig für Teilnahme"],
        )

    def test_mv_form_vote_transfer_without_check(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "vote_transfer": "Lisa",
                "vote_transfer_check": False,
                "mv_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer_check"],
            ["Bitte für Stimmübertragung bestätigen"],
        )

    def test_mv_form_vote_transfer_check_without_vote_transfer(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "o",
                "vote_transfer": "",
                "vote_transfer_check": True,
                "mv_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer"],
            ["Bitte ordentliches VFLL-Mitglied angeben"],
        )

    def test_mv_form_vote_transfer_only_for_standard_members(self):
        form = MV2023Form(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "member_type": "k",
                "vote_transfer": "Lisa",
                "vote_transfer_check": True,
                "mv_check": True,
            }
        )
        self.assertEqual(
            form.errors["vote_transfer"],
            ["Stimmübertragung nur für ordentliche Mitglieder möglich"],
        )

    # def test_mv_form_email_already_registerd(self):
    #     form = MV2023Form(
    #         data={
    #             "firstname": "Lilly",
    #             "lastname": "Lachnicht",
    #             "email": "lilly@lachmal.de",
    #             "member_type": "o",
    #             "mv_check": True,
    #         }
    #     )
    #     with self.assertRaisesCode("email_already_registered"):
    #         form.is_valid()


##################
# Standard Form
##################


class EventMemberFormTest(ValidationAssertionsMixin, TestCase):
    def test_standard_form_is_valid_with_required_fields(self):
        form = EventMemberForm(
            data={
                "firstname": "Hans",
                "lastname": "Huber",
                "email": "hans@huber.de",
                "street": "teststraße",
                "city": "teststadt",
                "postcode": "12345",
                "country": "DE",
            }
        )
        self.assertTrue(form.is_valid())
