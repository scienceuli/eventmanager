# f.py
#
from .base import BaseRegistrationStrategy

import events.forms

class FRegistrationStrategy(BaseRegistrationStrategy):
    def get_form(self, event, data=None):
        return Symposium2024Form(data, event_label=event.label)
