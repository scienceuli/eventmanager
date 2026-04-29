import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from events.models import Event, EventCategory, EventFormat, EventLocation, EventMember
from events.core_models import EmailBlacklist
from events.services.registration import EventRegistrationService, RegistrationResult


def make_form_data():
    """Return minimal valid form cleaned_data for standard registration."""
    return {
        "academic": "",
        "firstname": "Max",
        "lastname": "Mustermann",
        "email": "max@example.com",
        "address_line": "",
        "company": "",
        "street": "Teststr. 1",
        "city": "Berlin",
        "state": "",
        "postcode": "10115",
        "country": "DE",
        "phone": "030123456",
        "vfll": False,
        "memberships": [],
        "attention": "",
        "attention_other": "",
        "education_bonus": False,
        "message": "",
        "free_text_field": "",
        "agree": True,
        "newsletter": False,
    }


def make_mock_form(data=None):
    """Create a mock form with cleaned_data."""
    form = MagicMock()
    form.cleaned_data = data or make_form_data()
    return form


class RegistrationServiceTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="testcat")
        cls.eventformat = EventFormat.objects.create(name="testformat")
        cls.location = EventLocation.objects.create(title="testloc")

        cls.event = Event.objects.create(
            name="Test Event",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            label="test-event",
            price="100.00",
            registration_form="s",
        )

        cls.service = EventRegistrationService()


class RegisterSuccessTest(RegistrationServiceTestBase):

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_successful_registration(self):
        form = make_mock_form()
        result = self.service.register(form, self.event)

        self.assertTrue(result.success)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.successes), 1)

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_creates_event_member(self):
        form = make_mock_form()
        initial_count = EventMember.objects.filter(event=self.event).count()
        self.service.register(form, self.event)
        self.assertEqual(
            EventMember.objects.filter(event=self.event).count(), initial_count + 1
        )

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_member_has_survey_token(self):
        form = make_mock_form()
        self.service.register(form, self.event)
        member = EventMember.objects.filter(
            event=self.event, email="max@example.com"
        ).last()
        self.assertIsNotNone(member.survey_token)

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_success_message_for_registered(self):
        form = make_mock_form()
        result = self.service.register(form, self.event)
        self.assertIn("Test Event", result.successes[0])

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_waiting_status_when_event_full(self):
        self.event.capacity = 0
        self.event.save()
        form = make_mock_form()
        result = self.service.register(form, self.event)
        self.assertTrue(result.success)
        member = EventMember.objects.filter(
            event=self.event, email="max@example.com"
        ).last()
        self.assertEqual(member.attend_status, "waiting")
        # reset
        self.event.capacity = 15
        self.event.save()


class RegisterBlacklistTest(RegistrationServiceTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        EmailBlacklist.objects.create(email="blocked@example.com")

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_blacklisted_email_rejected(self):
        data = make_form_data()
        data["email"] = "blocked@example.com"
        form = make_mock_form(data)
        result = self.service.register(form, self.event)

        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("nicht verarbeitet", result.errors[0])

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_blacklisted_email_does_not_create_member(self):
        data = make_form_data()
        data["email"] = "blocked@example.com"
        form = make_mock_form(data)
        initial_count = EventMember.objects.filter(event=self.event).count()
        self.service.register(form, self.event)
        self.assertEqual(
            EventMember.objects.filter(event=self.event).count(), initial_count
        )


class RegisterDuplicateTest(RegistrationServiceTestBase):

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_duplicate_email_rejected(self):
        # Register once
        form = make_mock_form()
        self.service.register(form, self.event)

        # Try again with same email
        form2 = make_mock_form()
        result = self.service.register(form2, self.event)

        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("bereits eine Anmeldung", result.errors[0])

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=False)
    def test_duplicate_allowed_when_setting_off(self):
        form = make_mock_form()
        self.service.register(form, self.event)

        form2 = make_mock_form()
        result = self.service.register(form2, self.event)

        self.assertTrue(result.success)


class RegisterReturnsStrategyTest(RegistrationServiceTestBase):

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    def test_result_contains_strategy(self):
        form = make_mock_form()
        result = self.service.register(form, self.event)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.strategy)

    @override_settings(NO_MEMBER_DUPLICATES_ALLOWED=True)
    @patch("events.services.notification_service.send_registration_emails")
    def test_register_does_not_send_notifications(self, mock_send):
        form = make_mock_form()
        self.service.register(form, self.event)
        mock_send.assert_not_called()


class RegistrationResultDataclassTest(TestCase):

    def test_default_values(self):
        result = RegistrationResult()
        self.assertFalse(result.success)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.successes, [])

    def test_independent_instances(self):
        r1 = RegistrationResult()
        r2 = RegistrationResult()
        r1.errors.append("error")
        self.assertEqual(len(r2.errors), 0)
