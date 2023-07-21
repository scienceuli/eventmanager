from decimal import Decimal


from django.db import models
from events.models import Event

from events.abstract import BaseModel, AddressModel
from shop.utils import premium_price

PAYMENT_TYPE_CHOICES = (
    ("p", "PayPal"),
    ("r", "Rechnung"),
)


class Order(AddressModel):
    firstname = models.CharField(verbose_name="Vorname", max_length=50)
    lastname = models.CharField(verbose_name="Nachname", max_length=50)
    academic = models.CharField("Titel", max_length=40, null=True, blank=True)
    company = models.CharField("Firma", max_length=255, null=True, blank=True)
    phone = models.CharField("Tel", max_length=64, blank=True)

    email = models.EmailField(verbose_name="E-Mail")
    payment_type = models.CharField(
        verbose_name="Bezahltyp",
        max_length=1,
        choices=PAYMENT_TYPE_CHOICES,
        default="p",
    )
    discounted = models.BooleanField(verbose_name="reduziert", default=True)
    paid = models.BooleanField(verbose_name="bezahlt", default=False)
    payment_date = models.DateTimeField(
        verbose_name="Bezahldatum", null=True, blank=True
    )

    class Meta:
        ordering = ["-date_created"]
        indexes = [
            models.Index(fields=["-date_created"]),
        ]

    def __str__(self):
        return f"Bestellung {self.id}"

    def get_total_cost(self):
        costs = sum(item.get_cost() for item in self.items.all())
        return costs

    get_total_cost.short_description = "Betrag"

    # def get_premium_total_cost(self):  # was get_discounted_total_cost
    #     price = premium_price(self.get_total_cost())
    #     return price

    @property
    def get_order_number(self):
        return "V{:06d}".format(self.id)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    event = models.ForeignKey(
        Event, related_name="order_items", on_delete=models.CASCADE
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    premium_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        if self.order.discounted:
            return self.price * self.quantity
        return self.premium_price * self.quantity
