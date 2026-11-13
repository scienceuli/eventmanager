from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from vfllnl.constants import SUBSCRIBE_STATUS_SUBSCRIBED
from vfllnl.models import NewsletterSubscription


class Command(BaseCommand):
    help = "Delete newsletter subscriptions that were never confirmed (double opt-in)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=settings.NEWSLETTER_CONFIRMATION_DAYS
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        # updated_at is refreshed whenever a new confirmation mail is sent
        qs = NewsletterSubscription.objects.filter(
            status=SUBSCRIBE_STATUS_SUBSCRIBED, updated_at__lt=cutoff
        )
        count = qs.count()
        if options["dry_run"]:
            for sub in qs:
                self.stdout.write(f"{sub.email}  {sub.updated_at:%Y-%m-%d}")
            self.stdout.write(f"{count} unconfirmed subscriptions would be deleted.")
            return
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} unconfirmed subscriptions."))
