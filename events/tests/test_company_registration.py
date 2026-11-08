from datetime import date, timedelta

from django.test import TestCase

from events.forms import EventMemberForm
from events.models import Event, EventCategory, EventFormat, EventLocation
from events.utils.form_utils import get_additional_form_data


def make_post_data(**overrides):
    data = {
        "firstname": "Erika",
        "lastname": "Muster",
        "email": "erika@example.com",
        "company": "Verlag GmbH",
        "street": "Firmenweg 1",
        "postcode": "10115",
        "city": "Berlin",
        "country": "DE",
    }
    data.update(overrides)
    return data


class EventMemberFormCompanyTest(TestCase):
    def test_employed_requires_company_email(self):
        form = EventMemberForm(make_post_data(employed="on"))
        self.assertFalse(form.is_valid())
        self.assertIn("company_email", form.errors)

    def test_employed_requires_company_and_name(self):
        form = EventMemberForm(
            make_post_data(
                employed="on",
                company="",
                firstname="",
                company_email="rechnung@verlag.de",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("company", form.errors)
        self.assertIn("firstname", form.errors)

    def test_employed_clears_member_discounts(self):
        form = EventMemberForm(
            make_post_data(
                employed="on",
                company_email="rechnung@verlag.de",
                vfll="on",
                memberships=["vdu"],
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["employed"])
        self.assertFalse(form.cleaned_data["vfll"])
        self.assertEqual(form.cleaned_data["memberships"], [])
        self.assertFalse(form.cleaned_data["education_bonus"])

    def test_private_registration_ignores_company_email(self):
        form = EventMemberForm(
            make_post_data(company_email="rechnung@verlag.de", vfll="on")
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["employed"])
        self.assertEqual(form.cleaned_data["company_email"], "")
        self.assertTrue(form.cleaned_data["vfll"])


class CompanyFormDataTest(TestCase):
    def test_additional_form_data_contains_company_fields(self):
        event = Event.objects.create(
            name="Test Event",
            category=EventCategory.objects.create(name="cat"),
            eventformat=EventFormat.objects.create(name="fmt"),
            location=EventLocation.objects.create(title="loc"),
            label="test-company",
            price="100.00",
            first_day=date.today() + timedelta(days=30),
        )
        form = EventMemberForm(
            make_post_data(employed="on", company_email="rechnung@verlag.de")
        )
        self.assertTrue(form.is_valid(), form.errors)
        data = get_additional_form_data(form, event, "s")
        self.assertTrue(data["employed"])
        self.assertEqual(data["company_email"], "rechnung@verlag.de")
        self.assertFalse(data["vfll"])
