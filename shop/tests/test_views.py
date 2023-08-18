import datetime
from decimal import Decimal

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware

from events.models import (
    Event,
    EventDay,
    EventCategory,
    EventFormat,
    EventLocation,
    EventMember,
    EventCollection,
    PayLessAction,
)

from events.email_template import EmailTemplate
from shop.cart import Cart
from shop.views import cart_add, order_create, OrderCreateView

####################
# shop views
####################


class CartInitializeTestCase(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

        # adding session
        middleware = SessionMiddleware()
        middleware.process_request(self.request)
        self.request.session.save()

    def test_initialize_cart_clean_session(self):
        """
        The cart is initialized with a session that contains no cart.
        In the end it should have a variable cart which is an empty dict.
        """
        request = self.request
        cart = Cart(request)
        self.assertEqual(cart.cart, {})

    def test_initialize_cart_filled_session(self):
        """
        The cart is initialized with a session that contains a cart.
        In the end it should have a variable cart which is equal to the cart that
        is in the initial session.
        """
        existing_cart = {
            "1": {
                "price": "100.00",
                "premium_price": "120.00",
                "is_full": False,
                "action_price": False,
            },
            "2": {
                "price": "200.00",
                "premium_price": "250.00",
                "is_full": False,
                "action_price": False,
            },
        }

        request = self.request
        request.session["cart"] = existing_cart
        cart = Cart(request)
        self.assertEqual(cart.cart, existing_cart)


class CartAddTestCase(TestCase):
    # Test the add function
    # Possible outcomes:
    # Add non existing product
    # because quantity can only be 0 or 1

    def setUp(self):
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")
        # setup future standard events
        self.event1 = Event.objects.create(
            name=f"Future Event 1",
            category=category,
            eventformat=eventformat,
            location=location,
            price="100.00",
        )
        self.event2 = Event.objects.create(
            name=f"Future Event 2",
            category=category,
            eventformat=eventformat,
            location=location,
            price="200.00",
        )

        # Event and Payless Collection
        self.event_collection = EventCollection.objects.create(name="collection 1")
        self.payless_collection = PayLessAction.objects.create(
            name="payless collection 1"
        )
        # factory
        self.factory = RequestFactory()
        # request
        self.request = self.factory.get("/")

        # adding session
        middleware = SessionMiddleware()
        middleware.process_request(self.request)

        # add cart to session with one event
        event1_id = str(self.event1.id)
        self.request.session["cart"] = {
            event1_id: {
                "quantity": 1,
                "price": str(self.event1.price),
                "premium_price": str(self.event1.premium_price),
                "is_full": self.event1.is_full(),
                "action_price": False,
            },
        }
        self.request.session.save()

    def test_cart_add_new_event(self):
        cart = Cart(self.request)
        cart.add(
            event=self.event2,
            quantity=1,
            override_quantity=False,
        )
        event1_id = str(self.event1.id)
        event2_id = str(self.event2.id)
        new_cart = {
            event1_id: {
                "quantity": 1,
                "price": str(self.event1.price),
                "premium_price": str(self.event1.premium_price),
                "is_full": self.event1.is_full(),
                "action_price": False,
            },
            event2_id: {
                "quantity": 1,
                "price": str(self.event2.price),
                "premium_price": str(self.event2.premium_price),
                "is_full": self.event2.is_full(),
                "action_price": False,
            },
        }
        self.assertEqual(cart.cart, new_cart)

    # def test_cart_add_new_event_by_view(self):
    #     event1_id = str(self.event1.id)
    #     event2_id = str(self.event2.id)

    #     url = reverse("shop:cart-add", args=[self.event2.id])

    #     post_request = self.factory.post(url)

    #     middleware = SessionMiddleware()
    #     middleware.process_request(post_request)

    #     cart = Cart(post_request)

    #     response = cart_add(post_request, event_id=self.event2.id)

    #     post_cart = Cart(post_request)
    #     print(post_cart.cart)

    #     new_cart = {
    #         event2_id: {
    #             "quantity": 1,
    #             "price": str(self.event2.price),
    #             "premium_price": str(self.event2.premium_price),
    #             "is_full": self.event2.is_full(),
    #             "action_price": False,
    #         },
    #     }
    #     self.assertEqual(cart.cart, new_cart)

    def test_action_price_for_payless_action_of_type_p(self):
        cart = Cart(self.request)  # cart contains event1

        # setting type of payless action
        self.payless_collection.type = "p"
        self.payless_collection.percents = 20
        self.payless_collection.save()

        # adding event 2 to collection
        self.payless_collection.events.add(self.event2)
        self.event_collection.events.add(self.event2)

        # add event 2 to cart
        cart.add(
            event=self.event2,
            quantity=1,
            override_quantity=False,
        )

        # cart price is less than event price
        event2_id = str(self.event2.id)
        self.assertLess(float(cart.cart[event2_id]["price"]), float(self.event2.price))

    def test_action_price_for_cheaper_event_for_payless_action_of_type_n(self):
        # event 1 is cheaper, so in a n-Action its price on the cart shoud be zero
        cart = Cart(self.request)  # cart contains event1

        # setting type of payless action
        self.payless_collection.type = "n"
        self.payless_collection.save()

        # adding both evens to collection
        self.payless_collection.events.add(self.event1)
        self.event_collection.events.add(self.event1)
        self.payless_collection.events.add(self.event2)
        self.event_collection.events.add(self.event2)

        # add event 2 to cart
        cart.add(
            event=self.event2,
            quantity=1,
            override_quantity=False,
        )

        # cart price of event 1 zero
        event1_id = str(self.event1.id)
        self.assertEqual(float(cart.cart[event1_id]["price"]), 0.0)

    def test_action_price_for_more_expensive_event_for_payless_action_of_type_n(self):
        # event 2 is more expensive, so in a n-Action its cart price shoud be event price
        cart = Cart(self.request)  # cart contains event1

        # setting type of payless action
        self.payless_collection.type = "n"
        self.payless_collection.save()

        # adding both evens to collection
        self.payless_collection.events.add(self.event1)
        self.event_collection.events.add(self.event1)
        self.payless_collection.events.add(self.event2)
        self.event_collection.events.add(self.event2)

        # add event 2 to cart
        cart.add(
            event=self.event2,
            quantity=1,
            override_quantity=False,
        )

        # cart price of event 1 zero
        event2_id = str(self.event2.id)
        self.assertEqual(float(cart.cart[event2_id]["price"]), float(self.event2.price))

    def test_no_action_price_for_payless_action_of_type_n_if_not_all_events_in_cart(
        self,
    ):
        # event 1 is cheaper, so in a n-Action its price on the cart shoud be zero
        cart = Cart(self.request)  # cart contains event1

        # setting type of payless action
        self.payless_collection.type = "n"
        self.payless_collection.save()

        # adding both evens to collection
        self.payless_collection.events.add(self.event1)
        self.event_collection.events.add(self.event1)
        self.payless_collection.events.add(self.event2)
        self.event_collection.events.add(self.event2)

        # cart price should be event price because not all events
        # belonging to action are in cart
        event1_id = str(self.event1.id)
        self.assertEqual(float(cart.cart[event1_id]["price"]), float(self.event1.price))


class ShopViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # create event in the future
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")

        # create datetime object in the future
        future_datetime = timezone.now() + timezone.timedelta(days=7, hours=3)
        future_datetime_plus_one_hour = future_datetime + timezone.timedelta(
            days=0, hours=1
        )

        # Split the datetime into date and time components
        future_date = future_datetime.date()
        future_start_time = future_datetime.time()
        future_end_time = future_datetime_plus_one_hour.time()

        # setup future standard events
        cls.event1 = Event.objects.create(
            name=f"Future Event 1",
            category=category,
            eventformat=eventformat,
            location=location,
            price="100.00",
            registration_form="s",  # default
        )
        EventDay.objects.create(
            event=cls.event1,
            start_date=future_date,
            start_time=future_start_time,
            end_time=future_end_time,
        )

        cls.event2 = Event.objects.create(
            name=f"Future Event 2",
            category=category,
            eventformat=eventformat,
            location=location,
            price="100.00",
            registration_form="s",  # default
        )
        EventDay.objects.create(
            event=cls.event2,
            start_date=future_date,
            start_time=future_start_time,
            end_time=future_end_time,
        )

        # Event Collection
        cls.event_collection = EventCollection.objects.create(name="collection 1")
        cls.payless_collection = PayLessAction.objects.create(
            name="payless collection 1"
        )

        # request factory
        cls.request = RequestFactory().post(
            reverse("shop:cart-add", args=[cls.event1.id])
        )
        middleware = SessionMiddleware()
        middleware.process_request(cls.request)
        cls.request.session.save()
        cls.cart = Cart(cls.request)
        cls.request.session.save()

    def test_add_cart_view(self):
        self.event1.direct_payment = True
        self.event1.save()

        response = self.client.post(
            reverse("shop:cart-add", args=[self.event1.id]), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_cart_item_exists(self):
        self.event1.direct_payment = True
        self.event1.save()

        # Create an instance of a POST request.
        # response = self.client.post(
        #    reverse("shop:cart-add", args=[self.event1.id]), follow=True
        # )
        response = cart_add(self.request, self.event1.id)

        # cart
        session = self.request.session
        # session = self.client.session
        print(session["cart"])

        self.assertEqual(response.status_code, 302)
        # self.assertIsNotNone(respo)


###################
# Order Tests
###################


class OrderCreateViewTestCase(TestCase):
    def setUp(self):
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")
        # setup future standard events
        self.event1 = Event.objects.create(
            name=f"Future Event 1",
            category=category,
            eventformat=eventformat,
            location=location,
            price="100.00",
        )
        self.event2 = Event.objects.create(
            name=f"Future Event 2",
            category=category,
            eventformat=eventformat,
            location=location,
            price="200.00",
        )

        # Event and Payless Collection
        self.event_collection = EventCollection.objects.create(name="collection 1")
        self.payless_collection = PayLessAction.objects.create(
            name="payless collection 1"
        )
        # factory
        self.factory = RequestFactory()
        # request
        self.request = self.factory.get("shop/order_create")

        # adding session
        middleware = SessionMiddleware()
        middleware.process_request(self.request)

        # add cart to session with one event
        event1_id = str(self.event1.id)
        self.request.session["cart"] = {
            event1_id: {
                "quantity": 1,
                "price": str(self.event1.price),
                "premium_price": str(self.event1.premium_price),
                "is_full": self.event1.is_full(),
                "action_price": False,
            },
        }
        self.request.session.save()

    def test_order_create_view_exists(self):
        response = OrderCreateView.as_view()(self.request)
        # cart = Cart(self.request)
        self.assertEqual(
            response.status_code, 200
        )  # self.assertEqual(response.context_data["cart"], cart)

    def test_order_create_view_returns_cart_as_context(self):
        response = OrderCreateView.as_view()(self.request)
        cart = Cart(self.request)
        self.assertEqual(response.context_data["cart"].cart, cart.cart)
