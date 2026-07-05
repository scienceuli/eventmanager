# event/tables.py
import itertools

import django_tables2 as tables
from django.utils.html import format_html
from django_tables2.utils import A

from .choices import (
    FOOD_PREFERENCE_CHOICES,
    TAKES_PART_CHOICES_MV,
    TOUR_CHOICES_2026,
    WS2026_CHOICES,
)
from .models import EventMember
from .utils.utils import boolean_translate

_TOUR_LABEL_TO_KEY = {label: key for key, label in TOUR_CHOICES_2026}
_WS2026_LABEL_TO_KEY = {label: key for key, label in WS2026_CHOICES}
_TAKES_PART_LABEL_TO_KEY = {label: key for key, label in TAKES_PART_CHOICES_MV}
_FOOD_PREFERENCE_LABEL_TO_KEY = {label: key for key, label in FOOD_PREFERENCE_CHOICES}


class MemberViewLinkColumn(tables.LinkColumn):
    def render(self, record, value):
        return super().render(record, value)


class MemberUpdateLinkColumn(tables.LinkColumn):
    def render(self, record, value):
        return super().render(record, value)


class MemberDeleteLinkColumn(tables.LinkColumn):
    def render(self, record, value):
        return super().render(record, value)


class EventMembersTable(tables.Table):
    counter = tables.Column(verbose_name="#", empty_values=(), orderable=False)

    def render_counter(self):
        self.row_counter = getattr(self, "row_counter", itertools.count())
        return next(self.row_counter) + self.page.start_index()
        # self.page.sart_index() is default Table function and return number of start index per page

    view = MemberViewLinkColumn(
        "member-detail",
        args=[A("pk")],
        orderable=False,
        text="View",
        empty_values=(),
    )
    update = MemberUpdateLinkColumn(
        "member-update",
        args=[A("pk")],
        orderable=False,
        text="Update",
        empty_values=(),
    )
    delete = MemberDeleteLinkColumn(
        "member-delete",
        args=[A("pk")],
        orderable=False,
        text="Del",
        empty_values=(),
    )

    class Meta:
        model = EventMember
        template_name = "django_tables2/bootstrap.html"
        fields = (
            "counter",
            "firstname",
            "lastname",
            "email",
            "member_type",
            "vote_transfer",
            "vote_transfer_check",
            "date_created",
            "attend_status",
        )


class FTEventMembersTable(tables.Table):
    counter = tables.Column(empty_values=(), orderable=False)
    tour = tables.Column(verbose_name="Tour", empty_values=(), orderable=False)
    ws2026 = tables.Column(verbose_name="WS", empty_values=(), orderable=False)
    takes_part_in_mv = tables.Column(
        verbose_name="Teilnahme", empty_values=(), orderable=False
    )
    dinner_one = tables.BooleanColumn(
        yesno="✔,✘", verbose_name="AE Fr", empty_values=(), orderable=False
    )
    dinner_two = tables.BooleanColumn(
        yesno="✔,✘", verbose_name="AE Sa", empty_values=(), orderable=False
    )
    food_preferences = tables.Column(
        verbose_name="Essen", empty_values=(), orderable=False
    )

    def render_counter(self):
        self.row_counter = getattr(self, "row_counter", itertools.count())
        return next(self.row_counter) + self.page.start_index()

    def render_tour(self, record):
        if record.data:
            label = record.data.get("tour", "")
            return _TOUR_LABEL_TO_KEY.get(label, label)
        return ""

    def render_ws2026(self, record):
        if record.data:
            label = record.data.get("ws2026", "")
            return _WS2026_LABEL_TO_KEY.get(label, label)
        return ""

    def render_dinner_one(self, record):
        if record.data:
            label = boolean_translate(record.data.get("dinner_one", ""))
            return label
        return ""

    def render_dinner_two(self, record):
        if record.data:
            label = boolean_translate(record.data.get("dinner_two", ""))
            return label
        return ""

    def render_food_preferences(self, record):
        if record.data:
            label = record.data.get("food_preferences", "")
            return _FOOD_PREFERENCE_LABEL_TO_KEY.get(label, label)
        return ""

    def render_takes_part_in_mv(self, record):
        if record.data:
            label = record.data.get("takes_part_in_mv", "")
            return _TAKES_PART_LABEL_TO_KEY.get(label, label)
        return ""

    view = MemberViewLinkColumn(
        "ft-member-detail",
        args=[A("pk")],
        orderable=False,
        text="👁",
        empty_values=(),
    )
    update = MemberUpdateLinkColumn(
        "member-data-update",
        args=[A("pk")],
        orderable=False,
        text="✎",
        empty_values=(),
    )
    delete = MemberDeleteLinkColumn(
        "ft-member-delete",
        args=[A("pk")],
        orderable=False,
        text="🗑️",
        empty_values=(),
    )

    class Meta:
        model = EventMember
        template_name = "django_tables2/bootstrap4.html"
        fields = (
            "firstname",
            "lastname",
            "email",
        )
        sequence = (
            "counter",
            "firstname",
            "lastname",
            "email",
            "takes_part_in_mv",
            "ws2026",
            "tour",
            "dinner_one",
            "dinner_two",
            "food_preferences",
            "view",
            "delete",
            "update",
        )


class MVEventMembersTable(tables.Table):
    counter = tables.Column(empty_values=(), orderable=False)
    mv = tables.BooleanColumn(verbose_name="MV", empty_values=(), orderable=False)
    tg = tables.BooleanColumn(verbose_name="TG", empty_values=(), orderable=False)

    def render_counter(self):
        self.row_counter = getattr(self, "row_counter", itertools.count())
        return next(self.row_counter) + self.page.start_index()
        # self.page.sart_index() is default Table function and return number of start index per page

    def render_mv(self, record):
        if record.data:
            mv_value = record.data.get("takes_part_in_mv", False)
            if mv_value:
                return format_html('<span class="true">✔</span>')
            else:
                return format_html('<span class="false">✘</span>')
        else:
            return False

    def render_tg(self, record):
        if record.data:
            tg_value = record.data.get("takes_part_in_ft", False)
            if tg_value:
                return format_html('<span class="true">✔</span>')
            else:
                return format_html('<span class="false">✘</span>')
        else:
            return False

    view = MemberViewLinkColumn(
        "mv-member-detail",
        args=[A("pk")],
        orderable=False,
        text="View",
        empty_values=(),
    )

    update = MemberUpdateLinkColumn(
        "mv-member-update",
        args=[A("pk")],
        orderable=False,
        text="Update",
        empty_values=(),
    )

    class Meta:
        model = EventMember
        template_name = "django_tables2/bootstrap.html"
        fields = (
            "firstname",
            "lastname",
            "email",
            "vote_transfer",
            "vote_transfer_check",
        )
        sequence = (
            "counter",
            "firstname",
            "lastname",
            "email",
            "mv",
            "tg",
            "vote_transfer",
            "vote_transfer_check",
        )
