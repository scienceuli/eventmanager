# event/tables.py
import django_tables2 as tables
from .models import EventMember


class EventMembersTable(tables.Table):
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
