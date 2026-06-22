import ast
import logging
import re
from smtplib import SMTPException

import pandas as pd
import plotly.express as px
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.mail import BadHeaderError, EmailMessage
from django.http import HttpResponse
from plotly.offline import plot

from events.email_template import EmailTemplate
from events.parameters import ws_limits
from vfllnl.models import NewsletterSubscription

logger = logging.getLogger(__name__)


def boolean_translate(boolean_value):
    if boolean_value:
        return "Ja"
    return "Nein"


def yes_no_to_boolean(value):
    if value == "y":
        return True
    return False


def find_duplicates_in_list(L):
    seen = set()
    seen2 = set()
    seen_add = seen.add
    seen2_add = seen2.add
    for item in L:
        if item in seen:
            seen2_add(item)
        else:
            seen_add(item)
    return list(seen2)


def make_bar_plot_from_dict(data, x_string):
    # using pandas dataframe
    df = pd.DataFrame.from_dict(data, orient="index").reset_index()
    df.columns = [x_string, "Teiln"]

    fig = px.bar(df, x=x_string, y=["Teiln"], color_discrete_sequence=["green", "red"])
    fig.update_yaxes(title_text="Teiln.", dtick=1)
    plt_div = plot(fig, output_type="div")
    return plt_div


def get_utilisations(event):
    ws_utilisations = settings.WS_LIMITS.copy()
    for member in event.members.all():
        if member.data.get("ws2022"):
            if member.data["ws2022"] in ws_utilisations.keys():
                ws_utilisations[member.data["ws2022"]] = (
                    ws_utilisations[member.data["ws2022"]] - 1
                )

    tour_utilisations = settings.TOUR_LIMITS.copy()
    for member in event.members.all():
        if member.data.get("tour"):
            if member.data["tour"] in tour_utilisations.keys():
                tour_utilisations[member.data["tour"]] = (
                    tour_utilisations[member.data["tour"]] - 1
                )

    return ws_utilisations, tour_utilisations


def update_boolean_values(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, bool):
            dictionary[key] = boolean_translate(
                value
            )  # Replace value with function call


def convert_data_date(value):
    return value.strftime("%d.%m.%Y")


def convert_boolean_field(value):
    if value:
        return "x"
    return ""


def add_to_newsletter(email):
    try:
        newsletter = NewsletterSubscription.objects.get(email=email)
    except NewsletterSubscription.DoesNotExist:
        newsletter = NewsletterSubscription(email=email)
        newsletter.save()


def convert_html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()


def remove_linebreaks(text):
    return text.replace("\n", " ").replace("\r", "")


def parse_memberships(raw):
    """
    Converts the stored string into a Python list.
    Handles: '', '[]', "['ab']", malformed values.
    """
    if not raw or raw.strip() in ("", "[]"):
        return []

    try:
        value = ast.literal_eval(raw)
        if isinstance(value, list):
            return value
    except Exception:
        pass

    return []  # fallback


def format_memberships(code):
    translator = {
        "sp": "Selfpublisher-Verband",
        "bf": "BücherFrauen",
        "jv": "Junge Verlags- und Medienmenschen",
        "vdu": "Verband deutschsprachiger Übersetzer/innen literarischer und wissenschaftlicher Werke (VdÜ)",
        "tv": "Berufsverband Text und Konzept (alt: Texterverband)",
        "tt": "Texttreff",
        "at": "Unbekannt (at)",
        "bd": "Bundesverband der Dolmetscher und Übersetzer (BdÜ)",
        "vfll": "VFLL",
        "bv": "Börsenverein des deutschen Buchhandels, LV Bayern",
        "gt": "Goldegg Training (Alumni und Absolvent*innen)",
    }
    return translator.get(code, "unbekannt")
