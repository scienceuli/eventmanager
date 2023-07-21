from django.apps import AppConfig


class PaymentConfig(AppConfig):
    name = 'payment'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        import payment.signals
