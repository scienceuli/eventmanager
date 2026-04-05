# events/services/strategies/base.py

class BaseRegistrationStrategy:
    def get_form(self, event, data=None):
        raise NotImplementedError

    def build_member_data(self, form, event):
        raise NotImplementedError

    def build_formatting_dict(self, form, event, member):
        raise NotImplementedError

    def get_success_message(self, event, member):
        return "Vielen Dank für Ihre Anmeldung."
