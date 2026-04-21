# simple.py

from .base import BaseRegistrationStrategy
from events.utils import form_utils
import events.forms as forms

from event_feedback.services.feedback_service import SurveyService

class SimpleRegistrationStrategy(BaseRegistrationStrategy):

    def get_form(self, event, data=None):
        kwargs = {"initial": {"country": "DE"}} if data is None else {}

        if event.registration_form == "s":
            return forms.EventMemberForm(data, **kwargs)
        elif event.registration_form == "w":
            return forms.WelcomeMemberForm(data, **kwargs)

    def build_member_data(self, form, event):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_additional_form_data(form, event, event.registration_form))
        return data

    def build_formatting_dict(self, form, event, member):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_additional_form_data(form, event, event.registration_form))
        data["attend_status"] = member.attend_status
        survey_service = SurveyService()
        survey_service.ensure_survey(event)
        data["survey_info"] = f"Feedback-Link: {survey_service.build_survey_link(member)}"
        return data

    def get_success_message(self, event, member, newsletter=False):
        if member.attend_status == "waiting":
            return f"Sie wurden auf die Warteliste für die Veranstaltung {event} gesetzt."
        if event.get_first_day():
            success_string = f"Vielen Dank für Ihre Anmeldung zur Veranstaltung {event.name} am {event.get_first_day()}."
        else:
            success_string = f"Vielen Dank für Ihre Anmeldung zur Veranstaltung {event}."
        if newsletter:
            success_string += " Vielen Dank für Ihr Interesse am Newsletter."
        return success_string
