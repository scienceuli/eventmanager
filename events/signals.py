from django.db.models.signals import post_save
from django.dispatch import receiver
from events.models import Event, EventDay


# @receiver(post_save, sender=Event)
def first_day_handler(sender, instance, **kwargs):
    event = instance.event
    # print(event.get_first_day_start_date())
    Event.objects.filter(id=event.id).update(first_day=event.get_first_day_start_date())


post_save.connect(first_day_handler, sender=EventDay)
