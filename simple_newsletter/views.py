import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings

from .models import NewsletterSubscription


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
        newsletter_subscription = NewsletterSubscription()
        newsletter_subscription.email = email
        newsletter_subscription.save()
        # send a confirmation mail
        subject = "Newsletter Anmeldung VFLL Fortbildungen"
        message = "Hallo, vielen Dank für das Interessen an unserem Newsletter. Bitte nicht auf diese Mail antworten."
        email_from = settings.NEWSLETTER_EMAIL_FROM
        recipient_list = [
            email,
        ]
        send_mail(subject, message, email_from, recipient_list)
        res = JsonResponse({"msg": "Danke! Newsletter-Anmeldung war erfolgreich!"})
        return res
    return render(request, "index.html")


def validate_email(request):
    email = request.POST.get("email", None)
    if email is None:
        res = JsonResponse({"msg": "E-Mail-Adresse ist notwendig."})
    elif NewsletterSubscription.objects.get(email=email):
        res = JsonResponse({"msg": "Diese E-Mail-Adresse ist bereits registriert."})
    elif not re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", email):
        res = JsonResponse({"msg": "Ungültige E-Mail-Adresse"})
    else:
        res = JsonResponse({"msg": ""})
    return res
