from django.shortcuts import render, redirect
from django.contrib import messages

from .models import NewsletterSubscription


def unsubscribe(request, email):
    try:
        subscription = NewsletterSubscription.objects.get(email=email)
        subscription.delete()
        messages.success(request, "Du hast dich von Newsletter abgemeldet.")
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, "Email nicht gefunden.")
    return redirect("home")  # Redirect to a page after unsubscribing
