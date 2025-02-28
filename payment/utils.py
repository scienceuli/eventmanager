import os
import pytz
from decimal import Decimal
from datetime import datetime
from io import StringIO, BytesIO
import zipfile

from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import render

from django.template.loader import get_template
from xhtml2pdf import pisa

from events.models import EventMember
from shop.models import Order
from shop.cart import recalculate_action_prices


def get_local_datetime(value):
    return timezone.localtime(value, pytz.timezone("Europe/Berlin"))


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    result = finders.find(uri)
    print("result: ", result)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL  # Typically /static/
        sRoot = settings.STATIC_ROOT  # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL  # Typically /media/
        mRoot = settings.MEDIA_ROOT  # Typically /home/userX/project_static/media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        raise Exception("media URI must start with %s or %s" % (sUrl, mUrl))
    return path


def generate_zip(files):
    mem_zip = BytesIO()

    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.writestr(f[0], f[1])

    return mem_zip.getvalue()


item_status_dict = {
    "registered": "r",
    "attending": "r",
    "absent": "n",
    "waiting": "w",
    "cancelled": "s",
}


def check_order_date_in_future(order):
    # order_date = order.payment_date if order.payment_date else order.date_created
    order_date = order.date_created
    today = datetime.now().astimezone(pytz.timezone("UTC"))
    if order_date < today:
        return False
    return True


# def check_update_order(request, order):

#     if not check_order_date_in_future(order):

#         if request.method == "POST":
#             # Process the confirmation form

#             if form.is_valid() and form.cleaned_data["confirm"]:
#                 return True
#             elif form.is_valid() and not form.cleaned_data["confirm"]:
#                 return False
#         else:
#             # Show the confirmation form
#             form = UpdateOrderConfirmationForm()

#         # Render a template to ask for confirmation
#         return render(
#             request, "shop/confirm_update.html", {"form": form, "order": order}
#         )

#     else:
#         # If the order date is not in the past, proceed with the logic directly
#         # Add your "order update" logic here
#         return True  # Redirect to a success page


def update_order(order):
    # only update if payment_date in the future
    # order_date = order.payment_date if order.payment_date else order.date_created
    # order_updated = False
    # today = datetime.now().astimezone(pytz.timezone("UTC"))

    # if order_date > datetime.now().astimezone(pytz.timezone("UTC")):
    for item in order.items.all():
        try:
            event_member = EventMember.objects.get(event=item.event, email=order.email)
            # set item status to u (unbestimmt) if no dict key present
            item.status = item_status_dict.get(event_member.attend_status, "u")
            item.save()
        except:
            item.status = "u"
            item.save()

    # reload order
    updated_order = Order.objects.get(id=order.id)

    # get events belonging to order where status of item is registered
    events = updated_order.get_registered_items_events()

    # initialize dict with event ids and prices
    event_prices_dict = {}
    for event in events:
        event_prices_dict[event.id] = {
            "quantity": 0,
            "price": str(event.price),
            "premium_price": str(event.premium_price),
            "is_full": event.is_full(),
            "action_price": False,
        }

    event_prices_dict = recalculate_action_prices(event_prices_dict, events)

    for item in updated_order.items.filter(status="r"):
        item.price = event_prices_dict[item.event.id]["price"]
        if updated_order.date_created >= datetime(
            2024, 10, 21, 0, 0, 0, tzinfo=pytz.timezone("UTC")
        ):
            item.premium_price = event_prices_dict[item.event.id]["premium_price"]
        item.is_action_price = event_prices_dict[item.event.id]["action_price"]
        item.save()

    order_updated = True

    return order_updated


def check_order_complete(order):

    # all these fields must have values
    if any(
        s is None or s == "" for s in (order.email, order.firstname, order.lastname)
    ):
        return False
    return True
