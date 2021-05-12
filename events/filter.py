import django_filters
from events.models import Event, EventCategory


class EventFilter(django_filters.FilterSet):

    category = django_filters.ModelChoiceFilter(queryset=EventCategory.objects.all())

    first_day = django_filters.DateFromToRangeFilter(
        label="Datumsbereich",
        field_name="first_day",
        lookup_expr="month",
        widget=django_filters.widgets.RangeWidget(attrs={"type": "date"}),
    )

    class Meta:
        model = Event
        fields = [
            "category",
            "first_day",
        ]
        # fields = []
