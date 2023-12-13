from django.db import models
from django.db.models.query import QuerySet


class ShownEventCategoriesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(show=True)
