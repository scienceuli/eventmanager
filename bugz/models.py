from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from events.abstract import BaseModel

def return_date_time():
        now = timezone.now()
        return now + timedelta(days=7)


class Project(BaseModel):
    title = models.CharField(max_length=100)
    description = models.TextField(verbose_name="Beschreibung", max_length=2000)

    def __str__(self):
        return self.title

class Task(BaseModel):
    SEVERITY_CHOICES = [
        (1, 'niedrig'),
        (2, 'mittel'),
        (3, 'hoch')
    ]

    TASK_TYPE_CHOICES = [
        (1, 'Bug'),
        (2, 'Feature')
    ]

    STATUS_CHOICES = [
        (1, 'offen'),
        (2, 'in Arbeit'),
        (3, 'fertig')
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=1)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    title = models.CharField("Titel", max_length=100)
    description = models.TextField(verbose_name="Beschreibung", max_length=2000)
    task_type = models.PositiveSmallIntegerField("Typ", choices=TASK_TYPE_CHOICES, default=1)
    severity = models.PositiveSmallIntegerField(verbose_name='Priorität', choices=SEVERITY_CHOICES, default=1)
    close_date = models.DateField("erledigen bis", null=True, blank=True, default=return_date_time)
    status = models.PositiveSmallIntegerField(verbose_name='Status', choices=STATUS_CHOICES, default=1)

    def __str__(self):
        return self.title

class Comment(BaseModel):
    task = models.ForeignKey(Task, verbose_name="Kommentar", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField("Titel", max_length=100)
    description = models.TextField(verbose_name="Beschreibung", max_length=2000)

    def __str__(self):
        return f"Kommentar von {self.created_by.username} am {self.date_created}" 


    