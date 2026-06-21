import logging
import re
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import BadHeaderError, EmailMessage

from events.email_template import EmailTemplate

logger = logging.getLogger(__name__)


class EmailTemplateError(Exception):
    pass


def get_email_template(template_name):
    try:
        template = EmailTemplate.objects.get(name=template_name)
        return template
    except EmailTemplate.DoesNotExist:
        raise EmailTemplateError("No such template: {}".format(template_name))


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


def send_email(
    addresses,
    subject,
    from_email,
    reply_to,
    template_name,
    formatting_dict=None,
    **kwargs,
):
    formatting_dict = formatting_dict or {}
    template = get_email_template(template_name)
    text_template = getattr(template, "text_template", "")
    # html_template = getattr(template, "html_template", "")
    invoice_name = kwargs.get("invoice_name")
    pdf = kwargs.get("pdf")
    mime = kwargs.get("mime")

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
    reply_to = reply_to

    msg = EmailMessage(
        subject,
        text_content,
        from_email=from_email,
        to=to,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
    )
    if invoice_name and pdf and mime:
        msg.attach(invoice_name, pdf, mime)

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


def get_mail_to_admin_template_name(registration_form):
    if registration_form == "s":
        mail_to_admin_template_name = "anmeldung"
    elif registration_form == "w":
        mail_to_admin_template_name = "wc_anmeldung"
    elif registration_form == "m":
        mail_to_admin_template_name = "mv_anmeldung"
    elif registration_form == "f":
        mail_to_admin_template_name = "ft_anmeldung"
    elif registration_form == "f24":
        mail_to_admin_template_name = "ft_24_anmeldung"
    elif registration_form == "f26":
        mail_to_admin_template_name = "ft_26_anmeldung"
    else:
        mail_to_admin_template_name = "anmeldung"

    return mail_to_admin_template_name


def get_mail_to_member_template_name(registration_form, attend_status):
    if registration_form == "s":
        if attend_status == "waiting":
            mail_to_member_template_name = "warteliste"
        else:
            mail_to_member_template_name = "bestaetigung"
    elif registration_form == "w":
        mail_to_member_template_name = "wc_bestaetigung"
    elif registration_form == "m":
        mail_to_member_template_name = "mv_bestaetigung"
    elif registration_form == "f":
        mail_to_member_template_name = "ft_bestaetigung"
    elif registration_form == "f24":
        mail_to_member_template_name = "ft_24_bestaetigung"
    elif registration_form == "f26":
        mail_to_member_template_name = "ft_26_bestaetigung"
    else:
        mail_to_member_template_name = "bestaetigung"
    return mail_to_member_template_name


def send_registration_emails(event, form, formatting_dict, attend_status):
    admin_template = get_mail_to_admin_template_name(event.registration_form)
    member_template = get_mail_to_member_template_name(
        event.registration_form, attend_status
    )

    vfll_sent = send_email_after_registration(
        "vfll", event, form, admin_template, formatting_dict
    )

    member_sent = False
    if settings.SEND_EMAIL_AFTER_REGISTRATION_TO_MEMBER:
        member_sent = send_email_after_registration(
            "member", event, form, member_template, formatting_dict
        )

    return vfll_sent, member_sent


def send_email_after_registration(to, event, form, template, formatting_dict):
    formatting_dict.update(
        {
            "event": event.name,
            "date": event.first_day.strftime("%d.%m.%Y"),
        }
    )

    if event.registration_form == "s" or event.registration_form == "w":
        subject = f"Anmeldung am Kurs {event.name}"
        reply_to = [settings.REPLY_TO_EMAIL]
    elif event.registration_form == "m":
        subject = f"Anmeldung zu {event.name}"
        reply_to = [settings.MV_REPLY_TO_EMAIL]
    elif event.registration_form == "f24":
        subject = f"Anmeldung zur Fachtagung 2024 / Mitgliederversammlung"
        reply_to = [settings.FT_REPLY_TO_EMAIL]
    elif event.registration_form == "f26":
        subject = f"Anmeldung zur Fachtagung 2026 / Mitgliederversammlung"
        reply_to = [settings.FT_REPLY_TO_EMAIL]
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

        sponsors_string = ""
        if event.sponsors.all():
            sponsors_string = "Für weitere Informationen wenden Sie sich bitte an: "
            sponsors_list = [
                sponsor.email
                for sponsor in event.sponsors.all().exclude(email__isnull=True)
            ]
            sponsors_string += ", ".join(sponsors_list)

        if event.close_date:
            close_date = event.close_date.strftime("%d.%m.%Y")
        else:
            close_date = ""

        formatting_dict.update(
            {
                "label": event.label,
                "start": event.get_first_day_start_date(),
                "close_date": close_date,
                "addresses_string": addresses_string,
                "speaker_string": speaker_string,
                "sponsors_string": sponsors_string,
                "memberships_labels": form.selected_memberships_labels(),
            }
        )
    elif event.registration_form in ("f24", "f26"):
        formatting_dict.update(
            {
                "start": event.get_first_day_start_date(),
            }
        )
    elif event.registration_form == "w":
        formatting_dict.update(
            {
                "start": event.get_first_day_start_date(),
                "label": event.label,
            }
        )

    if event.registration_form in ("s", "w", "m", "f24", "f26"):
        try:
            send_email(
                addresses,
                subject,
                settings.DEFAULT_FROM_EMAIL,
                reply_to,
                template,
                formatting_dict=formatting_dict,
            )
            return True
        except BadHeaderError:
            return HttpResponse("Invalid header found.")
