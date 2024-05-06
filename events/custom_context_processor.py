from datetime import date, datetime

from django.db.models import Count
from django.conf import settings
from .models import Event, EventCategory


def category_renderer(request):
    return {
        #'all_categories': EventCategory.objects.all(),
        "all_categories": EventCategory.objects.annotate(events_count=Count("events"))
        .filter(events_count__gt=0)
        .filter(show=True)
        .order_by("position")
    }


def event_in_frontend_context(request):
    event_in_frontend = settings.EVENT_SHOWN_IN_FRONTEND
    return {"event_in_frontend": event_in_frontend}


def events_in_frontend_context(request):
    events_in_frontend = Event.objects.filter(edit_in_frontend=True).filter(
        first_day__gte=date.today()
    )
    return {"events_in_frontend": events_in_frontend}
