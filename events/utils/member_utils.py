from events.models import EventMember

def create_member(event, data):
    member = EventMember.objects.create(event=event, **data)
    return member
