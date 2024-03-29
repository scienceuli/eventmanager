import uuid

from django.db import models
from django_countries.fields import CountryField

from .choices import COUNTRIES


class BaseModel(models.Model):
    class Meta:
        abstract = True

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(verbose_name="angelegt am", auto_now_add=True)
    date_modified = models.DateTimeField(verbose_name="geändert am", auto_now=True)


class AddressModel(BaseModel):

    COUNTRIES_FIRST = ["DE", "AT", "CH", "FR", "IT"]

    class Meta:
        abstract = True

    address_line = models.CharField(
        "Adresszusatz", max_length=255, blank=True, null=True
    )
    street = models.CharField("Straße", max_length=55, blank=True, null=True)
    city = models.CharField("Stadt", max_length=255, blank=True, null=True)
    state = models.CharField("Bundesland", max_length=255, blank=True, null=True)
    postcode = models.CharField("PLZ", max_length=64, blank=True, null=True)
    country = CountryField("Land", default="DE")
