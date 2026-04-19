from datetime import datetime, timedelta, date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from events.models import Event, EventCategory, EventFormat, EventLocation
from shop.models import Order, OrderItem
from payment.services.payment_service import PaymentService


class PaymentServiceTestBase(TestCase):
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
            first_day=date.today() + timedelta(days=30),
        )

        cls.order = Order.objects.create(
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            payment_type="r",
            payment_date=timezone.now(),
        )

        cls.order_item = OrderItem.objects.create(
            order=cls.order,
            event=cls.event,
            price=Decimal("100.00"),
            premium_price=Decimal("135.00"),
            cost=Decimal("100.00"),
        )

        cls.service = PaymentService()


class GetPaymentDateTest(PaymentServiceTestBase):

    @override_settings(ORDER_DATE_DELAYED=False)
    def test_not_delayed_returns_date_created(self):
        result = self.service.get_payment_date(self.order)
        self.assertEqual(result, self.order.date_created)

    @override_settings(ORDER_DATE_DELAYED=True)
    def test_paypal_returns_date_created(self):
        self.order.payment_type = "p"
        self.order.save()
        result = self.service.get_payment_date(self.order)
        self.assertEqual(result, self.order.date_created)
        # reset
        self.order.payment_type = "r"
        self.order.save()

    @override_settings(ORDER_DATE_DELAYED=True, SEND_INVOICE_AFTER_ORDER_CREATION=True)
    def test_invoice_with_send_after_creation_returns_date_created(self):
        result = self.service.get_payment_date(self.order)
        self.assertEqual(result, self.order.date_created)

    @override_settings(
        ORDER_DATE_DELAYED=True,
        SEND_INVOICE_AFTER_ORDER_CREATION=False,
        ORDER_DATE_TIMEDELTA=5,
    )
    def test_invoice_delayed_returns_calculated_date(self):
        # Event is 30 days in the future, so calculated_date = first_day - 5 days
        result = self.service.get_payment_date(self.order)
        expected = self.event.first_day - timedelta(days=5)
        self.assertEqual(result, expected)


class HandlePaymentSuccessTest(PaymentServiceTestBase):

    def test_sets_payment_type_to_paypal(self):
        self.service.handle_payment_success(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_type, "p")
        # reset
        self.order.payment_type = "r"
        self.order.save()


class HandlePaymentFailureTest(PaymentServiceTestBase):

    @override_settings(ORDER_DATE_DELAYED=False)
    def test_sets_payment_type_to_invoice(self):
        self.order.payment_type = "p"
        self.order.save()
        self.service.handle_payment_failure(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_type, "r")

    @override_settings(ORDER_DATE_DELAYED=False)
    def test_sets_payment_date(self):
        self.service.handle_payment_failure(self.order)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.payment_date)


class HandleInvoicePaymentTest(PaymentServiceTestBase):

    @override_settings(
        ORDER_DATE_DELAYED=False, SEND_INVOICE_AFTER_ORDER_CREATION=False
    )
    def test_sets_payment_type_and_date(self):
        self.order.payment_type = "p"
        self.order.payment_date = None
        self.order.save()
        self.service.handle_invoice_payment(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_type, "r")
        self.assertIsNotNone(self.order.payment_date)

    @override_settings(
        ORDER_DATE_DELAYED=False, SEND_INVOICE_AFTER_ORDER_CREATION=True
    )
    @patch("payment.tasks.payment_completed")
    def test_triggers_payment_completed_when_configured(self, mock_completed):
        self.service.handle_invoice_payment(self.order)
        mock_completed.assert_called_once_with(self.order.id)


class SendReminderTest(PaymentServiceTestBase):

    def test_paid_order_returns_error(self):
        self.order.paid = True
        self.order.save()
        success, error = self.service.send_reminder(self.order)
        self.assertFalse(success)
        self.assertEqual(error, "Rechnung wurde bereits bezahlt")
        # reset
        self.order.paid = False
        self.order.save()

    def test_incomplete_order_returns_error(self):
        self.order.email = ""
        self.order.save()
        success, error = self.service.send_reminder(self.order)
        self.assertFalse(success)
        self.assertIn("vervollständigen", error)
        # reset
        self.order.email = "max@example.com"
        self.order.save()

    @patch("payment.services.payment_service.send_email", return_value=True)
    def test_successful_reminder_updates_sent_date(self, mock_send):
        self.order.reminder_sent_date = None
        self.order.save()
        success, error = self.service.send_reminder(self.order)
        self.assertTrue(success)
        self.assertIsNone(error)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.reminder_sent_date)
        mock_send.assert_called_once()

    @patch("payment.services.payment_service.send_email", return_value=False)
    def test_failed_send_returns_error(self, mock_send):
        success, error = self.service.send_reminder(self.order)
        self.assertFalse(success)
        self.assertIn("konnte nicht verschickt", error)
