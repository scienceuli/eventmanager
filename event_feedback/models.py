import uuid
from django.db import models

class Survey(models.Model):
    event = models.OneToOneField("events.Event", on_delete=models.CASCADE)

    def __str__(self):
        return f"Survey for {self.event}"


class SurveyCategory(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]


class SurveyQuestion(models.Model):
    category = models.ForeignKey(SurveyCategory, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)

    consent = models.BooleanField()
    final_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class QuestionAnswer(models.Model):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)

    rating = models.IntegerField()  # 1–5
    comment = models.TextField(blank=True)
