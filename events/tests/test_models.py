from django.test import TestCase

from events.models import Event, EventCategory, EventFormat, EventLocation

#############################
# Events
#############################


class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="testcat")
        cls.eventformat = EventFormat.objects.create(name="testformat")
        cls.location = EventLocation.objects.create(title="testloc")

        # Set up event
        Event.objects.create(
            name="Test Event",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            price="100.00",
        )

    def test_slug_from_title(self):
        event = Event.objects.get(id=1)
        slug = event.slug
        self.assertEqual(slug, "test-event-1")

    def test_get_absolute_url(self):
        event = Event.objects.get(id=1)
        slug = event.slug
        # This will also fail if the urlconf is not defined.
        self.assertEqual(event.get_absolute_url(), f"/detail/{slug}")
