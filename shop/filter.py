from datetime import datetime, date, timedelta

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


class YearQuarterFilter(admin.SimpleListFilter):
    """Custom filter for Year and Quarter"""

    title = "Jahr/Quartal"
    parameter_name = "year_quarter"

    def lookups(self, request, model_admin):
        """Provide filter options (years and quarters)."""
        current_year = date.today().year
        options = []

        # Add last 5 years with quarters
        for year in range(current_year, current_year - 5, -1):
            for quarter in range(1, 5):
                options.append((f"{year}-Q{quarter}", f"{year} - Q{quarter}"))

        return options

    def queryset(self, request, queryset):
        """Filter queryset based on selected year/quarter."""
        value = self.value()
        if value:
            year, quarter = map(int, value.replace("Q", "").split("-"))
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            start_date = datetime(year, start_month, 1, 0, 0, 0)
            end_date = datetime(year, end_month, 30, 23, 59, 59)

            return queryset.filter(payment_date__range=[start_date, end_date])
        return queryset
