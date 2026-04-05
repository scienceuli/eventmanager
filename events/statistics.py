from collections import Counter
import ast
from .models import EventMember

from events.utils.utils import parse_memberships


def membership_statistics():
    counter = Counter()

    for raw in EventMember.objects.exclude(attend_status="cancelled").values_list(
        "memberships", flat=True
    ):
        items = parse_memberships(raw)
        counter.update(items)

    return counter
