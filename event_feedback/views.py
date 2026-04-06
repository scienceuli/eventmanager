from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from .models import Survey, SurveyResponse, QuestionAnswer
from .forms import SurveyForm
from events.models import Event, EventMember

from event_feedback.services.feedback_service import SurveyService

def survey_view(request, token):
    service = SurveyService()

    try:
        registration = service.get_registration_by_token(token)
    except Exception:
        raise Http404()

    survey = service.get_survey_for_registration(registration)

    if service.has_already_answered(registration):
        return render(request, "survey/already_done.html", {
                    "event": registration.event
                })

    if request.method == "POST":
        form = SurveyForm(request.POST, survey=survey)

        if form.is_valid():
            service.save_response(registration, survey, form)
            return render(request, "survey/thanks.html")
    else:
        form = SurveyForm(survey=survey)

    return render(request, "survey/form.html", {
        "form": form,
        "survey": survey,
    })


@staff_member_required
def survey_results_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    service = SurveyService()
    results = service.get_results(event)

    return render(request, "survey/results.html", {
        "event": event,
        "results": results,
    })
