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


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)

    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type="application/pdf")
    pdf_status = pisa.CreatePDF(html, dest=response)

    if pdf_status.err:
        return HttpResponse("Es gab Probleme mit <pre>" + html + "</pre>")

    return response


def render_to_pdf_directly(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    # with open("html_out.html", "w") as out:
    #    out.write(html)
    # result = StringIO()
    result = BytesIO()
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("utf-8")),
        result,
        encoding="utf-8",
        # link_callback=link_callback,
    )
    if not pdf.err:
        return result.getvalue()
        # return HttpResponse(result.getvalue(), content_type="application/pdf")
        # return pdf
    else:
        return HttpResponse("Errors")


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


def update_order(order):
    # only update if payment_date in the future
    if order.payment_date > datetime.now().astimezone(pytz.timezone("UTC")):
        for item in order.items.all():
            try:
                event_member = EventMember.objects.get(
                    event=item.event, email=order.email
                )
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
            item.premium_price = event_prices_dict[item.event.id]["premium_price"]
            item.is_action_price = event_prices_dict[item.event.id]["action_price"]
            item.save()
