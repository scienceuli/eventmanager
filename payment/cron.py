from datetime import datetime

from events.models import EventMember
from shop.models import Order
from payment.tasks import payment_completed


from payment.utils import update_order, check_order_date_in_future


def send_invoices_of_actual_day():
    date_today = datetime.now()

    qs_not_sent_invoices_of_today = (
        Order.objects.filter(payment_date__lte=date_today)
        .filter(mail_sent_date=None)
        .filter(payment_type="r")
        #     .values_list("id", flat=True)
    )

    # not_sent_invoices_of_today_list = list(qs_not_sent_invoices_of_today)

    # for order_id in not_sent_invoices_of_today_list:
    #    payment_completed(order_id)

    # check if the recipient is still registered for the events (=items) of his invoice
    not_sent_invoices_of_today_list = []
    for order in qs_not_sent_invoices_of_today:
        if check_order_date_in_future(order):
            update_order(order)
        items = order.items.filter(status="r")
        number_of_items = items.count()

        if number_of_items > 0:
            not_sent_invoices_of_today_list.append(order.id)

    for order_id in not_sent_invoices_of_today_list:
        payment_completed(order_id)
