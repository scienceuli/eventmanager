import re
import logging

from smtplib import SMTPException

import pandas as pd
import plotly.express as px
from plotly.offline import plot

from django.core.mail import EmailMultiAlternatives, BadHeaderError

from django.conf import settings
from django.http import HttpResponse

from events.email_template import EmailTemplate

from events.parameters import ws_limits


logger = logging.getLogger(__name__)


class EmailTemplateError(Exception):
    pass


def validate_email_template(raw_template, formatting_dict, required=True):
    required_keys = set(re.findall("{(.+?)}", raw_template))
    if not required_keys.issubset(set(formatting_dict.keys())):
        if required:
            logger.critical(
                "Not all required fields of the template were found in formatting dictionary.\n"
                "required:{} !~ formatting:{}".format(
                    required_keys, set(formatting_dict)
                )
            )
            raise EmailTemplateError(
                "Not all required fields of the template were found in formatting dictionary.\n"
                "required:{} !~ formatting:{}".format(
                    required_keys, set(formatting_dict)
                )
            )
        else:
            logger.warning(
                "Not all required fields of the template were found in formatting dictionary."
            )
            return raw_template

    return raw_template.format(**formatting_dict)


def get_email_template(template_name):
    try:
        template = EmailTemplate.objects.get(name=template_name)
        return template
    except EmailTemplate.DoesNotExist:
        raise EmailTemplateError("No such template: {}".format(template_name))


def send_email(
    addresses, subject, from_email, template_name, formatting_dict=None, **kwargs
):
    formatting_dict = formatting_dict or {}
    template = get_email_template(template_name)
    text_template = getattr(template, "text_template", "")
    # html_template = getattr(template, "html_template", "")

    if not text_template:
        logger.critical(
            "Missing text template (required) for the input {}.".format(text_template)
        )
        raise EmailTemplateError("Email template is not valid for the input.")
    # if not html_template:
    #     logger.warning(
    #         "Invalid html template (not required) for the input {}.".format(
    #             html_template
    #         )
    #     )

    text_content = validate_email_template(text_template, formatting_dict)
    # html_content = validate_email_template(html_template, formatting_dict, False)

    to = addresses.get("to", [])
    cc = addresses.get("cc", [])
    bcc = addresses.get("bcc", settings.EMAIL_NOTIFY_BCC)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email=from_email, to=to, cc=cc, bcc=bcc
    )
    # if html_content:
    #     msg.attach_alternative(html_content, "text/html")

    try:
        msg.send()
    except (SMTPException, ConnectionRefusedError) as e:
        logger.critical("Sending email raised an exception: %s", e)
    else:
        # increase count on email_template
        template.add_count()
        if kwargs.get("verbose", 0) > 1:
            print(msg)
        return True


def send_email_after_registration(to, event, form, template, formatting_dict):
    if event.registration_form == "s":
        subject = f"Anmeldung am Kurs {event.name}"
    # mails to vfll
    addresses_list = []
    if to == "vfll":
        if event.sponsors:
            for sponsor in event.sponsors.all().exclude(email__isnull=True):
                addresses_list.append(sponsor.email)
        if len(addresses_list) == 0:
            if event.registration_recipient:
                addresses_list.append(event.registration_recipient)
            else:
                addresses_list.append(settings.EVENT_RECEIVER_EMAIL)

    elif to == "member":
        addresses_list.append(formatting_dict.get("email"))

    addresses = {"to": addresses_list}

    addresses_string = " oder ".join(addresses_list)

    # Dozenten - nur bei Fortbildungen
    if event.registration_form == "s":
        speaker_list = []
        if event.speaker:
            for sp in event.speaker.all():
                speaker_list.append(sp.full_name)

        if len(speaker_list) == 0:
            speaker_string = "NN"
        else:
            speaker_string = ", ".join(speaker_list)

        formatting_dict.update(
            {
                "event": event.name,
                "label": event.label,
                "start": event.get_first_day_start_date(),
                "close_date": event.close_date.strftime("%d.%m.%Y"),
                "addresses_string": addresses_string,
                "speaker_string": speaker_string,
                "memberships_labels": form.selected_memberships_labels(),
            }
        )

        if event.registration_form == "s" or event.registration_form == "f":
            try:
                send_email(
                    addresses,
                    subject,
                    settings.DEFAULT_FROM_EMAIL,
                    template,
                    formatting_dict=formatting_dict,
                )
                return True
            except BadHeaderError:
                return HttpResponse("Invalid header found.")


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


def make_bar_plot_from_dict(data, y_string):
    # using pandas dataframe
    df = pd.DataFrame.from_dict(data, orient="index").reset_index()
    df.columns = ["ws", "Teiln", "frei"]
    print(df)

    fig = px.bar(
        df, x="ws", y=["Teiln", "frei"], color_discrete_sequence=["red", "green"]
    )
    fig.update_yaxes(title_text="Teiln.")
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
