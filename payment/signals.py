from django.dispatch import receiver

from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received

import logging

from django.conf import settings

from shop.models import Order
from payment.tasks import payment_completed


logger = logging.getLogger(__name__)


@receiver(valid_ipn_received)
def paypal_payment_received(sender, **kwargs):
    ipn_obj = sender
    if ipn_obj.payment_status == ST_PP_COMPLETED:
        # WARNING !
        # Check that the receiver email is the same we previously
        # set on the `business` field. (The user could tamper with
        # that fields on the payment form before it goes to PayPal)
        if ipn_obj.receiver_email != settings.PAYPAL_RECEIVER_EMAIL:
            # Not a valid payment
            return

        # ALSO: for the same reason, you need to check the amount
        # received, `custom` etc. are all what you expect or what
        # is allowed.
        try:
            order_uuid = ipn_obj.invoice
            order = Order.objects.get(uuid=order_uuid)
            assert (
                ipn_obj.mc_gross == order.get_total_cost()
                and ipn_obj.mc_currency == "EUR"
            )
        except Exception:
            logger.exception("Paypal ipn_obj data not valid!")
        else:
            order.paid = True
            order.payment_date = ipn_obj.payment_date
            order.payment_type = "p"
            order.save()
            payment_completed(order.id)
            # payment_completed.delay(order.id)
    else:
        logger.debug("Paypal payment status not completed: %s" % ipn_obj.payment_status)
