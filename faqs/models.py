from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils.text import slugify
from django.shortcuts import reverse

from . import utils


# Create your models here.
class Question(models.Model):
    category = models.ForeignKey(
        "category", on_delete=models.SET_NULL, null=True, blank=True
    )
    question = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    position = models.PositiveSmallIntegerField(
        verbose_name="Reihenfolge",
        null=True,
        help_text="Reihenfolge der Programme in der Anezige",
    )

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        self.slug = slugify(self.question)[:150]

        Question.objects.filter(
            position__gte=self.position, category=self.category
        ).update(position=F("position") + 1)

        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("faqs:question_detail", args=(self.category.slug, self.slug))


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField()
    slug = models.SlugField(max_length=10, blank=True)

    def __str__(self):
        return self.answer

    class Meta:
        order_with_respect_to = "question"

    def save(self, *args, **kwargs):
        # if first time saving add a new slug
        if not self.pk or not self.slug:
            new_slug = utils.create_random_slug(5)
            while Answer.objects.filter(slug=new_slug, answer=self.answer).exists():
                new_slug = utils.create_random_slug()
            self.slug = new_slug
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)[:50]
        return super().save(*args, **kwargs)
