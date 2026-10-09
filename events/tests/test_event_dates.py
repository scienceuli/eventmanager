from datetime import date, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from events.models import (
    Event,
    EventCategory,
    EventDay,
    EventFormat,
    EventOrganizer,
)


class EventDatesTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="testcat", show=True)
        cls.eventformat = EventFormat.objects.create(name="testformat")
        cls.organizer = EventOrganizer.objects.create(name="testorga")
        cls.day1 = date.today() + timedelta(days=30)
        cls.day2 = date.today() + timedelta(days=32)


class EventDayChangesUpdateDatesTest(EventDatesTestBase):
    def setUp(self):
        self.event = Event.objects.create(
            name="Test Event",
            category=self.category,
            eventformat=self.eventformat,
            label="test-event",
            price="10.00",
        )

    def add_day(self, start_date):
        return EventDay.objects.create(
            event=self.event,
            start_date=start_date,
            start_time=time(10),
            end_time=time(12),
        )

    def test_adding_days_sets_first_and_last_day(self):
        self.add_day(self.day2)
        self.add_day(self.day1)
        self.event.refresh_from_db()
        self.assertEqual(self.event.first_day, self.day1)
        self.assertEqual(self.event.last_day, self.day2)

    def test_deleting_day_updates_dates(self):
        first = self.add_day(self.day1)
        self.add_day(self.day2)
        first.delete()
        self.event.refresh_from_db()
        self.assertEqual(self.event.first_day, self.day2)
        self.assertEqual(self.event.last_day, self.day2)

    def test_deleting_event_with_days_works(self):
        self.add_day(self.day1)
        self.event.delete()
        self.assertFalse(Event.objects.filter(label="test-event").exists())


class EventCreateViewDatesTest(EventDatesTestBase):
    def setUp(self):
        user = User.objects.create_user("creator", password="pw")
        user.user_permissions.add(Permission.objects.get(codename="add_event"))
        self.client.force_login(user)

    def post_data(self, **days):
        data = {
            settings.HONEYPOT_FIELD_NAME: "",
            "name": "Frontend Event",
            "category": self.category.pk,
            "eventformat": self.eventformat.pk,
            "organizer": self.organizer.pk,
            "pub_status": "PUB",
            "fees": "keine",
            "price": "10.00",
            "event_documents-TOTAL_FORMS": "0",
            "event_documents-INITIAL_FORMS": "0",
            "event_days-TOTAL_FORMS": str(len(days)),
            "event_days-INITIAL_FORMS": "0",
        }
        for i, start_date in enumerate(days.values()):
            data[f"event_days-{i}-start_date"] = start_date.isoformat()
            data[f"event_days-{i}-start_time"] = "10:00"
            data[f"event_days-{i}-end_time"] = "12:00"
        return data

    def test_create_view_sets_first_and_last_day(self):
        response = self.client.post(
            reverse("event-create"), self.post_data(a=self.day2, b=self.day1)
        )
        form = response.context["form"] if response.context else None
        self.assertEqual(response.status_code, 302, form.errors if form else "")

        event = Event.objects.get(name="Frontend Event")
        self.assertEqual(event.first_day, self.day1)
        self.assertEqual(event.last_day, self.day2)
