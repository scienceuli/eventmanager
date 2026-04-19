from unittest.mock import patch, MagicMock

from django.test import TestCase

from events.models import Event, EventCategory, EventFormat, EventLocation, EventMember
from events.services.notification_service import NotificationService


class NotificationServiceTestBase(TestCase):
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

        cls.member = EventMember.objects.create(
            event=cls.event,
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            attend_status="registered",
        )

        cls.service = NotificationService()

    def setUp(self):
        # Reset mail flags before each test
        self.member.mail_to_admin = False
        self.member.mail_to_member = False
        self.member.save()


class SendNotificationEmailsTest(NotificationServiceTestBase):

    @patch("events.services.notification_service.send_registration_emails")
    def test_both_emails_sent(self, mock_send):
        mock_send.return_value = (True, True)
        strategy = MagicMock()
        strategy.build_formatting_dict.return_value = {"key": "value"}

        form = MagicMock()
        vfll_sent, member_sent = self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        self.assertTrue(vfll_sent)
        self.assertTrue(member_sent)
        self.member.refresh_from_db()
        self.assertTrue(self.member.mail_to_admin)
        self.assertTrue(self.member.mail_to_member)

    @patch("events.services.notification_service.send_registration_emails")
    def test_only_admin_email_sent(self, mock_send):
        mock_send.return_value = (True, False)
        strategy = MagicMock()
        strategy.build_formatting_dict.return_value = {}

        form = MagicMock()
        vfll_sent, member_sent = self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        self.assertTrue(vfll_sent)
        self.assertFalse(member_sent)
        self.member.refresh_from_db()
        self.assertTrue(self.member.mail_to_admin)
        self.assertFalse(self.member.mail_to_member)

    @patch("events.services.notification_service.send_registration_emails")
    def test_no_emails_sent(self, mock_send):
        mock_send.return_value = (False, False)
        strategy = MagicMock()
        strategy.build_formatting_dict.return_value = {}

        form = MagicMock()
        vfll_sent, member_sent = self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        self.assertFalse(vfll_sent)
        self.assertFalse(member_sent)
        self.member.refresh_from_db()
        self.assertFalse(self.member.mail_to_admin)
        self.assertFalse(self.member.mail_to_member)

    @patch("events.services.notification_service.send_registration_emails")
    def test_calls_strategy_build_formatting_dict(self, mock_send):
        mock_send.return_value = (True, True)
        strategy = MagicMock()
        strategy.build_formatting_dict.return_value = {"firstname": "Max"}

        form = MagicMock()
        self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        strategy.build_formatting_dict.assert_called_once_with(
            form, self.event, self.member
        )

    @patch("events.services.notification_service.send_registration_emails")
    def test_calls_send_registration_emails_with_correct_args(self, mock_send):
        mock_send.return_value = (True, True)
        strategy = MagicMock()
        formatting_dict = {"firstname": "Max"}
        strategy.build_formatting_dict.return_value = formatting_dict

        form = MagicMock()
        self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        mock_send.assert_called_once_with(
            self.event, form, formatting_dict, self.member.attend_status
        )

    @patch("events.services.notification_service.send_registration_emails")
    def test_member_save_called(self, mock_send):
        mock_send.return_value = (True, True)
        strategy = MagicMock()
        strategy.build_formatting_dict.return_value = {}

        form = MagicMock()
        self.service.send_notification_emails(
            self.event, form, self.member, strategy
        )

        # Verify member was saved (flags should persist)
        self.member.refresh_from_db()
        self.assertTrue(self.member.mail_to_admin)
