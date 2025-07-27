# event/tables.py
from django.utils.html import format_html
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

    # update = MemberUpdateLinkColumn(
    #     "ft-member-update",
    #     args=[A("pk")],
    #     orderable=False,
    #     text="Update",
    #     empty_values=(),
    # )

    class Meta:
        model = EventMember
        template_name = "django_tables2/bootstrap.html"
        fields = (
            "firstname",
            "lastname",
            "email",
        )


class MVEventMembersTable(tables.Table):
    counter = tables.Column(empty_values=(), orderable=False)
    mv = tables.BooleanColumn(verbose_name="MV",empty_values=(), orderable=False)
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
            'counter',
            'firstname',
            'lastname',
            'email',
            'mv',
            'tg',
            'vote_transfer',
            'vote_transfer_check',
            )
