from decimal import Decimal

from django.contrib.auth.models import User

from django.db import models

from events.abstract import BaseModel, AddressModel
from shop.utils import premium_price

PAYMENT_TYPE_CHOICES = (
    ("n", "---"),
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
        default="r",
    )
    discounted = models.BooleanField(verbose_name="reduziert", default=True)
    paid = models.BooleanField(verbose_name="bezahlt", default=False)
    storno = models.BooleanField(verbose_name="Storno", default=False)
    payment_date = models.DateTimeField(
        verbose_name="Rechnungsdatum", null=True, blank=True
    )
    payment_receipt = models.DateTimeField(
        verbose_name="Zahlungseingang", null=True, blank=True
    )

    mail_sent_date = models.DateTimeField(
        verbose_name="Rechnungsversand", null=True, blank=True
    )
    reminder_sent_date = models.DateTimeField(
        verbose_name="Mahnungsversand", null=True, blank=True
    )

    download_marker = models.BooleanField(default=False)

    # these fields are for overwriting event name and event date
    replacement_event = models.CharField(
        "Ersatzangabe Event Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Zum Überschreiben des automatisch erzeugten Veranstaltungstitels. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.",
    )
    replacement_date = models.CharField(
        "Ersatzangabe Event Datum",
        max_length=40,
        null=True,
        blank=True,
        help_text="Zum Überschreiben des automatisch erzeugten Veranstaltungsdatums. Funktioniert nur, wenn die Rechnung nur 1 NICHT STORNIERTE Veranstaltung enthält.",
    )
    use_replacements = models.BooleanField(
        "Ersatzangaben benutzen",
        default=False,
        help_text="Anklicken, um Ersatzangaben zu benutzen",
    )

    class Meta:
        ordering = ["-date_created"]
        indexes = [
            models.Index(fields=["-date_created"]),
        ]

    def __str__(self):
        return f"Bestellung {self.id}"

    def get_total_cost(self):
        costs = sum(item.get_cost() for item in self.items.filter(status="r"))
        return costs

    get_total_cost.short_description = "Betrag"

    # def get_premium_total_cost(self):  # was get_discounted_total_cost
    #     price = premium_price(self.get_total_cost())
    #     return price

    @property
    def get_order_number(self):
        return "V{:06d}".format(self.id)

    def get_registered_items_events(self):
        """returns items/events of an order with status=registered"""
        order_items = self.items.filter(status="r")

        # Extract the events from the order_items
        order_events = [order_item.event for order_item in order_items]

        return order_events


ORDER_ITEM_STATUS_CHOICES = (
    ("r", "registriert"),
    ("w", "Warteliste"),
    ("s", "storniert"),
    ("n", "nicht erschienen"),
    ("u", "unklar"),
)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    event = models.ForeignKey(
        "events.Event", related_name="order_items", on_delete=models.CASCADE
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    premium_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    is_action_price = models.BooleanField(default=False)
    status = models.CharField(
        max_length=1, choices=ORDER_ITEM_STATUS_CHOICES, default="r"
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        if self.order.discounted:
            return self.price * self.quantity
        return self.premium_price * self.quantity

    def get_cost_property(self):
        return self.get_cost()

    get_cost_property.short_description = "Betrag"

    get_cost_property = property(get_cost_property)

    @property
    def get_invoice_number(self):
        return self.order.get_order_number

    get_invoice_number.fget.short_description = "R-Nr."

    @property
    def get_order_name(self):
        return f"{self.order.lastname}, {self.order.firstname}"

    @property
    def get_payment_type(self):
        return self.order.payment_type

    def save(self, *args, **kwargs):
        self.cost = self.get_cost()
        super().save(*args, **kwargs)


class OrderNote(BaseModel):
    order = models.ForeignKey(
        Order, verbose_name="Bestellung", related_name="notes", on_delete=models.CASCADE
    )
    title = models.CharField(verbose_name="Titel", max_length=255)
    note = models.TextField(verbose_name="Notiz")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date_created"]
        verbose_name = "Notiz"
        verbose_name_plural = "Notizen"

    def __str__(self):
        return self.title
