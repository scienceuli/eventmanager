import datetime
from decimal import Decimal

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.conf import settings

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
from shop.models import Order, OrderItem
from shop.views import cart_add, order_create, OrderCreateView


####################
# email sending
####################


class EmailTestCase(TestCase):
    def setUp(self):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    def test_send_email(self):
        mail.send_mail(
            "That’s your subject",
            "That’s your message body",
            "from@yourdjangoapp.com",
            ["ukilian@mac.com"],
            fail_silently=False,
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "That’s your subject")
        self.assertEqual(mail.outbox[0].body, "That’s your message body")


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

    def test_order_create_view_with_vfll_registration(self):
        cart = Cart(self.request)
        form_data = {
            "lastname": "Lachmal",
            "firstname": "Lilly",
            "email": "lilly@lachmal.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
            "vfll": True,
        }
        response = OrderCreateView.as_view()(self.request, data=form_data)
        last_order = Order.objects.all().last()
        self.assertEqual(last_order.event, self.event1)


class OrderCreateViewPostTestCase(TestCase):
    def setUp(self):
        # existing order
        existing_order = Order(
            lastname="Huber",
            firstname="Hans",
            email="hans@huber.de",
            street="Huberstrasse",
            postcode="11111",
            city="Hubercity",
            country="DE",
        )
        existing_order.save()

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

        # Template
        template_anmeldung = EmailTemplate.objects.create(
            name="anmeldung", text_template="anmeldung"
        )
        template_bestaetigung = EmailTemplate.objects.create(
            name="bestaetigung", text_template="bestaetigung"
        )
        template_waiting = EmailTemplate.objects.create(
            name="warteliste", text_template="warteliste"
        )

        # Event and Payless Collection
        self.event_collection = EventCollection.objects.create(name="collection 1")
        self.payless_collection = PayLessAction.objects.create(
            name="payless collection 1"
        )
        # factory
        self.factory = RequestFactory()

        # form_data
        form_data = {
            "lastname": "Lachmal",
            "firstname": "Lilly",
            "email": "lilly@lachmal.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
            "vfll": True,
        }
        # request
        self.request = self.factory.post("shop/order_create", data=form_data)

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

    def test_order_create_view_that_order_was_created(self):
        cart = Cart(self.request)

        response = OrderCreateView.as_view()(self.request)
        # order are ordered by -date_created, so newest order is first one
        newest_order = Order.objects.all().first()
        self.assertEqual(newest_order.lastname, "Lachmal")

    def test_order_create_view_that_order_was_not_created_when_email_already_registerd(
        self,
    ):
        # create event member with some email as in form_data

        self.event_member = EventMember.objects.create(
            event=self.event1,
            lastname=f"Nachname",
            firstname=f"Vorname",
            email=f"lilly@lachmal.de",
            street=f"Straße",
            city=f"Stadt",
            postcode="12345",
            country="DE",
            attend_status="registered",
        )

        cart = Cart(self.request)

        response = OrderCreateView.as_view()(self.request)
        # order are ordered by -date_created, so newest order is first one
        nr_of_orders = Order.objects.all().count()
        # lastname of newest order is Huber
        lastname = Order.objects.all().first().lastname
        self.assertEqual(nr_of_orders, 1)
        self.assertEqual(lastname, "Huber")

    def test_order_create_view_all_events_from_cart_are_created_as_items(self):
        # create event_member with email different from form_data email
        event_member = EventMember.objects.create(
            event=self.event1,
            lastname=f"Nachname",
            firstname=f"Vorname",
            email=f"not_used@emails.de",
            street=f"Straße",
            city=f"Stadt",
            postcode="12345",
            country="DE",
            attend_status="registered",
        )

        # add second event to cart
        event2_id = str(self.event2.id)
        new_event_for_cart = {
            event2_id: {
                "quantity": 1,
                "price": str(self.event2.price),
                "premium_price": str(self.event1.premium_price),
                "is_full": self.event1.is_full(),
                "action_price": False,
            },
        }
        self.request.session["cart"].update(new_event_for_cart)
        self.request.session.save()

        response = OrderCreateView.as_view()(self.request)

        # newest order
        newest_order = Order.objects.all().first()

        # number of order items
        nr_items = newest_order.items.all().count()
        self.assertEqual(nr_items, 2)

    def test_order_create_view_only_one_event_from_cart_is_created_as_item(self):
        # create event_member with email equal to form_data email
        event_member = EventMember.objects.create(
            event=self.event1,
            lastname=f"Nachname",
            firstname=f"Vorname",
            email=f"lilly@lachmal.de",
            street=f"Straße",
            city=f"Stadt",
            postcode="12345",
            country="DE",
            attend_status="registered",
        )

        # add second event to cart
        event2_id = str(self.event2.id)
        new_event_for_cart = {
            event2_id: {
                "quantity": 1,
                "price": str(self.event2.price),
                "premium_price": str(self.event1.premium_price),
                "is_full": self.event1.is_full(),
                "action_price": False,
            },
        }
        self.request.session["cart"].update(new_event_for_cart)
        self.request.session.save()

        response = OrderCreateView.as_view()(self.request)

        # newest order
        newest_order = Order.objects.all().first()

        # item
        order_item = OrderItem.objects.get(order=newest_order)

        # number of order items is 1 not 2
        nr_items = newest_order.items.all().count()
        self.assertEqual(nr_items, 1)
        # the event of the order item is event 2
        self.assertEqual(order_item.event, self.event2)

    def test_send_email_after_order_creation(self):
        EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        response = OrderCreateView.as_view()(self.request)
        # order are ordered by -date_created, so newest order is first one
        newest_order = Order.objects.all().first()

        # two mails must be created: 1 for registration, 1 to vfll

        self.assertEqual(len(mail.outbox), 2)


class OrderCreateViewPricesTestCase(TestCase):
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

        # Template
        template_anmeldung = EmailTemplate.objects.create(
            name="anmeldung", text_template="anmeldung"
        )
        template_bestaetigung = EmailTemplate.objects.create(
            name="bestaetigung", text_template="bestaetigung"
        )
        template_waiting = EmailTemplate.objects.create(
            name="warteliste", text_template="warteliste"
        )

        # Event and Payless Collection
        self.event_collection = EventCollection.objects.create(name="collection 1")
        self.payless_collection = PayLessAction.objects.create(
            name="payless collection 1"
        )
        # factory
        self.factory = RequestFactory()

    def test_price_is_reduced_if_vfll_member(self):
        # form_data
        form_data = {
            "lastname": "Lachmal",
            "firstname": "Lilly",
            "email": "lilly@lachmal.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
            "vfll": True,
        }
        # request
        self.request = self.factory.post("shop/order_create", data=form_data)

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

        response = OrderCreateView.as_view()(self.request)

        # newest order
        newest_order = Order.objects.all().first()

        # item (only one)
        order_item = OrderItem.objects.get(order=newest_order)

        # the get_cost method returns the price
        price = order_item.get_cost()

        # item event is event1
        self.assertEqual(price, Decimal(self.event1.price))

    def test_price_is_reduced_if_other_member(self):
        # form_data
        form_data = {
            "lastname": "Lachmal",
            "firstname": "Lilly",
            "email": "lilly@lachmal.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
            "memberships": ["vdu", "bf"],
            # "vfll": True,
        }
        # request
        self.request = self.factory.post("shop/order_create", data=form_data)

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

        response = OrderCreateView.as_view()(self.request)
        # newest order
        newest_order = Order.objects.all().first()

        # item (only one)
        order_item = OrderItem.objects.get(order=newest_order)

        # the get_cost method returns the price
        price = order_item.get_cost()

        # item event is event1
        self.assertEqual(price, Decimal(self.event1.price))

    def test_price_is_not_reduced_if_no_member(self):
        # form_data
        form_data = {
            "lastname": "Lachmal",
            "firstname": "Lilly",
            "email": "lilly@lachmal.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
        }
        # request
        self.request = self.factory.post("shop/order_create", data=form_data)

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

        response = OrderCreateView.as_view()(self.request)
        # newest order
        newest_order = Order.objects.all().first()

        # item (only one)
        order_item = OrderItem.objects.get(order=newest_order)

        # the get_cost method returns the price
        price = order_item.get_cost()

        # item event is event1
        self.assertEqual(price, Decimal(self.event1.premium_price))
