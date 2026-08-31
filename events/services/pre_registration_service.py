from dataclasses import dataclass, field


@dataclass
class PreRegistrationResult:
    success: bool = False
    pre_registration: object = None
    errors: list = field(default_factory=list)
    successes: list = field(default_factory=list)


class PreRegistrationService:
    def register(self, form, event):
        result = PreRegistrationResult()

        pre_registration = form.save(commit=False)
        pre_registration.event = event
        pre_registration.save()

        result.pre_registration = pre_registration
        result.success = True
        result.successes.append(
            "Vielen Dank für Ihre Vormerkung! Wir informieren Sie, sobald die "
            "Anmeldung für diese Veranstaltung möglich ist."
        )
        return result
