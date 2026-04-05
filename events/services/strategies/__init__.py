from .simple import SimpleRegistrationStrategy
from .mv import MVRegistrationStrategy
from .f24 import F24RegistrationStrategy
from .f import FRegistrationStrategy


def get_strategy(event):
    mapping = {
        "s": SimpleRegistrationStrategy(),
        "w": SimpleRegistrationStrategy(),
        "m": MVRegistrationStrategy(),
        "f24": F24RegistrationStrategy(),
        "f": FRegistrationStrategy(),
    }

    return mapping.get(event.registration_form, SimpleRegistrationStrategy())
