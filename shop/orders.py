from django.conf import settings
from django.contrib import messages
from shop.models import Order, OrderItem
from invoices.models import Invoice

from events.utils import no_duplicate_check

from invoices.utils import get_invoice_date


def create_order(form, email):
    order = Order(
        academic=form.cleaned_data["academic"],
        firstname=form.cleaned_data["firstname"],
        lastname=form.cleaned_data["lastname"],
        address_line=form.cleaned_data["address_line"],
        company=form.cleaned_data["company"],
        street=form.cleaned_data["street"],
        city=form.cleaned_data["city"],
        state=form.cleaned_data["state"],
        postcode=form.cleaned_data["postcode"],
        email=email,
        phone=form.cleaned_data["phone"],
    )
    vfll = form.cleaned_data["vfll"]
    memberships = form.cleaned_data["memberships"]
    # print("vfll:", vfll)
    # print("ms:", memberships, len(memberships), vfll or (len(memberships) > 0))
    order.discounted = vfll or (len(memberships) > 0)

    # only cart items where payment is possible belong to order

    order.save()
    return order

def create_order_item(order, item, email):
    duplicate_list = []  # list of events with already existing registration
    order_item_counter = 0

    event = item["event"]
    if no_duplicate_check(email, event):
        order_item =OrderItem.objects.create(
            order=order,
            event=event,
            price=item["price"],
            premium_price=item["premium_price"],
            quantity=item["quantity"],
            is_action_price=item["action_price"],
        )
        order_item_counter += 1
    else:
        duplicate_list.append(event.name)

    duplicate_string = ", ".join(duplicate_list)

    return order_item_counter, duplicate_list,duplicate_string, order_item

def create_invoice(order):
    invoice_name = f"Rechnung {order.lastname}, {order.firstname} ({', '.join([ev.label for ev in order.get_registered_items_events()])})"

    new_invoice_message = None
    new_invoice = Invoice.objects.create(
        order=order,
        invoice_number=order.get_order_number,
        invoice_date=get_invoice_date(order),
        invoice_type="i",
        name=invoice_name,
        amount=order.get_total_cost(),
    )
    if new_invoice:
        new_invoice_message = new_invoice.create_invoice_message()

    return new_invoice_message, new_invoice

def create_message(request, order, order_item_counter, duplicate_list, payment_cart, non_payment_cart):
    if settings.PAYPAL_ENABLED:

        if payment_cart and order_item_counter > 0 and len(duplicate_list) == 0:

            message = f"Vielen Dank für Ihre Bestellung/Anmeldung. Die Bestellnummer ist {order.get_order_number}. Bitte wählen Sie im nächsten Schritt Ihre bevorzugte Zahlungsmethode (PayPal oder Rechnung) aus."
            level = messages.SUCCESS
        elif payment_cart and order_item_counter > 0 and len(duplicate_list) > 0:
            message = f"Vielen Dank für Ihre Bestellung/Anmeldung. Für folgende Veranstaltungen waren Sie bereits angemeldet: {duplicate_string}. Diese werden aus Ihrer Bestellung entfernt. Für die anderen ist die Bestellnummer {order.get_order_number}. en Sie im nächsten Schritt Ihre bevorzugte Zahlungsmethode (PayPal oder Rechnung) aus."
            level = messages.SUCCESS
        elif payment_cart and order_item_counter == 0:
            message = f"Für alle von Ihnen ausgewählten Veranstaltungen sind sie bereits angemeldet. Ihre Bestellung wird daher verworfen."
            level = messages.ERROR
        elif non_payment_cart:
            message = f"Vielen Dank für Ihre Anmeldung."
            level = messages.SUCCESS
        else:
            message = f"Sie haben noch keine Anmeldung vorgenommen."
            level = messages.INFO

        messages.add_message(request, level, message, fail_silently=True)

