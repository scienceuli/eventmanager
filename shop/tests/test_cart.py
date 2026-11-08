import json
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase

from events.models import Event, EventCategory, EventFormat, EventLocation
from shop.cart import Cart, split_cart


class CartSessionSerializationTest(TestCase):
    """Iterating the cart must not put non-JSON values into the session."""

    @classmethod
    def setUpTestData(cls):
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")
        cls.event = Event.objects.create(
            name="Test Event",
            category=category,
            eventformat=eventformat,
            location=location,
            label="test-event",
            price="100.00",
            first_day=date.today() + timedelta(days=30),
        )

    def setUp(self):
        self.request = RequestFactory().get("/shop/")
        self.request.session = SessionStore()

    def test_session_serializable_after_iteration(self):
        cart = Cart(self.request)
        cart.add(event=self.event, quantity=1, override_quantity=True)

        items = list(cart)
        split_cart(cart)

        # iterated items carry Decimal + Event for templates ...
        self.assertIsInstance(items[0]["price"], Decimal)
        self.assertEqual(items[0]["event"], self.event)
        # ... but the session data stays JSON-serializable
        stored = self.request.session[settings.CART_SESSION_ID]
        json.dumps(stored)
        self.assertNotIn("event", stored[str(self.event.id)])
        self.assertIsInstance(stored[str(self.event.id)]["price"], str)

        # the real failure: saving a modified session after iteration
        self.request.session.modified = True
        self.request.session.save()

    def test_deleted_event_is_skipped(self):
        cart = Cart(self.request)
        cart.add(event=self.event, quantity=1, override_quantity=True)
        self.request.session[settings.CART_SESSION_ID]["999999"] = {
            "quantity": 1,
            "price": "10.00",
            "premium_price": "10.00",
            "is_full": False,
            "action_price": False,
        }

        items = list(cart)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["event"], self.event)
