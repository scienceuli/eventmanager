import re
import logging
import traceback
from disposable_email_domains import blocklist

from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

from .models import NewsletterSubscription

from .constants import SUBSCRIBE_STATUS_SUBSCRIBED


def validate_email(email):
    if email is None:
        return "Email is required."
    elif not re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", email):
        return "Invalid Email Address."
    elif email.split("@")[-1].lower() in blocklist:
        return "Temporäre E-Mail-Adressen werden nicht akzeptiert."
    elif NewsletterSubscription.objects.filter(email=email).exists():
        return "E-Mail-Adresse exitiert bereits"
    else:
        return None


def save_email(email):
    try:
        subscribe_model_instance = NewsletterSubscription.objects.get(email=email)
    except ObjectDoesNotExist as e:
        subscribe_model_instance = NewsletterSubscription()
        subscribe_model_instance.email = email
    except Exception as e:
        logging.getLogger("error").error(traceback.format_exc())
        return False

    # does not matter if already subscribed or not...resend the email
    subscribe_model_instance.status = SUBSCRIBE_STATUS_SUBSCRIBED
    subscribe_model_instance.save()
    return True
