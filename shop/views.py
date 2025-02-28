import locale
from typing import Any
import pytz
from datetime import datetime


from django import http

locale.setlocale(locale.LC_ALL, "de_DE")

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.template.loader import get_template
from django.views.generic.edit import CreateView, FormView

from django.core.mail import send_mail

from django.utils import timezone

from xhtml2pdf import pisa

from events.models import Event, EventCollection
from events.forms import EventMemberForm
from events.views import handle_form_submission
from events.utils import no_duplicate_check, send_email

from shop.cart import Cart
from shop.forms import CartAddEventForm
from shop.models import Order, OrderItem
from shop.tasks import order_created

from utilities.pdf import render_to_pdf

from payment.utils import (
    update_order,
    check_order_complete,
)
from payment.tasks import payment_completed

from invoices.models import Invoice
from invoices.utils import get_invoice_date
from mailings.models import InvoiceMessage


def split_cart(cart):
    payment, non_payment = [], []
    for item in cart:
        (non_payment, payment)[not item["event"].is_full()].append(item)
    return payment, non_payment


@require_POST
def cart_add(request, event_id):
    cart = Cart(request)
    event = get_object_or_404(Event, id=event_id)
    form = CartAddEventForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        cart.add(event=event, quantity=cd["quantity"], override_quantity=cd["override"])

    return redirect("shop:cart-detail")


def cart_add_collection(request, event_collection_id):
    cart = Cart(request)
    event_collection = get_object_or_404(EventCollection, id=event_collection_id)

    for event in event_collection.events.all():
        cart.add(event=event, quantity=1, override_quantity=True)

    return redirect("shop:cart-detail")


@require_POST
def cart_remove(request, event_id):
    cart = Cart(request)
    event = get_object_or_404(Event, id=event_id)
    cart.remove(event)

    return redirect("shop:cart-detail")


def cart_detail(request):
    cart = Cart(request)

    return render(
        request,
        "shop/cart_detail.html",
        # "shop/test.html",
        {
            "payment_cart": split_cart(cart)[0],
            "non_payment_cart": split_cart(cart)[1],
            "total_price": cart.get_total_price(),
            "discounted_total_price": cart.get_discounted_total_price(),
        },
    )


class OrderCreateView(FormView):
    model = Order
    template_name = "events/add_event_member_tw.html"
    form_class = EventMemberForm

    def dispatch(self, request, *args, **kwargs):
        self.cart = Cart(request)

        self.payment_cart = split_cart(self.cart)[0]
        self.non_payment_cart = split_cart(self.cart)[1]

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(OrderCreateView, self).get_initial()
        initial.update({"country": "DE"})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.cart
        payment_cart = self.payment_cart
        non_payment_cart = self.non_payment_cart

        if payment_cart:
            show_costs = True
        else:
            show_costs = False

        payment_button_text = ""
        show_costs_string = "Kosten"

        order_summary_html_string = "<br>".join(
            [f"{item['event'].name}" for item in payment_cart]
        )

        order_price_html_string = "<br>".join(
            [
                f"{item['event'].name} – {locale.currency(item['premium_price'], grouping=False, symbol=False)} €*"
                for item in payment_cart
            ]
        )

        order_discounted_price_html_string = "<br>".join(
            [
                f"{item['event'].name} – {locale.currency(item['price'], grouping=False, symbol=False)} €"
                for item in payment_cart
            ]
        )

        order_totalprice_html_string = f"<span class='font-semibold'>Gesamtpreis: {locale.currency(cart.get_total_price(), grouping=False,symbol=False)} €</span>"
        order_totalprice_html_string += "<br><span class='italic'>*Preis für Nichtmitglieder. VFLL-Mitglied? Dann bitte entsprechendes Feld anklicken.</span>"

        order_discounted_totalprice_html_string = f"<span class='font-semibold'>Gesamtpreis: {locale.currency(cart.get_discounted_total_price(), grouping=False, symbol=False)} €</span>"

        order_summary_html_string += "<br>".join(
            [f"{item['event'].name} (Warteliste)" for item in non_payment_cart]
        )

        waiting_list_string = "<br>".join(
            [f"{item['event'].name}" for item in non_payment_cart]
        )

        # generate text of registration/pay button
        if payment_cart:
            payment_button_text = settings.PAY_NOW_TEXT
        elif non_payment_cart:
            payment_button_text = settings.REGISTER_NOW_TEXT_WAITING

        context_update = {
            "cart": cart,
            "show_costs_string": show_costs_string,
            "show_costs": show_costs,
            "order_summary_html_string": order_summary_html_string,
            "order_price_html_string": order_price_html_string,
            "order_discounted_price_html_string": order_discounted_price_html_string,
            "order_totalprice_html_string": order_totalprice_html_string,
            "order_discounted_totalprice_html_string": order_discounted_totalprice_html_string,
            "waiting_list_string": waiting_list_string,
            "payment_button_text": payment_button_text,
        }
        self.cart = cart
        self.payment_cart = payment_cart
        self.non_payment_cart = non_payment_cart

        context.update(context_update)
        return context

    def form_valid(self, form):
        payment_cart = self.payment_cart
        non_payment_cart = self.non_payment_cart
        cart = self.cart

        order_saved = False
        self.order_saved = order_saved
        order = None

        # Orders are created if there is something to pay
        if len(split_cart(cart)[0]) > 0:
            email = form.cleaned_data.get("email")
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
            # print(order.payment_type)
            order_saved = True

            duplicate_list = []  # list of events with already existing registration
            order_item_counter = 0
            for item in split_cart(cart)[0]:
                event = item["event"]
                if no_duplicate_check(email, event):
                    OrderItem.objects.create(
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

        # create EventMemberInstances for ALL cart items

        for item in cart:
            new_member = handle_form_submission(self.request, form, item["event"])

        # creating invoice
        if order_saved:
            invoice_name = f"Rechnung {order.lastname}, {order.firstname} ({', '.join([ev.label for ev in order.get_registered_items_events()])})"

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

        # clear the cart
        cart.clear()

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

            messages.add_message(self.request, level, message, fail_silently=True)

        if order:
            if not order_item_counter == 0:
                self.order_saved = order_saved
                self.order = order
            else:
                order.delete()
                self.order_saved = False

        return super().form_valid(form)

    def get_success_url(self):
        order_saved = self.order_saved

        if order_saved:
            order = self.order
            # send email to user if order was created
            # order_created.delay(order.id)

            order_created(order.id)

            # set the order in the session
            self.request.session["order_id"] = order.id

            # redirect for payment
            return reverse_lazy("payment:payment-process")
        else:
            return reverse_lazy("event-filter")


# obsolete
# def order_create(request):
#     cart = Cart(request)
#     print("in view: ", cart.cart)

#     payment_cart = split_cart(cart)[0]

#     if payment_cart:
#         show_costs = True
#     else:
#         show_costs = False

#     payment_button_text = ""
#     show_costs_string = "Kosten"

#     order_summary_html_string = "<br>".join(
#         [f"{item['event'].name}" for item in payment_cart]
#     )

#     order_price_html_string = "<br>".join(
#         [
#             f"{item['event'].name} – {locale.currency(item['premium_price'], grouping=False, symbol=False)} €*"
#             for item in payment_cart
#         ]
#     )

#     order_discounted_price_html_string = "<br>".join(
#         [
#             f"{item['event'].name} – {locale.currency(item['price'], grouping=False, symbol=False)} €"
#             for item in payment_cart
#         ]
#     )

#     order_totalprice_html_string = f"<span class='font-semibold'>Gesamtpreis: {locale.currency(cart.get_total_price(), grouping=False,symbol=False)} €</span>"
#     order_totalprice_html_string += "<br><span class='italic'>*Preis für Nichtmitglieder. VFLL-Mitglied? Dann bitte entsprechendes Feld anklicken.</span>"

#     order_discounted_totalprice_html_string = f"<span class='font-semibold'>Gesamtpreis: {locale.currency(cart.get_discounted_total_price(), grouping=False, symbol=False)} €</span>"

#     non_payment_cart = split_cart(cart)[1]

#     order_summary_html_string += "<br>".join(
#         [f"{item['event'].name} (Warteliste)" for item in non_payment_cart]
#     )

#     waiting_list_string = "<br>".join(
#         [f"{item['event'].name}" for item in non_payment_cart]
#     )

#     # generate text of registration/pay button
#     if payment_cart:
#         payment_button_text = settings.PAY_NOW_TEXT
#     elif non_payment_cart:
#         payment_button_text = settings.REGISTER_NOW_TEXT_WAITING

#     if request.method == "POST":
#         form = EventMemberForm(request.POST)
#         if form.is_valid():
#             order_saved = False
#             # Orders are created if there is something to pay
#             if len(split_cart(cart)[0]) > 0:
#                 order = Order(
#                     academic=form.cleaned_data["academic"],
#                     firstname=form.cleaned_data["firstname"],
#                     lastname=form.cleaned_data["lastname"],
#                     address_line=form.cleaned_data["address_line"],
#                     company=form.cleaned_data["company"],
#                     street=form.cleaned_data["street"],
#                     city=form.cleaned_data["city"],
#                     state=form.cleaned_data["state"],
#                     postcode=form.cleaned_data["postcode"],
#                     email=form.cleaned_data["email"],
#                     phone=form.cleaned_data["phone"],
#                 )
#                 memberships = form.cleaned_data["memberships"]
#                 print("memberships: ", memberships)
#                 vfll = form.cleaned_data["vfll"]
#                 order.discounted = vfll or (len(memberships) > 0)

#                 # only cart items where payment is possible belong to order

#                 order.save()
#                 order_saved = True
#                 for item in split_cart(cart)[0]:
#                     OrderItem.objects.create(
#                         order=order,
#                         event=item["event"],
#                         price=item["price"],
#                         premium_price=item["premium_price"],
#                         quantity=item["quantity"],
#                         is_action_price=item["action_price"],
#                     )

#             # create EventMemberInstances for ALL cart items

#             for item in cart:
#                 new_member = handle_form_submission(request, form, item["event"])
#                 # academic = form.cleaned_data["academic"]
#                 # firstname = form.cleaned_data["firstname"]
#                 # lastname = form.cleaned_data["lastname"]

#                 # address_line = form.cleaned_data["address_line"]
#                 # company = form.cleaned_data["company"]
#                 # street = form.cleaned_data["street"]
#                 # city = form.cleaned_data["city"]
#                 # state = form.cleaned_data["state"]
#                 # postcode = form.cleaned_data["postcode"]

#                 # email = form.cleaned_data["email"]
#                 # phone = form.cleaned_data["phone"]
#                 # message = form.cleaned_data["message"]
#                 # vfll = form.cleaned_data["vfll"]
#                 # memberships = form.cleaned_data["memberships"]
#                 # memberships_labels = form.selected_memberships_labels()
#                 # attention = form.cleaned_data["attention"]
#                 # attention_other = form.cleaned_data["attention_other"]
#                 # education_bonus = form.cleaned_data["education_bonus"]
#                 # free_text_field = form.cleaned_data["free_text_field"]
#                 # check = form.cleaned_data["check"]
#                 # if item["event"].is_full():
#                 #     attend_status = "waiting"
#                 # else:
#                 #     attend_status = "registered"

#                 # # make name of this registration from event label and date

#                 # name = f"{item['event'].label} | {timezone.now()}"

#                 # new_member = EventMember.objects.create(
#                 #     name=name,
#                 #     event=item["event"],
#                 #     academic=academic,
#                 #     firstname=firstname,
#                 #     lastname=lastname,
#                 #     company=company,
#                 #     street=street,
#                 #     address_line=address_line,
#                 #     city=city,
#                 #     postcode=postcode,
#                 #     state=state,
#                 #     email=email,
#                 #     phone=phone,
#                 #     message=message,
#                 #     vfll=vfll,
#                 #     memberships=memberships,
#                 #     attention=attention,
#                 #     attention_other=attention_other,
#                 #     education_bonus=education_bonus,
#                 #     free_text_field=free_text_field,
#                 #     check=check,
#                 #     attend_status=attend_status,
#                 # )

#             # clear the cart
#             cart.clear()

#             if payment_cart:
#                 message = f"Vielen Dank für Ihre Bestellung/Anmeldung. Die Bestellnummer ist {order.get_order_number}. Bitte wähle im nächsten Schritt Deine bevorzugte Zahlungsmethode (PayPal oder Rechnung) aus."
#             elif non_payment_cart:
#                 message = f"Vielen Dank für Ihre Anmeldung."
#             else:
#                 message = f"Sie haben noch keine Anmeldung vorgenommen."

#             messages.success(request, message, fail_silently=True)

#             # send email to user if order was created
#             if order_saved:
#                 # order_created.delay(order.id)
#                 order_created(order.id)

#                 # set the order in the session
#                 request.session["order_id"] = order.id

#                 # redirect for payment
#                 return redirect(reverse("payment:payment-process"))
#             else:
#                 return redirect(reverse("event-filter"))

#             # return redirect("event-list")
#             # return render(request,
#             #               'shop/order_created.html',
#             #               {'order': order})
#     else:
#         form = EventMemberForm(initial={"country": "DE"})

#     return render(
#         request,
#         "events/add_event_member_tw.html",
#         {
#             "cart": cart,
#             "form": form,
#             "show_costs_string": show_costs_string,
#             "show_costs": show_costs,
#             "order_summary_html_string": order_summary_html_string,
#             "order_price_html_string": order_price_html_string,
#             "order_discounted_price_html_string": order_discounted_price_html_string,
#             "order_totalprice_html_string": order_totalprice_html_string,
#             "order_discounted_totalprice_html_string": order_discounted_totalprice_html_string,
#             "waiting_list_string": waiting_list_string,
#             "payment_button_text": payment_button_text,
#         },
#     )


@staff_member_required
def admin_order_pdf(request, order_id, process):
    context = {}
    order = get_object_or_404(Order, id=order_id)
    template_path = "shop/pdf_invoice.html"

    # if check_update_order(request, order):
    #     update_order(order)

    context["order"] = order
    context["process"] = process
    if process == "storno":
        context["label"] = "Storno-Rechnung"
        context["invoice_date"] = datetime.now()
    elif process == "order":
        context["label"] = "Rechnung"
        if order.payment_date:
            invoice_date = order.payment_date
        else:
            invoice_date = order.date_created
        context["invoice_date"] = invoice_date

    if process == "order":
        context["order_items"] = OrderItem.objects.filter(order=order, status="r")
    elif process == "storno":
        context["order_items"] = OrderItem.objects.filter(order=order, status="c")
    context["contains_action_price"] = any(
        [
            item.is_action_price
            for item in OrderItem.objects.filter(order=order, status="r")
        ]
    )
    # if order.discounted:
    #     ust_footnote_counter = "2"
    # else:
    #     ust_footnote_counter = "1"
    # context["ust_footnote_counter"] = ust_footnote_counter
    response = render_to_pdf(template_path, context)

    # to directly download the pdf we need attachment
    # response['Content-Disposition'] = 'attachment; filename="report.pdf"'

    # to view on browser we can remove attachment
    filename = f"{process}_rechnung_{order.get_order_number}"

    response["Content-Disposition"] = f'filename="{filename}.pdf"'

    return response


@staff_member_required
def admin_order_pdf_and_mail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # set payment type to invoice
    order.payment_type = "r"
    order.save()
    # call payment_completed
    response = payment_completed(order_id)
    # Redirect explicitly to the admin list view
    list_view_url = reverse(
        "admin:%s_%s_changelist" % (order._meta.app_label, order._meta.model_name)
    )
    return HttpResponseRedirect(list_view_url)


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "admin/shop/orders/detail.html", {"order": order})


@staff_member_required
def invoice_report(request):
    orders = Order.objects.all()
    return render(request, "admin/shop/orders/list.html", {"orders": orders})


@staff_member_required
def reminder_mail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    template_name = "reminder"

    order_complete = check_order_complete(order)

    if order.paid:
        messages.error(request, f"Rechnung wurde bereits bezahlt")
    elif not order_complete:
        messages.error(
            request, f"Bitte erst die Rechnung vervollständigen (Name, Email)"
        )
    else:
        addresses_list = [order.email]
        addresses = {"to": addresses_list}
        subject = f"Mahnung Rechnung {order.get_order_number}"
        formatting_dict = {
            "firstname": order.firstname,
            "lastname": order.lastname,
            "order_number": order.get_order_number,
            "payment_date": order.payment_date.date().strftime("%d.%m.%Y"),
            "events": ", ".join(
                [event.name for event in order.get_registered_items_events()]
            ),
            "total_costs": order.get_total_cost(),
        }

        send_reminder_mail = send_email(
            addresses,
            subject,
            settings.DEFAULT_FROM_EMAIL,
            [settings.REPLY_TO_EMAIL],
            template_name,
            formatting_dict=formatting_dict,
        )

        if send_reminder_mail:
            messages.success(request, f"Mahnung wurde verschickt")
            order.reminder_sent_date = timezone.now()

    list_view_url = reverse(
        "admin:%s_%s_changelist" % (order._meta.app_label, order._meta.model_name)
    )
    return HttpResponseRedirect(list_view_url)
