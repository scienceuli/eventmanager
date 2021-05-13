import django_filters
from django import forms

from events.models import Event, EventCategory


class EventFilter(django_filters.FilterSet):

    category = django_filters.ModelChoiceFilter(
        queryset=EventCategory.objects.all(),
        empty_label="Alle",
    )

    first_day = django_filters.DateFromToRangeFilter(
        label="Datum eingrenzen",
        field_name="first_day",
        lookup_expr="month",
        widget=django_filters.widgets.RangeWidget(
            attrs={
                "type": "date",
                "class": "w-1/4 p-3 mt-2 text-gray-700 bg-gray-200 appearance-none focus:outline-none focus:bg-gray-300 focus:shadow-inner",
                # "class": "w-full h-10 px-3 text-base placeholder-gray-600 border rounded-lg focus:shadow-outline",
            }
        ),
    )

    class Meta:
        model = Event
        fields = [
            "category",
            "first_day",
        ]
        # fields = []