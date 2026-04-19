# f24.py
#
from .base import BaseRegistrationStrategy
from events.utils import form_utils
import events.forms

class F24RegistrationStrategy(BaseRegistrationStrategy):
    def get_form(self, event, data=None):
        return Symposium2024Form(data, event_label=event.label)

    def build_member_data(self, form, event):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_additional_form_data(form, event, "f24"))
        data.update(form_utils.get_f24_form_data(form))

        data.update({
            "agree": True,
            "attend_status": "registered",
            "data": form_utils.get_f24_form_data(form),
        })

        return data

    def build_formatting_dict(self, form, event, member):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_f24_form_data(form))
        data["attend_status"] = "registered"
        return data

    def get_success_message(self, event, member, newsletter=False):
        return "Vielen Dank für deine Anmeldung."
