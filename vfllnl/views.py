import logging
import re
import time
import traceback

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives, get_connection
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from honeypot.decorators import check_honeypot, honeypot_exempt

from .constants import (
    SEPARATOR,
    SUBSCRIBE_STATUS_CONFIRMED,
    SUBSCRIBE_STATUS_SUBSCRIBED,
)
from .email_utility import send_subscription_email
from .encrypt_utils import decrypt, encrypt
from .forms import EmailTemplateForm
from .models import EmailTemplate, NewsletterSubscription
from .templatetags.vfllnl_tags import FORM_TOKEN_SALT
from .utils import save_email, validate_email


UNSUBSCRIBE_SALT = "vfllnl.unsubscribe"


def make_unsubscribe_token(email):
    return signing.dumps(email, salt=UNSUBSCRIBE_SALT)


def add_html_footer(html, footer):
    """Insert footer before </body>, or append it if there is no body tag."""
    index = html.lower().rfind("</body>")
    if index == -1:
        return html + footer
    return html[:index] + footer + html[index:]


@csrf_exempt  # one-click unsubscribe (RFC 8058) is POSTed by mail clients
@honeypot_exempt
def unsubscribe(request, token):
    try:
        email = signing.loads(token, salt=UNSUBSCRIBE_SALT)
    except signing.BadSignature:
        messages.error(request, "Ungültiger Abmeldelink.")
        return redirect("home")

    # GET only shows a confirmation page: mail scanners follow links and
    # would otherwise unsubscribe people unintentionally
    if request.method != "POST":
        return render(request, "vfllnl/unsubscribe.html", {"email": email})

    NewsletterSubscription.objects.filter(email=email).delete()
    messages.success(request, "Du hast dich vom Newsletter abgemeldet.")
    return redirect("home")


FORM_MIN_SECONDS = 3  # humans need longer than this to type an email address
FORM_MAX_AGE = 60 * 60 * 24


def is_bot_submission(post_data):
    """Return a reason string if the signup looks automated, else None."""
    if post_data.get("website"):
        return "bait field filled"
    try:
        rendered_at = signing.loads(
            post_data.get("form_token", ""), salt=FORM_TOKEN_SALT, max_age=FORM_MAX_AGE
        )
    except signing.SignatureExpired:
        return "form token expired"
    except signing.BadSignature:
        return "form token missing or invalid"
    if time.time() - rendered_at < FORM_MIN_SECONDS:
        return "submitted too fast"
    return None


@check_honeypot(field_name="secret_key_for_vfll")
def subscribe(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        email = post_data.get("email", None)

        bot_reason = is_bot_submission(post_data)
        if bot_reason:
            logging.getLogger("warning").warning(
                "Rejected newsletter signup for %s: %s", email, bot_reason
            )
            # pretend success so bots get no feedback
            messages.success(
                request,
                "Eine E-Mail wurde gesendet. Bitte bestätige deine Anmeldung "
                "durch Klicken des Links in der E-Mail.",
            )
            return HttpResponseRedirect(reverse("vfllnl:subscribe"))

        error_msg = validate_email(email)
        if error_msg:
            messages.error(request, error_msg)
            return HttpResponseRedirect(reverse("vfllnl:subscribe"))

        save_status = save_email(email)

        if save_status:
            token = encrypt(email + SEPARATOR + str(time.time()))
            subscription_confirmation_url = (
                request.build_absolute_uri(reverse("vfllnl:subscription_confirmation"))
                + "?token="
                + token
            )
            status = send_subscription_email(email, subscription_confirmation_url)
            if not status:
                NewsletterSubscription.objects.get(email=email).delete()
                logging.getLogger("info").info(
                    "Deleted the record from Subscribe table for "
                    + email
                    + " as email sending failed. status: "
                    + str(status)
                )
            else:
                msg = (
                    "Eine E-Mail wurde an '"
                    + email
                    + "' gesendet. Bitte bestätige deine Anmeldung durch "
                    "Klicken des Links in der E-Mail. "
                    "Bitte überprüfe ggf. auch deinen Spam-Ordner."
                )
                messages.success(request, msg)
        else:
            msg = "Es trat ein Fehler auf. Wir kümmern ums drum."
            messages.error(request, msg)

        return HttpResponseRedirect(reverse("vfllnl:subscribe"))

    return redirect("home")


def subscription_confirmation(request):
    if request.method == "POST":
        raise Http404

    token = request.GET.get("token", None)
    print("token: ", token)

    if not token:
        logging.getLogger("warning").warning("Invalid Link ")
        messages.error(request, "Invalid Link")
        return HttpResponseRedirect(reverse("vfllnl:subscribe"))

    token = decrypt(token)
    if token:
        token = token.split(SEPARATOR)
        email = token[0]
        print(email)
        initiate_time = float(token[1])  # time when email was sent, in epoch format
        if time.time() - initiate_time > settings.NEWSLETTER_CONFIRMATION_DAYS * 86400:
            messages.error(
                request,
                "Der Bestätigungslink ist abgelaufen. Bitte melde dich erneut an.",
            )
            return HttpResponseRedirect(reverse("vfllnl:subscribe"))
        try:
            subscribe_model_instance = NewsletterSubscription.objects.get(email=email)
            subscribe_model_instance.status = SUBSCRIBE_STATUS_CONFIRMED
            subscribe_model_instance.save()
            messages.success(
                request,
                "Deine Anmeldung zum VFLL-Newsletter wurde bestätigt. Vielen Dank.",
            )
        except ObjectDoesNotExist as e:
            logging.getLogger("warning").warning(traceback.format_exc())
            messages.error(request, "Ungültiger Link")
    else:
        logging.getLogger("warning").warning("Invalid token ")
        messages.error(request, "Ungültiger Link")

    return HttpResponseRedirect(reverse("vfllnl:subscribe"))


# def validate_email(request):
#     email = request.POST.get("email", None)
#     if email is None:
#         res = JsonResponse({"msg": "E-Mail-Adresse ist notwendig."})
#     elif NewsletterSubscription.objects.get(email=email):
#         res = JsonResponse({"msg": "Diese E-Mail-Adresse ist bereits registriert."})
#     elif not re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", email):
#         res = JsonResponse({"msg": "Ungültige E-Mail-Adresse"})
#     else:
#         res = JsonResponse({"msg": ""})
#     return res


@login_required
def create_newsletter(request):
    context = {}
    form = EmailTemplateForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.instance.created_by = request.user
            form.save()
            return redirect("vfllnl:newsletter-list")

    context["form"] = form
    return render(request, "vfllnl/edit_newsletter.html", context)


@login_required
def newsletter_list(request):
    newsletters = EmailTemplate.objects.all()
    context = {"newsletters": newsletters}
    return render(request, "vfllnl/newsletter_list.html", context)


@login_required
def send_newsletter(request, pk):
    obj = EmailTemplate.objects.get(pk=pk)
    obj = get_object_or_404(EmailTemplate, pk=pk)

    subject = obj.subject
    print("obj body:", obj.body)

    if obj.use_mjml and not obj.sent_at:
        html_message = render_to_string(
            "vfllnl/email_template.html",
            {
                "body": obj.body,
            },
        )
    else:
        html_message = obj.body

    plain_message = strip_tags(html_message)

    # no explicit selection means all subscribers; only confirmed ones get mail
    subscribers = (
        obj.recipients.all()
        if obj.recipients.exists()
        else NewsletterSubscription.objects.all()
    )
    recipients = [
        subscriber.email
        for subscriber in subscribers.filter(status=SUBSCRIBE_STATUS_CONFIRMED)
    ]
    from_email = settings.NEWSLETTER_EMAIL_FROM

    # one mail per recipient so subscribers don't see each other's addresses
    # and every mail can carry a personal unsubscribe link
    mails = []
    for recipient in recipients:
        unsubscribe_url = request.build_absolute_uri(
            reverse("vfllnl:unsubscribe", args=[make_unsubscribe_token(recipient)])
        )
        footer = render_to_string(
            "vfllnl/emails/unsubscribe_footer.html",
            {"unsubscribe_url": unsubscribe_url},
        )
        mail = EmailMultiAlternatives(
            subject,
            plain_message + "\n\n" + strip_tags(footer).strip(),
            from_email,
            [recipient],
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        mail.attach_alternative(add_html_footer(html_message, footer), "text/html")
        mails.append(mail)
    get_connection(fail_silently=False).send_messages(mails)

    obj.sent_at = obj.created_at
    obj.save()

    return redirect("vfllnl:newsletter-list")


ALL_RECIPIENTS_ID = "__all__"


@login_required
def edit_newsletter(request, pk):
    obj = EmailTemplate.objects.get(pk=pk)

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=obj)
        if form.is_valid():
            nl_instance = form.save(commit=False)
            nl_instance.save()
            recipients = form.cleaned_data["recipients"]

            nl_instance.recipients.set(recipients)

            return redirect("vfllnl:newsletter-list")
    else:
        form = EmailTemplateForm(instance=obj)

    context = {"obj": obj, "form": form}
    return render(request, "vfllnl/edit_newsletter.html", context)


@login_required
def copy_newsletter(request, pk):
    original = get_object_or_404(EmailTemplate, pk=pk)

    if original:
        new_template = EmailTemplate.objects.get(pk=pk)
        new_template.pk = None
        new_template.subject += " (Koipe)"
        new_template.title += " (Koipe)"
        new_template.created_by = request.user
        new_template.sent_at = None
        new_template.save()

        messages.success(request, "Newsletter wurde kopiert.")

        return redirect("vfllnl:edit-newsletter", pk=new_template.pk)

    messages.error(request, "Newsletter konnte nicht kopiert werden.")

    return redirect("vfllnl:newsletter-list")


@login_required
def delete_newsletter(request, pk):
    obj = get_object_or_404(EmailTemplate, pk=pk)

    obj.status = "c"
    obj.save()

    newsletters = (
        EmailTemplate.objects.filter(status="a").order_by("created_at").reverse()
    )
    return render(
        request, "vfllnl/_newsletter_table.html", {"newsletters": newsletters}
    )


@login_required
def preview_newsletter(request, pk):
    template = get_object_or_404(EmailTemplate, pk=pk)

    if template.use_mjml:
        html = render_to_string(
            "vfllnl/email_template.html",
            {
                "body": template.body,
            },
        )
    else:
        html = template.body  # fallback if not using MJML

    return HttpResponse(html)
