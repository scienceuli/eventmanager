from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from events.models import Event, EventCategory, EventFormat, EventLocation, EventMember
from shop.models import Order, OrderItem
from shop.services.order_service import OrderService
from invoices.models import Invoice


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


def make_cart_item(event, price=100, premium_price=135):
    return {
        "event": event,
        "quantity": 1,
        "price": Decimal(str(price)),
        "premium_price": Decimal(str(premium_price)),
        "action_price": False,
    }


class OrderServiceTestBase(TestCase):
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

        cls.event2 = Event.objects.create(
            name="Test Event 2",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            label="test-event-2",
            price="50.00",
            first_day=date.today() + timedelta(days=60),
        )


class CreateOrderTest(OrderServiceTestBase):

    def test_creates_order_with_form_data(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        order = service.create_order()

        self.assertIsNotNone(order.pk)
        self.assertEqual(order.firstname, "Max")
        self.assertEqual(order.lastname, "Mustermann")
        self.assertEqual(order.email, "max@example.com")
        self.assertEqual(order.academic, "Dr.")
        self.assertEqual(order.company, "Test GmbH")
        self.assertEqual(order.street, "Teststr. 1")
        self.assertEqual(order.city, "Berlin")
        self.assertEqual(order.postcode, "10115")
        self.assertEqual(order.phone, "030123456")

    def test_discounted_when_vfll_member(self):
        data = make_form_data(vfll=True)
        form = make_mock_form(data)
        service = OrderService(form, "max@example.com")
        order = service.create_order()

        self.assertTrue(order.discounted)

    def test_discounted_when_has_memberships(self):
        data = make_form_data(memberships=["BDU"])
        form = make_mock_form(data)
        service = OrderService(form, "max@example.com")
        order = service.create_order()

        self.assertTrue(order.discounted)

    def test_not_discounted_when_no_membership(self):
        data = make_form_data(vfll=False, memberships=[])
        form = make_mock_form(data)
        service = OrderService(form, "max@example.com")
        order = service.create_order()

        self.assertFalse(order.discounted)


class EnsureOrderTest(OrderServiceTestBase):

    def test_creates_order_on_first_call(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        order = service.ensure_order()

        self.assertIsNotNone(order.pk)

    def test_returns_same_order_on_subsequent_calls(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        order1 = service.ensure_order()
        order2 = service.ensure_order()

        self.assertEqual(order1.pk, order2.pk)

    def test_only_creates_one_order(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        initial_count = Order.objects.count()

        service.ensure_order()
        service.ensure_order()
        service.ensure_order()

        self.assertEqual(Order.objects.count(), initial_count + 1)


class AddItemTest(OrderServiceTestBase):

    def test_creates_order_item(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        item = make_cart_item(self.event)

        order_item = service.add_item(item)

        self.assertIsNotNone(order_item.pk)
        self.assertEqual(order_item.event, self.event)
        self.assertEqual(order_item.price, Decimal("100"))
        self.assertEqual(order_item.premium_price, Decimal("135"))
        self.assertEqual(order_item.quantity, 1)
        self.assertFalse(order_item.is_action_price)

    def test_add_item_creates_order_if_needed(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        item = make_cart_item(self.event)

        self.assertIsNone(service.order)
        service.add_item(item)
        self.assertIsNotNone(service.order)

    def test_add_multiple_items_to_same_order(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")

        service.add_item(make_cart_item(self.event))
        service.add_item(make_cart_item(self.event2, price=50, premium_price=70))

        self.assertEqual(service.order.items.count(), 2)


class FinalizeTest(OrderServiceTestBase):

    @override_settings(ORDER_DATE_DELAYED=False)
    @patch("invoices.models.Invoice.create_invoice_message")
    def test_finalize_with_items_creates_invoice(self, mock_msg):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")

        # Register a member so get_registered_items_events works
        EventMember.objects.create(
            event=self.event,
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            attend_status="registered",
        )

        service.add_item(make_cart_item(self.event))
        order = service.finalize()

        self.assertIsNotNone(order)
        invoice = Invoice.objects.filter(order=order).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.invoice_type, "i")
        self.assertEqual(invoice.invoice_number, order.get_order_number)

    def test_finalize_without_items_deletes_order(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")

        service.ensure_order()
        order_pk = service.order.pk
        service.finalize()

        self.assertFalse(Order.objects.filter(pk=order_pk).exists())

    def test_finalize_without_order_returns_none(self):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")
        result = service.finalize()

        self.assertIsNone(result)

    @override_settings(ORDER_DATE_DELAYED=False)
    @patch("invoices.models.Invoice.create_invoice_message")
    def test_invoice_name_contains_order_info(self, mock_msg):
        form = make_mock_form()
        service = OrderService(form, "max@example.com")

        EventMember.objects.create(
            event=self.event,
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            attend_status="registered",
        )

        service.add_item(make_cart_item(self.event))
        order = service.finalize()

        invoice = Invoice.objects.filter(order=order).first()
        self.assertIn("Mustermann", invoice.name)
        self.assertIn("Max", invoice.name)

    @override_settings(ORDER_DATE_DELAYED=False)
    @patch("invoices.models.Invoice.create_invoice_message")
    def test_invoice_amount_matches_order_total(self, mock_msg):
        data = make_form_data(vfll=True)  # discounted
        form = make_mock_form(data)
        service = OrderService(form, "max@example.com")

        EventMember.objects.create(
            event=self.event,
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            attend_status="registered",
        )

        service.add_item(make_cart_item(self.event))
        order = service.finalize()

        invoice = Invoice.objects.filter(order=order).first()
        self.assertEqual(invoice.amount, order.get_total_cost())
