from dataclasses import dataclass, field

from .strategies import get_strategy

from events.utils import check_utils
from events.utils.member_utils import create_member
from events.utils.email_utils import send_registration_emails

@dataclass
class RegistrationResult:
    success: bool = False
    errors: list[str] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)

class EventRegistrationService:

    def register(self, form, event):
        result = RegistrationResult()
        email = form.cleaned_data.get("email")

        if check_utils.on_blacklist_check(email):
            result.errors.append("Ihre Anfrage konnte nicht verarbeitet werden.")
            return result

        if not check_utils.no_duplicate_check(email, event):
            result.errors.append(
                f"Es gibt bereits eine Anmeldung für {email} an {event}"
            )
            return result

        strategy = get_strategy(event)

        member_data = strategy.build_member_data(form, event)
        member = create_member(event, member_data)

        if not member.survey_token:
            member.survey_token = uuid.uuid4()

        formatting_dict = strategy.build_formatting_dict(form, event, member)

        vfll_sent, member_sent = send_registration_emails(
            event, form, formatting_dict, member.attend_status
        )

        if vfll_sent:
            member.mail_to_admin = True
        if member_sent:
            member.mail_to_member = True

        member.save()

        result.successes.append(strategy.get_success_message(event, member))
        result.success = True

        return result
