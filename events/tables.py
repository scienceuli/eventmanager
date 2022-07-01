# event/tables.py
import django_tables2 as tables
from django_tables2.utils import A

import itertools

from .models import EventMember


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

    counter = tables.Column(empty_values=(), orderable=False)

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
            "event",
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

    def render_counter(self):
        self.row_counter = getattr(self, "row_counter", itertools.count())
        return next(self.row_counter) + self.page.start_index()
        # self.page.sart_index() is default Table function and return number of start index per page

    view = MemberViewLinkColumn(
        "ft-member-detail",
        args=[A("pk")],
        orderable=False,
        text="View",
        empty_values=(),
    )

    update = MemberUpdateLinkColumn(
        "ft-member-update",
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
        )
