import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from events.api_models import VfllMemberEmail


class Command(BaseCommand):
    help = "Fetch emails from the external API and update the local database."

    def handle(self, *args, **kwargs):
        token_url = settings.TOKEN_URL
        members_url = settings.MEMBER_ADMIN_URL
        username = settings.MEMBER_ADMIN_USER_USERNAME
        password = settings.MEMBER_ADMIN_USER_SECRET

        auth_ = {"username": username, "password": password}  # This is a Django user.

        r1 = requests.post(token_url, data=auth_)

        token_ = r1.json()["token"]
        headers = {"Authorization": "Token " + token_}

        r2 = requests.get(
            members_url,
            headers=headers,
        )
        if r2.status_code == 200:
            emails = r2.json()
            # Update local database
            for email_data in emails:
                email, created = VfllMemberEmail.objects.get_or_create(
                    email=email_data["email"]
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Added new email: {email.email}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Email already exists: {email.email}")
                    )
        else:
            self.stderr.write(self.style.ERROR("Failed to fetch emails from the API."))
