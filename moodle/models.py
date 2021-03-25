from django.db import models
from events.abstract import BaseModel

class MoodleUser(BaseModel):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField(max_length=255)
    moodle_id = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('lastname',)

    def __str__(self):
        return f"{self.lastname}, {self.firstname}"

