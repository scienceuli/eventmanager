import os
import re
import logging
from io import BytesIO
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.html import strip_tags

from docxtpl import DocxTemplate

from events.core_models import SiteSettings
from events.email_template import EmailTemplate
from events.utils.email_utils import EmailTemplateError
from mailings.models import ConfirmationMessage

logger = logging.getLogger(__name__)

CONFIRMATION_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "confirmation_template"
)


def get_email_template(template_name):
    try:
        return EmailTemplate.objects.get(name=template_name)
    except EmailTemplate.DoesNotExist:
        raise EmailTemplateError("No such template: {}".format(template_name))


def validate_email_template(raw_template, formatting_dict):
    required_keys = set(re.findall(r"{(.+?)}", raw_template))
    if not required_keys.issubset(set(formatting_dict.keys())):
        logger.warning(
            "Not all required fields of the template were found in formatting dictionary. "
            "required:%s !~ formatting:%s",
            required_keys,
            set(formatting_dict),
        )
        return raw_template
    return raw_template.format(**formatting_dict)


def get_template_path():
    """Return path to the DOCX template file."""
    default_path = os.path.join(
        CONFIRMATION_TEMPLATE_DIR, "Teilnahmebescheinigung_2026.docx"
    )
    return default_path


def create_confirmation_docx(confirmation):
    """Generate a DOCX confirmation from template for the given Confirmation."""
    member = confirmation.event_member
    event = member.event
    site_settings = SiteSettings.load()

    template_path = get_template_path()
    if not os.path.exists(template_path):
        logger.error("Confirmation template not found: %s", template_path)
        return False

    doc = DocxTemplate(template_path)

    description = strip_tags(event.description) if event.description else ""
    today = datetime.now().strftime("%d.%m.%Y")

    context = {
        "academic": member.academic or "",
        "firstname": member.firstname,
        "lastname": member.lastname,
        "event_name": event.name,
        "event_date_string": event.date_string,
        "event_speaker_string": event.speaker_string,
        "event_description": description,
        "place": site_settings.confirmation_place,
        "signatory_vfll": site_settings.confirmation_signatory_vfll,
        "signatory_speaker": site_settings.confirmation_signatory_speaker,
        "today": today,
    }

    doc.render(context)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    filename = (
        f"Teilnahmebescheinigung_{member.lastname}_{member.firstname}"
        f"_{event.label}.docx"
    )
    confirmation.docx_file.save(filename, ContentFile(buffer.read()))
    confirmation.save()
    return True


def create_confirmation_mail(confirmation):
    """Create a queued ConfirmationMessage with DOCX attachment."""
    member = confirmation.event_member
    event = member.event

    formatting_dict = {
        "academic": member.academic or "",
        "firstname": member.firstname,
        "lastname": member.lastname,
        "event_name": event.name,
    }

    template = get_email_template("confirmation")
    text_template = getattr(template, "text_template", "")
    if not text_template:
        raise EmailTemplateError("Email template 'confirmation' has no text_template.")

    mail = ConfirmationMessage()
    mail.subject = f"VFLL - Teilnahmebescheinigung: {event.name}"
    mail.from_address = settings.DEFAULT_FROM_EMAIL
    mail.to_address = member.email
    mail.reply_to = settings.REPLY_TO_EMAIL
    if hasattr(settings, "EMAIL_NOTIFY_BCC") and settings.EMAIL_NOTIFY_BCC:
        mail.bcc_address = settings.EMAIL_NOTIFY_BCC

    mail.content = validate_email_template(text_template, formatting_dict)

    if not confirmation.docx_file:
        create_confirmation_docx(confirmation)

    if confirmation.docx_file:
        mail.add_attachment(confirmation.docx_file)

    mail.confirmation = confirmation
    mail.save()
    return mail
