from django.db import models
from .abstract import SingletonModel

class SiteSettings(SingletonModel):
    vfll_recipient_payment = models.CharField(max_length=255, default="Verband der Freien Lektorinnen und Lektoren e. V.")
    vfll_bank_account = models.CharField(max_length=255, default="GLS Bank // IBAN: DE67430609676032523702 // BIC: GENODEM1GLS", blank=True)

    def __str__(self):
        return "Site Settings"
