from django.db import models

from events.abstract import BaseModel


class EmailTemplate(BaseModel):
    name = models.CharField(max_length=255)
    text_template = models.TextField("Vorlage für Text Email")
    html_template = models.TextField("Vorlage für Html Email", blank=True)
    counter = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Email-Vorlage"
        verbose_name_plural = "Email-Vorlagen"


    def __str__(self):
        return self.name

    def add_count(self, add=1):
        self.counter += add
        self.save()