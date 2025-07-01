from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from .models import Event


def hitcount_view(request, model_admin, object):
    model = model_admin.model
    return render(
        request,
        "admin/events/hitcount.html",
        {
            "original": object,
        },
    )

@staff_member_required
def event_answers_summary(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    eventmembers = event.members.prefetch_related('answers__question')
    return render(request, 'admin/events/event_answers_summary.html', {
        'event': event,
        'eventmembers': eventmembers,
    })
