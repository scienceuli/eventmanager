from django.contrib import admin

from events.models import Event


class EventListFilter(admin.SimpleListFilter):
    title = "Veranstaltung"
    parameter_name = "event"

    def lookups(self, request, model_admin):
        list_of_events = []
        queryset = Event.objects.all().order_by("name")
        for event in queryset:
            list_of_events.append(
                (str(event.id), f"{event.name} ({event.get_first_day})")
            )
        return list_of_events

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(items__event__id=self.value())
        return queryset
