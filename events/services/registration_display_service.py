from dataclasses import dataclass
from datetime import date


def _pre_registration_text(next_year: int) -> str:
    open_date = date(next_year, 1, 1)
    return (
        f"Für diese Fortbildung können Sie sich ab dem 1. {open_date:%B %Y} "
        "anmelden. Gern schicken wir Ihnen eine schriftliche Erinnerung zu, "
        "sobald die Anmeldung möglich ist. Lassen Sie sich gern für eine "
        "Erinnerungs-E-Mail vormerken."
    )


@dataclass
class RegistrationDisplay:
    show_registration: bool = True
    show_button: bool = False
    show_pre_registration: bool = False
    registration_text: str = ""
    registration_button: str = ""
    additional_text: str = ""


class RegistrationDisplayService:
    """
    Determines what to show in the 'Anmeldung' section of the event detail
    page: pre-registration, open registration (with button text depending on
    close date / capacity), or plain informational text.
    """

    def get_display(self, event, override_registration_possible=False) -> RegistrationDisplay:
        display = RegistrationDisplay()

        if self._is_next_year_event(event) and event.category.registration:
            display.show_pre_registration = True
            display.registration_text = _pre_registration_text(event.first_day.year)
            return display

        if override_registration_possible:
            event.registration_possible = True
            event.category.registration = True

        if not event.category.registration:
            if event.registration:
                display.registration_text = event.registration
            else:
                display.show_registration = False
        elif event.registration_possible:
            display.show_button = True
            self._apply_open_registration(display, event)
        else:
            display.show_registration = False

        return display

    @staticmethod
    def _is_next_year_event(event):
        if not event.first_day:
            return False
        next_year_start = date(date.today().year + 1, 2, 1)
        return event.first_day >= next_year_start

    def _apply_open_registration(self, display, event):
        display.registration_text = event.registration

        if event.registration_message:
            display.registration_text += (
                f"<span class='font-medium'>{event.registration_message}</span><br/>"
            )
            display.registration_button = "Online anmelden"
            return

        if not event.close_date:
            display.registration_button = "Online anmelden"
            return

        display.registration_text += (
            "<span class='font-medium'>Anmeldeschluss: {:%d. %B %Y}</span><br/>".format(
                event.close_date
            )
        )
        closed = event.is_closed_for_registration()
        display.registration_text += self._availability_fragment(event, closed)
        (
            display.registration_button,
            display.additional_text,
        ) = self._availability_button_and_note(event, closed)

    @staticmethod
    def _availability_fragment(event, closed):
        if event.is_full():
            return "<span class='italic'>Leider ausgebucht</span>" + ("" if closed else " ")
        if closed:
            if event.few_remaining_places():
                return "<span class='text-vfllred'>Anmeldung möglich, da noch wenige freie Plätze</span>"
            return "<span class='text-vfllred'>Anmeldung möglich, da noch freie Plätze</span>"
        if event.few_remaining_places():
            return "<span class='text-vfllred'>Nur noch wenige freie Plätze!</span>"
        return ""

    @staticmethod
    def _availability_button_and_note(event, closed):
        if event.is_full():
            additional_text = "Nach Abschluss des Bestellvorgangs werden Sie auf die Warteliste gesetzt."
            if not closed:
                additional_text = "*" + additional_text
            return "Auf die Warteliste", additional_text
        return "Online anmelden", ""
