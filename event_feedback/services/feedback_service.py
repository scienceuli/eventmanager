import json
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.db.models import Avg, Count


from event_feedback.models import Survey, SurveyCategory, SurveyQuestion, QuestionAnswer
from events.models import EventMember
from event_feedback.models import SurveyResponse

class SurveyService:
    def create_survey(self, event, template_name="default"):
        survey, created = Survey.objects.get_or_create(event=event)

        # Prevent duplicate structure creation
        if created or not survey.categories.exists():
            self.create_structure(survey, template_name)

        return survey

    def build_survey_link(self, registration):
        path = reverse("feedback:survey-view", args=[registration.survey_token])
        return f"{settings.EMAIL_LINK_DOMAIN}{path}"

    def get_registration_by_token(self, token):
        return EventMember.objects.select_related("event__survey").get(
            survey_token=token
        )

    def get_survey_for_registration(self, registration):
        return registration.event.survey

    def has_already_answered(self, registration):
        return SurveyResponse.objects.filter(registration=registration).exists()

    def save_response(self, registration, survey, form):
        response = SurveyResponse.objects.create(
            survey=survey,
            registration=registration,
            consent=form.cleaned_data["consent"],
            final_comment=form.cleaned_data["final_comment"],
        )

        for category in survey.categories.all():
            for q in category.questions.all():
                QuestionAnswer.objects.create(
                    response=response,
                    question=q,
                    rating=form.cleaned_data[f"rating_{q.id}"],
                    comment=form.cleaned_data[f"comment_{q.id}"],
                )

        return response

    def create_structure(self, survey, template_name="default"):
        template_path = Path(__file__).parent.parent / "survey_templates" / f"{template_name}.json"

        with open(template_path) as f:
            data = json.load(f)

        for cat_data in data["categories"]:
            category = SurveyCategory.objects.create(
                survey=survey,
                name=cat_data["name"],
                order=cat_data.get("order", 0)
            )

            for q_data in cat_data["questions"]:
                SurveyQuestion.objects.create(
                    category=category,
                    text=q_data["text"],
                    order=q_data.get("order", 0)
                )


    def get_results(self, event):
        survey = event.survey

        results = []

        for category in survey.categories.all():
            questions_data = []

            for question in category.questions.all():
                stats = question.questionanswer_set.aggregate(
                    avg_rating=Avg("rating"),
                    count=Count("id")
                )

                comments = question.questionanswer_set.exclude(
                    comment=""
                ).values_list("comment", flat=True)

                questions_data.append({
                    "question": question,
                    "avg": round(stats["avg_rating"] or 0, 2),
                    "count": stats["count"],
                    "comments": comments,
                })

            results.append({
                "category": category,
                "questions": questions_data,
            })

        return results
