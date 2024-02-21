from django.core.management.base import BaseCommand

from shop.models import Order


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for order in Order.objects.all():
            if not order.payment_date:
                order.payment_date = order.date_created
                order.save()
