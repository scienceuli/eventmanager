import re
import logging

from smtplib import SMTPException

import pandas as pd
import plotly.express as px
from plotly.offline import plot

from django.core.mail import EmailMultiAlternatives

from django.conf import settings

from events.email_template import EmailTemplate

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
    html_template = getattr(template, "html_template", "")

    if not text_template:
        logger.critical(
            "Missing text template (required) for the input {}.".format(text_template)
        )
        raise EmailTemplateError("Email template is not valid for the input.")
    if not html_template:
        logger.warning(
            "Invalid html template (not required) for the input {}.".format(
                html_template
            )
        )

    text_content = validate_email_template(text_template, formatting_dict)
    html_content = validate_email_template(html_template, formatting_dict, False)

    to = addresses.get("to", [])
    cc = addresses.get("cc", [])
    bcc = addresses.get("bcc", settings.EMAIL_NOTIFY_BCC)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email=from_email, to=to, cc=cc, bcc=bcc
    )
    if html_content:
        msg.attach_alternative(html_content, "text/html")

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
