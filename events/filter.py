import django_filters
from events.models import Event


class EventFilter(django_filters.FilterSet):

    date_range = django_filters.DateFromToRangeFilter(
        label="Datumsbereich",
        field_name="first_day",
        widget=django_filters.widgets.RangeWidget(attrs={"type": "date"}),
    )

    class Meta:
        model = Event
        fields = [
            "first_day",
        ]
