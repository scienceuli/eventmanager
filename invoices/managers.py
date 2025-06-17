from django.db import models


class StandardInvoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(invoice_type='i')


class StornoInvoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(invoice_type='s')