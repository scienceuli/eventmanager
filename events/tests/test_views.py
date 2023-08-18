import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


# Function to calculate  elements of a nested dict where the non dict value is list
# return the combined length of these lists
def count_dict_elements(mydict, c=0):
    for mykey in mydict:
        if isinstance(mydict[mykey], dict):
            # calls repeatedly
            c = count_dict_elements(mydict[mykey], c)
        else:
            c += len(mydict[mykey])
    return c


class EventListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create 5 events
        number_of_events = 5

        cls.category = EventCategory.objects.create(name="testcat")
        cls.eventformat = EventFormat.objects.create(name="testformat")
        cls.location = EventLocation.objects.create(title="testloc")

        # Create a past date and time and future date and time
        past_datetime = timezone.now() - timezone.timedelta(days=7, hours=3)
        past_datetime_plus_one_hour = past_datetime + timezone.timedelta(
            days=0, hours=1
        )
        future_datetime = timezone.now() + timezone.timedelta(days=7, hours=3)
        future_datetime_plus_one_hour = future_datetime + timezone.timedelta(
            days=0, hours=1
        )
        # Split the datetime into date and time components
        past_date = past_datetime.date()
        past_start_time = past_datetime.time()
        past_end_time = past_datetime_plus_one_hour.time()

        future_date = future_datetime.date()
        future_start_time = future_datetime.time()
        future_end_time = future_datetime_plus_one_hour.time()

        # setup future events
        for event_id in range(number_of_events):
            event = Event.objects.create(
                name=f"Test Event {event_id}",
                category=cls.category,
                eventformat=cls.eventformat,
                location=cls.location,
                price="100.00",
            )
            EventDay.objects.create(
                event=event,
                start_date=future_date,
                start_time=future_start_time,
                end_time=future_end_time,
            )

        # Event in the past:
        event_in_the_past = Event.objects.create(
            name="Past Event",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            price="100.00",
        )

        # create event_day in the past for event in the past
        event_day_in_past = EventDay.objects.create(
            event=event_in_the_past,
            start_date=past_date,
            start_time=past_start_time,
            end_time=past_end_time,
        )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get("/event_list/")
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse("event-list"))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse("event-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_list_filter.html")

    def test_do_not_list_events_in_the_past(self):
        # confirm that only total number minus one events are listed
        number_of_events_in_the_future = Event.objects.all().count() - 1
        response = self.client.get(reverse("event-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            count_dict_elements(response.context["events_dict"]),
            number_of_events_in_the_future,
        )


#################
# Testing context
#################


class EventContextTest(TestCase):
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

    def test_registration_button_for_non_payment_direct_event(self):
        self.event1.registration_possible = True
        self.event1.save()

        response = self.client.get(reverse("event-detail", args=[self.event1.slug]))
        self.assertEqual(response.context[-1]["registration_button"], "Online anmelden")

    def test_dont_show_registration_button_when_registration_not_possible(self):
        self.event1.registration_possible = False
        self.event1.save()

        response = self.client.get(reverse("event-detail", args=[self.event1.slug]))
        self.assertEqual(response.context[-1]["show_button"], False)

    def test_dont_show_registration_text_when_registration_not_possible(self):
        self.event1.registration_possible = False
        self.event1.save()

        response = self.client.get(reverse("event-detail", args=[self.event1.slug]))
        self.assertEqual(response.context[-1]["show_registration"], False)

    def test_show_action_button_if_event_belongs_to_payless_collection(self):
        self.event1.event_collection = self.event_collection
        self.event2.event_collection = self.event_collection

        self.event1.payless_collection = self.payless_collection
        self.event2.payless_collection = self.payless_collection

        self.event1.save()
        self.event2.save()

        response = self.client.get(reverse("event-detail", args=[self.event1.slug]))
        self.assertEqual(response.context[-1]["show_action_button"], True)

    def test_dont_show_action_button_if_one_event_is_full(self):
        # create member of event 2 with attend_status='registered'
        form_data = {
            "firstname": "Hans",
            "lastname": "Huber",
            "email": "hans@huber.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
        }
        EventMember.objects.create(
            event=self.event2, attend_status="registered", **form_data
        )
        # change capacity of event2 to 1 which makes event2 fully booked
        self.event2.capacity = 1
        self.event2.save()

        # collections
        self.event1.event_collection = self.event_collection
        self.event2.event_collection = self.event_collection

        self.event1.payless_collection = self.payless_collection
        self.event2.payless_collection = self.payless_collection

        self.event1.save()
        self.event2.save()

        response = self.client.get(reverse("event-detail", args=[self.event1.slug]))
        self.assertEqual(response.context[-1]["show_action_button"], False)


################################
# Testing Creating Event Members
################################


class AddEventMemberTest(TestCase):
    def setUp(self):
        # create event in the future
        category = EventCategory.objects.create(name="testcat")
        eventformat = EventFormat.objects.create(name="testformat")
        location = EventLocation.objects.create(title="testloc")
        template_anmeldung = EmailTemplate.objects.create(
            name="anmeldung", text_template="anmeldung"
        )
        template_bestaetigung = EmailTemplate.objects.create(
            name="bestaetigung", text_template="bestaetigung"
        )
        template_waiting = EmailTemplate.objects.create(
            name="warteliste", text_template="warteliste"
        )

        # create day in the future
        future_datetime = timezone.now() + timezone.timedelta(days=7, hours=3)
        future_datetime_plus_one_hour = future_datetime + timezone.timedelta(
            days=0, hours=1
        )

        # Split the datetime into date and time components
        future_date = future_datetime.date()
        future_start_time = future_datetime.time()
        future_end_time = future_datetime_plus_one_hour.time()

        # setup future standard event
        self.event = Event.objects.create(
            name=f"Future Event",
            category=category,
            eventformat=eventformat,
            location=location,
            price="100.00",
            registration_form="s",  # default
        )
        EventDay.objects.create(
            event=self.event,
            start_date=future_date,
            start_time=future_start_time,
            end_time=future_end_time,
        )

        # create two members
        number_of_members = 2
        for member_id in range(number_of_members):
            EventMember.objects.create(
                event=self.event,
                lastname=f"Nachname {member_id}",
                firstname=f"Vorname {member_id}",
                email=f"nachname{member_id}@users.de",
                street=f"Straße {member_id}",
                city=f"Stadt {member_id}",
                postcode="12345",
                country="DE",
                attend_status="registered",
            )

    def test_add_member_with_standard_form(self):
        form_data = {
            "firstname": "Hans",
            "lastname": "Huber",
            "email": "hans@huber.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
        }
        # Post form data to the view
        # the follow=True is important
        response = self.client.post(
            reverse("event-add-member", args=[self.event.slug]), form_data, follow=True
        )
        self.assertEqual(
            response.status_code, 200
        )  # Assuming a successful response code

        self.assertTrue(
            EventMember.objects.filter(
                firstname="Hans", lastname="Huber", event=self.event
            ).exists()
        )

    def test_add_member_with_standard_form_to_full_event(self):
        self.event.capacity = 2
        self.event.save()
        form_data = {
            "firstname": "Hans",
            "lastname": "Huber",
            "email": "hans@huber.de",
            "street": "teststraße",
            "city": "teststadt",
            "postcode": "12345",
            "country": "DE",
        }
        # Post form data to the view
        # the follow=True is important
        response = self.client.post(
            reverse("event-add-member", args=[self.event.slug]), form_data, follow=True
        )
        self.assertEqual(
            response.status_code, 200
        )  # Assuming a successful response code

        self.assertEqual(
            EventMember.objects.get(
                firstname="Hans", lastname="Huber", event=self.event
            ).attend_status,
            "waiting",
        )
