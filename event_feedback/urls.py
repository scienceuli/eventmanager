from django.urls import path
from . import views

app_name = "feedback"

urlpatterns = [
    path("survey/<uuid:token>/", views.survey_view, name="survey-view"),
    path("survey/results/<int:event_id>/", views.survey_results_view, name="survey-results")
]
