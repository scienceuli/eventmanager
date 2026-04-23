from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from events.models import Event, EventCategory, EventFormat, EventLocation
from events.services.registration import RegistrationResult
from shop.services.checkout_service import CheckoutService, CheckoutResult


def make_form_data(**overrides):
    data = {
        "academic": "Dr.",
        "firstname": "Max",
        "lastname": "Mustermann",
        "address_line": "",
        "company": "Test GmbH",
        "street": "Teststr. 1",
        "city": "Berlin",
        "state": "",
        "postcode": "10115",
        "phone": "030123456",
        "email": "max@example.com",
        "vfll": False,
        "memberships": [],
    }
    data.update(overrides)
    return data


def make_mock_form(data=None):
    form = MagicMock()
    form.cleaned_data = data or make_form_data()
    return form


def make_cart_item(event, is_full=False):
    item = {
        "event": event,
        "quantity": 1,
        "price": Decimal("100.00"),
        "premium_price": Decimal("135.00"),
        "action_price": False,
    }
    return item


class CheckoutServiceTestBase(TestCase):
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

        cls.event_full = Event.objects.create(
            name="Full Event",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            label="full-event",
            price="80.00",
            first_day=date.today() + timedelta(days=30),
            capacity=0,
        )


class CheckoutResultTest(TestCase):

    def test_default_values(self):
        result = CheckoutResult()
        self.assertFalse(result.success)
        self.assertFalse(result.has_error)
        self.assertEqual(result.successes, [])
        self.assertEqual(result.errors, [])

    def test_independent_instances(self):
        r1 = CheckoutResult()
        r2 = CheckoutResult()
        r1.successes.append("msg")
        self.assertEqual(r2.successes, [])


@override_settings(ONE_ORDER_ONE_INVOICE=False)
class CheckoutExecuteSuccessTest(CheckoutServiceTestBase):

    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_single_paid_item_success(self, mock_strategy, mock_split):
        """Successful checkout with one paid item creates order and sends emails."""
        member = MagicMock()
        reg_result = RegistrationResult(
            success=True, successes=["Anmeldung erfolgreich"]
        )

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        mock_notification_service = MagicMock()
        mock_order_service = MagicMock()

        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])
        reg_result.member = member

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = mock_notification_service
        service.order_service = mock_order_service

        result = service.execute()

        self.assertTrue(result.success)
        self.assertFalse(result.has_error)
        self.assertIn("Anmeldung erfolgreich", result.successes)
        mock_notification_service.send_notification_emails.assert_called_once()
        mock_order_service.add_item.assert_called_once_with(item)
        mock_order_service.finalize.assert_called_once()
        service.cart.clear.assert_called_once()

    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_free_item_not_added_to_order(self, mock_strategy, mock_split):
        """Free items (full events) are registered but not added to order."""
        member = MagicMock()
        reg_result = RegistrationResult(
            success=True, successes=["Warteliste"]
        )
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        free_item = make_cart_item(self.event_full)
        mock_split.return_value = ([], [free_item])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        service.order_service.add_item.assert_not_called()
        service.order_service.finalize.assert_called_once()

    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_mixed_paid_and_free_items(self, mock_strategy, mock_split):
        """Both paid and free items are processed; only paid added to order."""
        member = MagicMock()
        reg_result = RegistrationResult(
            success=True, successes=["OK"]
        )
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        paid_item = make_cart_item(self.event)
        free_item = make_cart_item(self.event_full)
        mock_split.return_value = ([paid_item], [free_item])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        self.assertEqual(len(result.successes), 2)
        service.order_service.add_item.assert_called_once_with(paid_item)


@override_settings(ONE_ORDER_ONE_INVOICE=False)
class CheckoutExecuteErrorTest(CheckoutServiceTestBase):

    @patch("shop.services.checkout_service.split_cart")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_registration_error_sets_has_error(self, mock_split):
        """Registration errors are collected in result."""
        reg_result = RegistrationResult(
            success=False, errors=["Duplicate email"]
        )

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.has_error)
        self.assertIn("Duplicate email", result.errors)
        service.order_service.add_item.assert_not_called()

    @patch("shop.services.checkout_service.split_cart")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_exception_returns_generic_error(self, mock_split):
        """Unhandled exception inside try block results in generic error message."""
        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])

        mock_reg_service = MagicMock()
        mock_reg_service.register.side_effect = Exception("DB error")

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.has_error)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Fehler", result.errors[0])

    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_partial_success_and_error(self, mock_strategy, mock_split):
        """Mix of successful and failed registrations."""
        member = MagicMock()
        success_result = RegistrationResult(
            success=True, successes=["OK"]
        )
        success_result.member = member
        error_result = RegistrationResult(
            success=False, errors=["Blacklisted"]
        )

        mock_reg_service = MagicMock()
        mock_reg_service.register.side_effect = [success_result, error_result]

        item1 = make_cart_item(self.event)
        item2 = make_cart_item(self.event_full)
        mock_split.return_value = ([item1], [item2])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        self.assertTrue(result.has_error)
        self.assertIn("OK", result.successes)
        self.assertIn("Blacklisted", result.errors)


@override_settings(ONE_ORDER_ONE_INVOICE=False)
class CheckoutExecuteCartClearTest(CheckoutServiceTestBase):

    @patch("shop.services.checkout_service.split_cart")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_cart_cleared_on_success(self, mock_split):
        """Cart is cleared after successful checkout."""
        member = MagicMock()
        reg_result = RegistrationResult(success=True, successes=["OK"])
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        mock_split.return_value = ([], [])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        service.execute()

        service.cart.clear.assert_called_once()

    @patch("shop.services.checkout_service.split_cart")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_cart_not_cleared_on_exception(self, mock_split):
        """Cart is NOT cleared when an exception occurs."""
        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])

        mock_reg_service = MagicMock()
        mock_reg_service.register.side_effect = Exception("fail")

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        service.execute()

        service.cart.clear.assert_not_called()


@override_settings(ONE_ORDER_ONE_INVOICE=False)
class CheckoutNotificationTest(CheckoutServiceTestBase):

    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_notification_called_with_correct_args(self, mock_strategy, mock_split):
        """Notification service receives event, form, member, strategy."""
        member = MagicMock()
        reg_result = RegistrationResult(success=True, successes=["OK"])
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        strategy_instance = MagicMock()
        mock_strategy.return_value = strategy_instance

        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])

        form = make_mock_form()
        service = CheckoutService.__new__(CheckoutService)
        service.form = form
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        service.execute()

        service.notification_service.send_notification_emails.assert_called_once_with(
            self.event, form, member, strategy_instance
        )

    @patch("shop.services.checkout_service.split_cart")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_no_notification_on_failed_registration(self, mock_split):
        """No notification emails sent when registration fails."""
        reg_result = RegistrationResult(success=False, errors=["Error"])

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        item = make_cart_item(self.event)
        mock_split.return_value = ([item], [])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        service.execute()

        service.notification_service.send_notification_emails.assert_not_called()


class CheckoutOneOrderOneInvoiceTest(CheckoutServiceTestBase):

    @override_settings(ONE_ORDER_ONE_INVOICE=True)
    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch("shop.services.checkout_service.OrderService")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_two_paid_items_create_two_orders(self, MockOrderService, mock_strategy, mock_split):
        """With ONE_ORDER_ONE_INVOICE=True, each paid item gets its own OrderService."""
        member = MagicMock()
        reg_result = RegistrationResult(success=True, successes=["OK"])
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        event2 = Event.objects.create(
            name="Event Two",
            category=self.category,
            eventformat=self.eventformat,
            location=self.location,
            label="event-two",
            price="50.00",
            first_day=self.event.first_day,
        )

        item1 = make_cart_item(self.event)
        item2 = make_cart_item(event2)
        mock_split.return_value = ([item1, item2], [])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        # OrderService should be instantiated twice (once per paid item)
        self.assertEqual(MockOrderService.call_count, 2)
        # Each instance should have add_item and finalize called once
        for call_instance in MockOrderService.return_value.method_calls:
            pass  # checked below
        instances = [MockOrderService.return_value]
        # Since mock returns same instance, check total calls
        self.assertEqual(MockOrderService.return_value.add_item.call_count, 2)
        self.assertEqual(MockOrderService.return_value.finalize.call_count, 2)
        # The shared order_service should NOT have been used
        service.order_service.add_item.assert_not_called()
        service.order_service.finalize.assert_not_called()

    @override_settings(ONE_ORDER_ONE_INVOICE=False)
    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_two_paid_items_default_creates_one_order(self, mock_strategy, mock_split):
        """With ONE_ORDER_ONE_INVOICE=False, all paid items go into one order."""
        member = MagicMock()
        reg_result = RegistrationResult(success=True, successes=["OK"])
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        item1 = make_cart_item(self.event)
        item2 = make_cart_item(self.event_full)
        mock_split.return_value = ([item1, item2], [])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        self.assertEqual(service.order_service.add_item.call_count, 2)
        service.order_service.finalize.assert_called_once()

    @override_settings(ONE_ORDER_ONE_INVOICE=True)
    @patch("shop.services.checkout_service.split_cart")
    @patch("shop.services.checkout_service.get_strategy")
    @patch.object(CheckoutService, "__init__", lambda self, form, cart: None)
    def test_free_items_no_order_with_setting(self, mock_strategy, mock_split):
        """Free items still don't create orders even with ONE_ORDER_ONE_INVOICE=True."""
        member = MagicMock()
        reg_result = RegistrationResult(success=True, successes=["Warteliste"])
        reg_result.member = member

        mock_reg_service = MagicMock()
        mock_reg_service.register.return_value = reg_result

        free_item = make_cart_item(self.event_full)
        mock_split.return_value = ([], [free_item])

        service = CheckoutService.__new__(CheckoutService)
        service.form = make_mock_form()
        service.cart = MagicMock()
        service.email = "max@example.com"
        service.registration_service = mock_reg_service
        service.notification_service = MagicMock()
        service.order_service = MagicMock()

        result = service.execute()

        self.assertTrue(result.success)
        service.order_service.add_item.assert_not_called()
