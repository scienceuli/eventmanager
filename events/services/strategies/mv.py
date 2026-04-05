# mv.py
#
from .base import BaseRegistrationStrategy
from events.utils import form_utils
import events.forms


class MVRegistrationStrategy(BaseRegistrationStrategy):
    def get_form(self, event, data=None):
        return forms.MV2025Form(data, event_label=event.label)

    def build_member_data(self, form, event):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_mv_form_data(form))
        data["data"] = form_utils.get_additional_mv_form_data(form)
        return data

    def build_formatting_dict(self, form, event, member):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_mv_form_data(form))

        if data.get("vote_transfer"):
            data["transfer_string"] = f"Stimme übertragen an: {data['vote_transfer']}"
        else:
            data["transfer_string"] = ""

        data["attend_status"] = "registered"
        return data

    def get_success_message(self, event, member):
        return "Vielen Dank für deine Anmeldung zur Mitgliederversammlung."
