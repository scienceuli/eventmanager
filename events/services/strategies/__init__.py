from .f import FRegistrationStrategy
from .f24 import F24RegistrationStrategy
from .f26 import F26RegistrationStrategy
from .mv import MVRegistrationStrategy
from .simple import SimpleRegistrationStrategy


def get_strategy(event):
    mapping = {
        "s": SimpleRegistrationStrategy(),
        "w": SimpleRegistrationStrategy(),
        "m": MVRegistrationStrategy(),
        "f24": F24RegistrationStrategy(),
        "f26": F26RegistrationStrategy(),
        "f": FRegistrationStrategy(),
    }

    return mapping.get(event.registration_form, SimpleRegistrationStrategy())
