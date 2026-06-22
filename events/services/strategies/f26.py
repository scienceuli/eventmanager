# f26.py
#
import events.forms as evforms
from events.utils import form_utils
from events.utils.utils import get_utilisations

from .base import BaseRegistrationStrategy


class F26RegistrationStrategy(BaseRegistrationStrategy):
    def get_form(self, event, data=None):
        ws_utilisations, tour_utilisations = get_utilisations(event)
        return evforms.Symposium2026Form(
            data,
            event_label=event.label,
            ws_utilisations=ws_utilisations,
            tour_utilisations=tour_utilisations,
        )

    def build_member_data(self, form, event):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_additional_form_data(form, event, "f26"))

        f26_data = form_utils.get_f26_form_data(form)
        if "vfll" in f26_data.memberships:
            vfll = True
        else:
            vfll = False

        data.update(
            {
                "agree": True,
                "attend_status": "registered",
                "data": f26_data,
                "vfll": vfll,
            }
        )
        return data

    def build_formatting_dict(self, form, event, member):
        data = form_utils.get_personal_form_data(form)
        data.update(form_utils.get_additional_form_data(form, event, "f26"))
        data.update(form_utils.get_f26_form_data(form))
        data["attend_status"] = "registered"
        return data

    def get_success_message(self, event, member, newsletter=False):
        return "Vielen Dank für deine Anmeldung."
