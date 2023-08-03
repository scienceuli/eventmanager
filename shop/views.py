from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.template.loader import get_template

from django.utils import timezone

from xhtml2pdf import pisa

from events.models import Event, EventCollection
from events.forms import EventMemberForm
from events.views import handle_form_submission

from shop.cart import Cart
from shop.forms import CartAddEventForm
from shop.models import Order, OrderItem
from shop.tasks import order_created

from payment.utils import render_to_pdf


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
        {
            "payment_cart": split_cart(cart)[0],
            "non_payment_cart": split_cart(cart)[1],
            "total_price": cart.get_total_price(),
            "discounted_total_price": cart.get_discounted_total_price(),
        },
    )


def order_create(request):
    cart = Cart(request)

    payment_cart = split_cart(cart)[0]

    show_costs_string = "Kosten"

    order_summary_html_string = "<br>".join(
        [f"{item['event'].name}" for item in payment_cart]
    )

    order_price_html_string = "<br>".join(
        [f"{item['event'].name} - {item['premium_price']} €*" for item in payment_cart]
    )

    order_discounted_price_html_string = "<br>".join(
        [f"{item['event'].name} - {item['price']} €" for item in payment_cart]
    )

    order_totalprice_html_string = (
        f"<span class='font-semibold'>Gesamtpreis: {cart.get_total_price()} €</span>"
    )
    order_totalprice_html_string += "<br><span class='italic'>*Voller Preis für Nichtmitglieder. VFLL-Mitglied? Dann bitte entsprechendes Feld anklicken.</span>"

    order_discounted_totalprice_html_string = f"<span class='font-semibold'>reduzierter Gesamtpreis*: {cart.get_discounted_total_price()} €</span>"

    non_payment_cart = split_cart(cart)[1]
    waiting_list_string = "<br>".join(
        [f"{item['event'].name}" for item in non_payment_cart]
    )

    if request.method == "POST":
        form = EventMemberForm(request.POST)
        if form.is_valid():
            order_saved = False
            # Orders are created if there is something to pay
            if len(split_cart(cart)[0]) > 0:
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
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                )
                vfll = form.cleaned_data["vfll"]
                order.discounted = vfll

                # only cart items where payment is possible belong to order

                order.save()
                order_saved = True
                for item in split_cart(cart)[0]:
                    OrderItem.objects.create(
                        order=order,
                        event=item["event"],
                        price=item["price"],
                        premium_price=item["premium_price"],
                        quantity=item["quantity"],
                        is_action_price=item["action_price"],
                    )

            # create EventMemberInstances for ALL cart items

            for item in cart:
                new_member = handle_form_submission(request, form, item["event"])
                # academic = form.cleaned_data["academic"]
                # firstname = form.cleaned_data["firstname"]
                # lastname = form.cleaned_data["lastname"]

                # address_line = form.cleaned_data["address_line"]
                # company = form.cleaned_data["company"]
                # street = form.cleaned_data["street"]
                # city = form.cleaned_data["city"]
                # state = form.cleaned_data["state"]
                # postcode = form.cleaned_data["postcode"]

                # email = form.cleaned_data["email"]
                # phone = form.cleaned_data["phone"]
                # message = form.cleaned_data["message"]
                # vfll = form.cleaned_data["vfll"]
                # memberships = form.cleaned_data["memberships"]
                # memberships_labels = form.selected_memberships_labels()
                # attention = form.cleaned_data["attention"]
                # attention_other = form.cleaned_data["attention_other"]
                # education_bonus = form.cleaned_data["education_bonus"]
                # free_text_field = form.cleaned_data["free_text_field"]
                # check = form.cleaned_data["check"]
                # if item["event"].is_full():
                #     attend_status = "waiting"
                # else:
                #     attend_status = "registered"

                # # make name of this registration from event label and date

                # name = f"{item['event'].label} | {timezone.now()}"

                # new_member = EventMember.objects.create(
                #     name=name,
                #     event=item["event"],
                #     academic=academic,
                #     firstname=firstname,
                #     lastname=lastname,
                #     company=company,
                #     street=street,
                #     address_line=address_line,
                #     city=city,
                #     postcode=postcode,
                #     state=state,
                #     email=email,
                #     phone=phone,
                #     message=message,
                #     vfll=vfll,
                #     memberships=memberships,
                #     attention=attention,
                #     attention_other=attention_other,
                #     education_bonus=education_bonus,
                #     free_text_field=free_text_field,
                #     check=check,
                #     attend_status=attend_status,
                # )

            # clear the cart
            cart.clear()

            if payment_cart:
                message = f"Vielen Dank für deine Bestellung/Anmeldung. Die Bestellnummer ist {order.get_order_number}."
            elif non_payment_cart:
                message = f"Vielen Dank für deine Anmeldung."
            else:
                message = f"Du hast noch keine Anmeldung vorgenommen."

            messages.success(request, message)

            # send email to user if order was created
            if order_saved:
                order_created.delay(order.id)

                # set the order in the session
                request.session["order_id"] = order.id

                # redirect for payment
                return redirect(reverse("payment:payment-process"))
            else:
                return redirect(reverse("event-filter"))

            # return redirect("event-list")
            # return render(request,
            #               'shop/order_created.html',
            #               {'order': order})
    else:
        form = EventMemberForm(initial={"country": "DE"})

    return render(
        request,
        "events/add_event_member_tw.html",
        {
            "cart": cart,
            "form": form,
            "show_costs_string": show_costs_string,
            "order_summary_html_string": order_summary_html_string,
            "order_price_html_string": order_price_html_string,
            "order_discounted_price_html_string": order_discounted_price_html_string,
            "order_totalprice_html_string": order_totalprice_html_string,
            "order_discounted_totalprice_html_string": order_discounted_totalprice_html_string,
            "waiting_list_string": waiting_list_string,
        },
    )


@staff_member_required
def admin_order_pdf(request, order_id):
    context = {}
    order = get_object_or_404(Order, id=order_id)
    template_path = "shop/pdf_invoice.html"
    context["order"] = order
    # if order.discounted:
    #     ust_footnote_counter = "2"
    # else:
    #     ust_footnote_counter = "1"
    # context["ust_footnote_counter"] = ust_footnote_counter
    response = render_to_pdf(template_path, context)

    # to directly download the pdf we need attachment
    # response['Content-Disposition'] = 'attachment; filename="report.pdf"'

    # to view on browser we can remove attachment
    filename = "rechnung_%s" % (order.get_order_number)

    response["Content-Disposition"] = f'filename="{filename}.pdf"'

    return response


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "admin/shop/orders/detail.html", {"order": order})
