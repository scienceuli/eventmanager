from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver
from events.models import Event, EventDay, EventSpeakerThrough
from event_feedback.services.feedback_service import SurveyService


def event_dates_handler(sender, instance, **kwargs):
    """Keep Event.first_day/last_day in sync with its event days, no matter
    whether they are edited in the admin, the frontend views or the shell."""
    event = Event.objects.filter(pk=instance.event_id).first()
    if event:
        event.update_dates()


post_save.connect(event_dates_handler, sender=EventDay)
post_delete.connect(event_dates_handler, sender=EventDay)
