import datetime as dt

from django.db import IntegrityError
from django.test import TestCase

from events.models import Event, EventHighlight


class EventHighlightTests(TestCase):
    def test_single_instance(self):
        constraint_name = "events_eventhighlight_single_instance"
        with self.assertRaisesMessage(IntegrityError, constraint_name):
            EventHighlight.objects.create(
                id=2,
                event=Event.objects.all().first(),
            )
