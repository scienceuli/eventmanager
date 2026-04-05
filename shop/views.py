import locale
from typing import Any
import pytz
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


from django import http

locale.setlocale(locale.LC_ALL, "de_DE")

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.template.loader import get_template
from django.views.generic.edit import CreateView, FormView
from django.views.generic import TemplateView

from django.core.mail import send_mail

from django.utils import timezone

from xhtml2pdf import pisa

from events.models import Event, EventCollection
from events.forms import EventMemberForm
from events.utils.email_utils import send_email
from events.core_models import SiteSettings


from shop.cart import Cart, split_cart
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
from mailings.models import InvoiceMessage
from events.core_models import SiteSettings

from shop.services.checkout_service import CheckoutService
from events.utils.messages_utils import add_success, add_error


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

    def add_success(self, message):
        if message:
            messages.success(self.request, message)

    def add_error(self, message):
        if message:
            messages.error(self.request, message)

    def handle_blacklist(self):
        site_settings = SiteSettings.load()
        messages.error(self.request, site_settings.blacklist_message)
        self.cart.clear()
        return redirect("shop:order-result", status="blacklist")

    def apply_result_messages(self, result):
        """Apply successes and errors from RegistrationResult to Django messages."""
        for msg in result.successes:
            messages_utils.add_success(self.request, msg)
        for msg in result.errors:
            messages_utils.add_error(self.request, msg)

    def finalize_response(self, has_success, has_error):
        if has_error and has_success:
            status = "partial"
        elif has_error:
            status = "error"
        else:
            status = "ready"

        return redirect("shop:order-result", status=status)

    def form_valid(self, form):
        checkout = CheckoutService(form, self.cart)
        result = checkout.execute()

        # apply messages
        for msg in result.successes:
            add_success(self.request, msg)

        for msg in result.errors:
            add_error(self.request, msg)

        return self.finalize_response(result.success, result.has_error)

    # def form_valid(self, form):
    #     email = form.cleaned_data.get("email")
    #     registration_service = EventRegistrationService()

    #     has_error = False
    #     has_success = False
    #     order_created = None
    #     collected_success = []
    #     collected_errors = []

    #     # Process all cart items
    #     paid_items, free_items = split_cart(self.cart)

    #     try:
    #         with transaction.atomic():
    #             for item in paid_items + free_items:
    #                 event = item["event"]

    #                 # 1a. Register member for the event
    #                 result = registration_service.register(form, event)
    #                 order_service = OrderService(form, email)

    #                 if result.success:
    #                     has_success = True
    #                     collected_success.extend(result.successes)
    #                 if result.errors:
    #                     has_error = True
    #                     collected_errors.extend(result.errors)
    #                 # If event is paid, create order + invoice
    #                 if not event.direct_payment or item not in paid_items:
    #                     continue  # skip free events

    #                 if item in paid_items and result.success:
    #                     # Create order if not yet created
    #                     order_service.add_item(item)

    #             # finalize
    #             order_service.finalize()

    #             # Clear cart
    #             self.cart.clear()
    #     except Exception as e:
    #         # rollback happens automatically
    #         has_error = True

    #         # optional: log the error

    #         _logger.exception("Order processing failed")
    #         collected_errors.extend("Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.")

    #     # error and success messages
    #     for msg in collected_success:
    #         self.add_success(msg)

    #     for msg in collected_errors:
    #         self.add_error(msg)

    #     # Redirect to result page based on collected outcome
    #     return self.finalize_response(has_success, has_error)

    def get_success_url(self):
        return reverse("shop:order-result", kwargs={"status": "ready"})

class OrderResultView(TemplateView):
    template_name = "shop/order_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = self.kwargs.get("status")
        return context

@staff_member_required
def admin_order_pdf(request, order_id, process):
    site_settings = SiteSettings.load()
    context = {}
    order = get_object_or_404(Order, id=order_id)
    template_path = "shop/pdf_invoice.html"

    # if check_update_order(request, order):
    #     update_order(order)

    context["order"] = order
    context["vfll_recipient_payment"] = site_settings.vfll_recipient_payment
    context["vfll_bank_account"] = site_settings.vfll_bank_account
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
