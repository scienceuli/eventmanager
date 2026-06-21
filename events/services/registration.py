import uuid
from dataclasses import dataclass, field

from events.services.strategies import get_strategy
from events.utils import check_utils
from events.utils.member_utils import create_member


@dataclass
class RegistrationResult:
    success: bool = False
    member: object = None
    strategy: object = None
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
        print(f"member_data: {member_data}")
        member = create_member(event, member_data)

        if not member.survey_token:
            member.survey_token = uuid.uuid4()

        member.save()

        result.member = member
        newsletter = form.cleaned_data.get("newsletter", False)
        result.successes.append(
            strategy.get_success_message(event, member, newsletter=newsletter)
        )
        result.success = True
        result.strategy = strategy

        return result
