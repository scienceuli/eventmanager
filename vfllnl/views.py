import re
import time
import logging
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import NewsletterSubscription, EmailTemplate
from .forms import EmailTemplateForm
from .utils import validate_email, save_email
from .email_utility import send_subscription_email
from .encrypt_utils import encrypt, decrypt

from .constants import (
    SUBSCRIBE_STATUS_CONFIRMED, 
    SUBSCRIBE_STATUS_SUBSCRIBED, 
    SEPARATOR
)


def unsubscribe(request, email):
    try:
        subscription = NewsletterSubscription.objects.get(email=email)
        subscription.delete()
        messages.success(request, "Du hast dich von Newsletter abgemeldet.")
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, "E-Mail nicht gefunden.")
    return redirect("home")  # Redirect to a page after unsubscribing


def subscribe(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        email = post_data.get("email", None)
        error_msg = validate_email(email)
        if error_msg:
            messages.error(request, error_msg)
            return HttpResponseRedirect(reverse('vfllnl:subscribe'))
        
        save_status = save_email(email)
        
        if save_status:
            token = encrypt(email + SEPARATOR + str(time.time()))
            subscription_confirmation_url = request.build_absolute_uri(
                reverse('vfllnl:subscription_confirmation')) + "?token=" + token
            status = send_subscription_email(email, subscription_confirmation_url)
            if not status:
                NewsletterSubscription.objects.get(email=email).delete()
                logging.getLogger("info").info(
                    "Deleted the record from Subscribe table for " + email + " as email sending failed. status: " + str(
                        status))
            else:
                msg = "Eine E-Mail wurde an '" + email + "' gesendet. Bitte bestätige deine Anmeldung durch " \
                                                        "Klicken des Links in der E-Mail. " \
                                                        "Bitte überprüfe ggf. auch deinen Spam-Ordner."
                messages.success(request, msg)
        else:
            msg = "Es trat ein Fehler auf. Wir kümmern ums drum."
            messages.error(request, msg)

        return HttpResponseRedirect(reverse('vfllnl:subscribe'))

        
    return redirect("home")

def subscription_confirmation(request):
    if request.method == "POST":
        raise Http404

    token = request.GET.get("token", None)
    print('token: ', token)

    if not token:
        logging.getLogger("warning").warning("Invalid Link ")
        messages.error(request, "Invalid Link")
        return HttpResponseRedirect(reverse('vfllnl:subscribe'))

    token = decrypt(token)
    if token:
        token = token.split(SEPARATOR)
        email = token[0]
        print(email)
        initiate_time = token[1]  # time when email was sent , in epoch format. can be used for later calculations
        try:
            subscribe_model_instance = NewsletterSubscription.objects.get(email=email)
            subscribe_model_instance.status = SUBSCRIBE_STATUS_CONFIRMED
            subscribe_model_instance.save()
            messages.success(request, "Deine Anmeldung zum VFLL-Newsletter wurde bestätigt. Vielen Dank.")
        except ObjectDoesNotExist as e:
            logging.getLogger("warning").warning(traceback.format_exc())
            messages.error(request, "Ungültiger Link")
    else:
        logging.getLogger("warning").warning("Invalid token ")
        messages.error(request, "Ungültiger Link")

    return HttpResponseRedirect(reverse('vfllnl:subscribe'))


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
        
    context['form']= form     
    return render(request, "vfllnl/edit_newsletter.html", context)

@login_required
def newsletter_list(request):
    newsletters = EmailTemplate.objects.all()
    context = {
        "newsletters": newsletters
    }
    return render(request, "vfllnl/newsletter_list.html", context)

@login_required
def send_newsletter(request, pk):
    obj = EmailTemplate.objects.get(pk=pk)
    obj = get_object_or_404(EmailTemplate, pk=pk)

    subject = obj.subject
    print('obj body:', obj.body)

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

    recipients = [subscriber.email for subscriber in obj.recipients.all()]
    if not recipients:
        recipients = [
            subscriber.email
            for subscriber in NewsletterSubscription.objects.all()
        ]
    from_email = settings.NEWSLETTER_EMAIL_FROM

    send_mail(
        subject,
        plain_message,
        from_email,
        recipients,
        fail_silently=False,
        html_message=html_message,
    )

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
            recipients = form.cleaned_data['recipients']
            
            nl_instance.recipients.set(recipients)

            return redirect("vfllnl:newsletter-list")
    else:
        form = EmailTemplateForm(instance=obj)

        
    context = {
        "obj": obj,
        "form": form
    }
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

    obj.status = 'c'
    obj.save()

    newsletters = EmailTemplate.objects.filter(status='a').order_by('created_at').reverse()
    return render(request, 'vfllnl/_newsletter_table.html', {'newsletters': newsletters})

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

    
    
    
        
