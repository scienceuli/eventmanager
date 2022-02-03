from django.db.models import Count
from .models import EventCategory


def category_renderer(request):
    return {
        #'all_categories': EventCategory.objects.all(),
        "all_categories": EventCategory.objects.annotate(events_count=Count("events"))
        .filter(events_count__gt=0)
        .filter(show=True)
        .order_by("position")
    }
