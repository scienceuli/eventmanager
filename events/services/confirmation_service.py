import io
import os
import re
from datetime import datetime

from django.core.files.base import ContentFile
from PyPDF2 import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from events.core_models import SiteSettings

ALLOWED_TAGS = re.compile(r"<(?!/?(?:b|i|u|em|strong|br|font|a|sub|super)\b)[^>]+>")
CONFIRMATION_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "confirmation_template"
)

FONT_COLOR = HexColor("#5B5F61")

FONT_SIZES = {
    "name": 28,
    "text": 15,
    "format": 24,
    "event": 24,
    "small": 9,
}

# Map weight names to TTF filenames in confirmation_template/
_MERRIWEATHER_FILES = {
    "regular": "Merriweather-Regular.ttf",
    "bold": "Merriweather-Bold.ttf",
    "semibold": "Merriweather-SemiBold.ttf",
    "light": "Merriweather-Light.ttf",
    "italic": "Merriweather-Italic.ttf",
    "bold-italic": "Merriweather-BoldItalic.ttf",
}

# Register each variant that exists; build weight → registered font name map
MERRIWEATHER = {}
for _weight, _filename in _MERRIWEATHER_FILES.items():
    _path = os.path.join(CONFIRMATION_TEMPLATE_DIR, _filename)
    if os.path.exists(_path):
        _font_name = f"Merriweather-{_weight.title().replace('-', '')}"
        pdfmetrics.registerFont(TTFont(_font_name, _path))
        MERRIWEATHER[_weight] = _font_name

# Register Garamond if available
_garamond_path = os.path.join(CONFIRMATION_TEMPLATE_DIR, "Garamond.ttf")
if os.path.exists(_garamond_path):
    pdfmetrics.registerFont(TTFont("Garamond", _garamond_path))

FALLBACK_FONT = "Times-Roman"


def from_acrobat(x, y, page_height=841.9):
    return (x, page_height - y)


def _resolve_font(weight="regular"):
    return MERRIWEATHER.get(weight, FALLBACK_FONT)


def clean_html_for_reportlab(html):
    if not html:
        return ""
    return ALLOWED_TAGS.sub("", html)


class ConfirmationService:
    def __init__(self):
        pass

    def get_template_path(self):
        event = self.member.event
        if event.confirmation_template:
            self.default_path = event.confirmation_template.path
        else:
            self.default_path = os.path.join(
                CONFIRMATION_TEMPLATE_DIR, "Teilnahmebescheinigung_2026.pdf"
            )

    def prepare_pdf(self):
        self.template_pdf = PdfReader(open(self.default_path, "rb"))
        self.template_page = self.template_pdf.pages[0]

        self.packet = io.BytesIO()
        self.c = Canvas(
            self.packet,
            pagesize=(
                self.template_page.mediabox.width,
                self.template_page.mediabox.height,
            ),
        )
        self.c.setFillColor(FONT_COLOR)
        self.c.setFont(_resolve_font("regular"), FONT_SIZES["text"])
        self.y = float(self.template_page.mediabox.height)  # start at top

    def get_pdf_filename(self):
        self.filename = (
            f"Teilnahmebescheinigung_{self.member.firstname}_{self.member.lastname}"
            f"_{self.member.event.label}.pdf"
        )

    def addText(
        self, text, point=None, size="text", position="standard", weight="regular"
    ):
        font_size = FONT_SIZES.get(size, FONT_SIZES["text"])
        font_weight = _resolve_font(weight)
        self.c.setFont(font_weight, font_size)
        self.c.setFillColor(FONT_COLOR)
        y = point[1] if point else self.y
        x = point[0] if point else 250
        if position == "centered":
            self.c.drawCentredString(x, y, text)
        else:
            self.c.drawString(x, y, text)
        self.y = y - font_size

    def addTextWrapped(
        self,
        text,
        point=None,
        max_width=300,
        size="text",
        position="standard",
        weight="regular",
    ):
        font_size = FONT_SIZES.get(size, FONT_SIZES["text"])
        style = ParagraphStyle(
            "wrapped",
            fontName=_resolve_font(weight),
            fontSize=font_size,
            leading=font_size * 1.3,
            textColor=FONT_COLOR,
        )
        p = Paragraph(text, style)
        w, h = p.wrapOn(self.c, max_width, 1000)
        y = point[1] if point else self.y
        x = point[0] if point else 250
        p.drawOn(self.c, x, y - h)
        self.y = y - h

    def addParagraph(self, text, point, dim, size="text", weight="regular"):
        font_size = FONT_SIZES.get(size, FONT_SIZES["text"])
        font_weight = _resolve_font(weight)
        style = ParagraphStyle(
            "confirmation",
            fontName=font_weight,
            fontSize=font_size,
            leading=font_size * 1.2,
            textColor=FONT_COLOR,
        )
        p = Paragraph(text, style)
        w, h = p.wrapOn(self.c, dim[0], dim[1])
        p.drawOn(self.c, point[0], point[1] - h)

    def debug_grid(self):
        self.c.setStrokeColorRGB(0.8, 0.8, 0.8)
        self.c.setFont("Helvetica", 6)
        w = float(self.template_page.mediabox.width)
        h = float(self.template_page.mediabox.height)
        for x in range(0, int(w), 50):
            self.c.line(x, 0, x, h)
            self.c.drawString(x + 2, 10, str(x))
        for y in range(0, int(h), 50):
            self.c.line(0, y, w, y)
            self.c.drawString(2, y + 2, str(y))

    def space(self, gap=20):
        self.y -= gap

    def prepare_text(self):
        event = self.member.event
        site_settings = SiteSettings.load()
        today = datetime.now().strftime("%d.%m.%Y")
        academic = self.member.academic or ""
        if academic:
            full_name = (
                academic + " " + self.member.firstname + " " + self.member.lastname
            )
        else:
            full_name = self.member.firstname + " " + self.member.lastname
        place_date_string = site_settings.confirmation_place + ", " + today

        self.addText(
            full_name,
            from_acrobat(250, 226),
            size="name",
            position="standard",
            weight="semibold",
        )
        self.addText(
            "hat am",
            from_acrobat(250, 278),
            size="text",
            position="standard",
            weight="light",
        )
        self.addText(
            event.eventformat.title
            if event.eventformat.title
            else event.eventformat.name,
            from_acrobat(250, 308),
            size="format",
            position="standard",
            weight="light",
        )
        # self.addText(
        #     event.name,
        #     from_acrobat(250, 339),
        #     size="event",
        #     position="standard",
        #     weight="bold",
        # )
        self.addTextWrapped(
            event.name,
            from_acrobat(250, 339),
            max_width=300,
            size="event",
            position="standard",
            weight="bold",
        )
        self.space(20)
        self.addText(
            "teilgenommen.",
            size="text",
            position="standard",
            weight="light",
        )
        self.space(20)
        self.addText(
            event.date_string_confirmation,
            size="text",
            position="standard",
            weight="regular",
        )
        self.addText(
            event.speaker_string,
            from_acrobat(420, 794),
            size="small",
            position="standard",
            weight="light",
        )
        # self.addText(
        #     event.speaker_string,
        #     from_acrobat(300, 445),
        #     position="standard",
        #     weight="italic",
        # )
        # self.addText(place_date_string, from_acrobat(300, 150), position="standard")
        # self.addText(
        #     site_settings.confirmation_signatory_speaker,
        #     from_acrobat(340, 100),
        #     size="small",
        # )
        # self.addText(
        #     site_settings.confirmation_signatory_vfll,
        #     from_acrobat(60, 100),
        #     size="small",
        # )

    def merge(self):
        self.c.save()
        self.packet.seek(0)
        result_pdf = PdfReader(self.packet)
        result = result_pdf.pages[0]

        self.output = PdfWriter()

        op = Transformation().rotate(0).translate(tx=0, ty=0)
        result.add_transformation(op)
        self.template_page.merge_page(result)
        self.output.add_page(self.template_page)

    def generate(self):
        pdf_buffer = io.BytesIO()
        self.output.write(pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    def make_pdf(self, confirmation):
        self.member = confirmation.event_member
        self.get_template_path()
        self.prepare_pdf()
        self.debug_grid()  # TODO: remove after coordinates are finalized
        self.prepare_text()
        self.merge()
        self.get_pdf_filename()
        pdf_buffer = self.generate()

        confirmation.pdf_file.save(self.filename, ContentFile(pdf_buffer.read()))
        confirmation.save()

    def make_pdfs_for_event(self, event):
        from events.models import Confirmation
        from events.utils.confirmation_utils import create_confirmation_mail
        from mailings.models import ConfirmationMessage

        members = event.members.filter(attend_status="done").select_related("event")
        created_count = 0
        updated_count = 0
        errors = []

        for member in members:
            try:
                confirmation, created = Confirmation.objects.get_or_create(
                    event_member=member
                )
                self.make_pdf(confirmation)
                if created:
                    create_confirmation_mail(confirmation)
                    created_count += 1
                else:
                    try:
                        mail = confirmation.message
                        mail.attachment_set.all().delete()
                        confirmation.pdf_file.open("rb")
                        mail.add_attachment(confirmation.pdf_file)
                        confirmation.pdf_file.close()
                        mail.sent = False
                        mail.last_attempt = None
                        mail.save(update_fields=["sent", "last_attempt"])
                    except ConfirmationMessage.DoesNotExist:
                        create_confirmation_mail(confirmation)
                    confirmation.mail_sent_date = None
                    confirmation.save(update_fields=["mail_sent_date"])
                    updated_count += 1
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(
                    "Error creating confirmation for member %s: %s", member.pk, e
                )
                errors.append(f"{member.firstname} {member.lastname}: {e}")

        return created_count, updated_count, errors
