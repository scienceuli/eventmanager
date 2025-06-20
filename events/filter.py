import urllib
import django_filters
from django import forms

from django.db.models import Count

from django.contrib.admin.filters import FieldListFilter
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from django.utils.encoding import force_str


from events.forms import DateRangeForm

from events.models import Event, EventCategory, EventMember


# admin filter: per default only future events
class PeriodFilter(SimpleListFilter):
    """
    Filter the Events Happening in the Past and Future
    ref: https://stackoverflow.com/questions/851636/default-filter-in-django-admin
    """

    default_value = "future"
    title = "Zeitraum"
    parameter_name = "period"

    def lookups(self, request, model_admin):
        """
        List the Choices available for this filter.
        """
        return (
            ("all", "Alle"),
            ("future", "noch nicht gestartet"),
            ("past", "abgeschlossen"),
        )

    def choices(self, changelist):
        """
        Overwrite this method to prevent the default "All".
        """
        value = self.value() or self.default_value
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == force_str(lookup),
                "query_string": changelist.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        """
        Returns the Queryset depending on the Choice.
        """
        value = self.value() or self.default_value
        now = timezone.now()
        if value == "future":
            return queryset.filter(first_day__gte=now) | queryset.filter(first_day=None)
        if value == "past":
            return queryset.filter(first_day__lt=now)
        return queryset.all()


class EventFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(
        queryset=EventCategory.shown_event_categories.annotate(
            events_count=Count("events")
        )
        .filter(events_count__gt=0)
        .order_by("position"),
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


class MVMembersFilter(django_filters.FilterSet):
    class Meta:
        model = EventMember
        fields = [
            "firstname",
            "lastname",
            "email",
            "date_created",
            "member_type",
            "vote_transfer",
            "vote_transfer_check",
            "agree",
        ]


class FormFilter(FieldListFilter):
    initial = {}
    form_class = None

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        expected = self.expected_parameters()
        others = {k: v for k, v in request.GET.items() if k not in expected}
        self.other_query_string = urllib.parse.urlencode(others)
        self.form = self.get_form(request)
        self.form.is_valid()

    def form_lookups(self):
        raise NotImplementedError(
            "subclasses of FormFieldFilter must provide a form_lookups() method"
        )

    def expected_parameters(self):
        return [item[0] for item in self.form_lookups()]

    def get_initial(self):
        return self.initial.copy()

    def get_form_kwargs(self, request):
        return {
            "prefix": self.field.name,
            "initial": self.get_initial(),
            "data": request.GET or None,
        }

    def get_form(self, request):
        return self.form_class(**self.get_form_kwargs(request))

    def get_lookups(self):
        lookups = {k.split("-")[1]: v for k, v in self.form_lookups()}
        data = self.form.cleaned_data if self.form.is_bound else {}
        return {v: data[k] for k, v in lookups.items() if data.get(k)}

    def queryset(self, request, queryset):
        return queryset.filter(**self.get_lookups())

    def choices(self, changelist):
        return ()


class DateRangeFilter(FormFilter):
    template = "admin/daterange/filter_form.html"
    form_class = DateRangeForm

    def form_lookups(self):
        name = self.field.name
        return (
            ("%s-start" % name, "%s__gte" % name),
            ("%s-until" % name, "%s__lt" % name),
        )
