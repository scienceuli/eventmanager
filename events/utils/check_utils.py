from django.conf import settings

from events.core_models import EmailBlacklist

def on_blacklist_check(email):
    if EmailBlacklist.objects.filter(email=email).exists():
        return True
    return False


def no_duplicate_check(email, event):
    if (
        email in list(event.members.all().values_list("email", flat=True))
        and settings.NO_MEMBER_DUPLICATES_ALLOWED
    ):
        return False
    return True
