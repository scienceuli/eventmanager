import logging, traceback
from django.urls import reverse
import requests
from django.template.loader import get_template
from django.utils.html import strip_tags
from django.conf import settings


def send_email(data):
    try:
        url = settings.MAILGUN_URL
        status = requests.post(
            url,
            auth=("api", settings.MAILGUN_API_KEY),
            data={"from": "VFLL <postmaster@mg.vfll.de>",
                  "to": [data["email"]],
                  "subject": data["subject"],
                  "text": data["plain_text"],
                  "html": data["html_text"]}
        )
        logging.getLogger("info").info("Mail sent to " + data["email"] + ". status: " + str(status))
        return status
    except Exception as e:
        logging.getLogger("error").error(traceback.format_exc())
        return False


def send_subscription_email(email, subscription_confirmation_url):
    data = dict()
    data["confirmation_url"] = subscription_confirmation_url
    data["subject"] = "Bitte bestätige deine Anmeldung für den VFLL-Newsletter"
    data["email"] = email
    template = get_template("simple_newsletter/emails/subscription.html")
    data["html_text"] = template.render(data)
    data["plain_text"] = strip_tags(data["html_text"])
    return send_email(data)