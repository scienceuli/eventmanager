from django.core import management


def get_emails_from_vfll_memberadmin():
    management.call_command("fetch_emails")
