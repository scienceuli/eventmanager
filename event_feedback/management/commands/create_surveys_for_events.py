from django.core.management.base import BaseCommand
from events.models import Event
from event_feedback.models import Survey
from event_feedback.services import SurveyService


class Command(BaseCommand):
    help = "Create surveys for events that don't have one"

    def handle(self, *args, **kwargs):
        service = SurveyService()

        events = Event.objects.all()

        created_count = 0

        for event in events:
            survey, created = service.create_survey(event)

            if created:
                service.create_default_structure(survey)
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} surveys"
        ))
