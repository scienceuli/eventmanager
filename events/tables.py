# event/tables.py
import django_tables2 as tables
from django_tables2.utils import A

from .models import EventMember


class MemberEditLinkColumn(tables.LinkColumn):
    def render(self, record, value):
        return super().render(record, value)


class MemberDeleteLinkColumn(tables.LinkColumn):
    def render(self, record, value):
        return super().render(record, value)


class EventMembersTable(tables.Table):
    edit = MemberEditLinkColumn(
        "member-detail",
        args=[A("pk")],
        orderable=False,
        text="Edit",
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
            "attend_status",
        )
