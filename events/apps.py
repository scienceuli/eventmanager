from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "events"
    verbose_name = "Veranstaltung"
    verbose_name_plural = "Veranstaltungen"

    def ready(self):
        from . import signals
