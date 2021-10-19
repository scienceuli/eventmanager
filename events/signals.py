from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from events.models import Event, EventDay, EventSpeakerThrough

from moodle.management.commands.moodle import create_or_update_trainer


# @receiver(post_save, sender=Event)
def first_day_handler(sender, instance, **kwargs):
    event = instance.event
    # print(event.get_first_day_start_date())
    Event.objects.filter(id=event.id).update(first_day=event.get_first_day_start_date())


post_save.connect(first_day_handler, sender=EventDay)

# try to build a trainer handler
# @receiver(m2m_changed, sender=EventSpeakerThrough)
def event_speakers_changed(sender, instance, **kwargs):
    print("event_speakers_changed called")
    moodle_id = instance.event.moodle_id
    speaker_email = instance.eventspeaker.email
    if moodle_id != 0 and speaker_email:
        moodle_new_user_flag = instance.event.moodle_new_user_flag
        moodle_standard_password = instance.event.moodle_standard_password
        speakers = []
        speakers.append(instance.eventspeaker)
        create_or_update_trainer(
            moodle_id, moodle_new_user_flag, moodle_standard_password, speakers
        )


post_save.connect(event_speakers_changed, sender=EventSpeakerThrough)
