from dataclasses import dataclass, field
from django.conf import settings
from django.db import transaction

from events.services.registration import EventRegistrationService
from events.services.notification_service import NotificationService
from events.services.strategies import get_strategy

from shop.services.order_service import OrderService
from shop.cart import split_cart

@dataclass
class CheckoutResult:
    success: bool = False
    has_error: bool = False
    successes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class CheckoutService:

    def __init__(self, form, cart):
        self.form = form
        self.cart = cart
        self.email = form.cleaned_data.get("email")

        self.registration_service = EventRegistrationService()
        self.order_service = OrderService(form, self.email)
        self.notification_service = NotificationService()

    def _process_item(self, item, result):
        """Register member and send notifications. Returns reg_result."""
        event = item["event"]

        reg_result = self.registration_service.register(
            self.form, event
        )

        # collect messages
        result.successes.extend(reg_result.successes)
        result.errors.extend(reg_result.errors)

        if reg_result.success:
            result.success = True
            strategy = get_strategy(event)
            self.notification_service.send_notification_emails(
                event,
                self.form,
                reg_result.member,
                strategy,
            )

        if reg_result.errors:
            result.has_error = True

        return reg_result

    def execute(self) -> CheckoutResult:
        result = CheckoutResult()

        paid_items, free_items, waiting_items = split_cart(self.cart)

        try:
            with transaction.atomic():

                for item in paid_items + free_items + waiting_items:
                    reg_result = self._process_item(item, result)

                    # add to order only if paid (price > 0, not full)
                    if item in paid_items and reg_result.success:
                        if getattr(settings, 'ONE_ORDER_ONE_INVOICE', False):
                            # each paid item gets its own order + invoice
                            item_order_service = OrderService(self.form, self.email)
                            item_order_service.add_item(item)
                            item_order_service.finalize()
                        else:
                            self.order_service.add_item(item)

                if not getattr(settings, 'ONE_ORDER_ONE_INVOICE', False) and paid_items:
                    # single order for all paid items
                    self.order_service.finalize()

                # clear cart
                self.cart.clear()

        except Exception:
            result.has_error = True
            result.errors.append(
                "Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut."
            )

        return result
