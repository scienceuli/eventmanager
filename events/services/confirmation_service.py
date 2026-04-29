import os
import re
from PyPDF2 import PdfWriter, PdfReader, Transformation
import io
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from events.core_models import SiteSettings
from datetime import datetime

from django.core.files.base import ContentFile

ALLOWED_TAGS = re.compile(r'<(?!/?(?:b|i|u|em|strong|br|font|a|sub|super)\b)[^>]+>')
CONFIRMATION_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "confirmation_template"
)
PARA_FONT_SIZE = 10
FONT_SIZE = 12
FONT_SIZE_SMALL = 8
FONT_NAME = "Times-Roman"  # fallback

# Register Garamond if TTF file is available
_garamond_path = os.path.join(CONFIRMATION_TEMPLATE_DIR, "Garamond.ttf")
if os.path.exists(_garamond_path):
    pdfmetrics.registerFont(TTFont("Garamond", _garamond_path))
    FONT_NAME = "Garamond"

def clean_html_for_reportlab(html):
    """Strip HTML tags not supported by ReportLab Paragraph."""
    if not html:
        return ""
    return ALLOWED_TAGS.sub('', html)

class ConfirmationService:
    def __init__(self):
        pass

    def get_template_path(self):
        self.default_path = os.path.join(
            CONFIRMATION_TEMPLATE_DIR, "Teilnahmebescheinigung_2026.pdf"
        )

    def prepare_pdf(self):
        self.template_pdf = PdfReader(open(self.default_path, "rb"))
        self.template_page= self.template_pdf.pages[0]

        self.packet = io.BytesIO()
        self.c = Canvas(self.packet,pagesize=(self.template_page.mediabox.width,self.template_page.mediabox.height))
        self.c.setFont(FONT_NAME, FONT_SIZE)

    def get_pdf_filename(self):
        self.filename = (
            f"Teilnahmebescheinigung_{self.member.firstname}_{self.member.lastname}"
            f"_{self.member.event.label}.pdf"
        )

    def addText(self, text, point, size='normal'):
        if size == 'small':
            self.c.setFont(FONT_NAME, FONT_SIZE_SMALL)
        else:
            self.c.setFont(FONT_NAME, FONT_SIZE)
        self.c.drawString(point[0], point[1], text)

    def addCenteredText(self, text, point, size='normal'):
        if size == 'small':
            self.c.setFont(FONT_NAME, FONT_SIZE_SMALL)
        else:
            self.c.setFont(FONT_NAME, FONT_SIZE)
        self.c.drawCentredString(point[0], point[1], text)

    def addParagraph(self, text, point, dim):
        style = ParagraphStyle("confirmation", fontName=FONT_NAME, fontSize=PARA_FONT_SIZE, leading=FONT_SIZE * 1.2)
        p = Paragraph(text, style)
        w, h = p.wrapOn(self.c, dim[0], dim[1])
        p.drawOn(self.c, point[0], point[1] - h)

    def debug_grid(self):
        """Temporary: draw coordinate grid on the canvas to find text positions."""
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

    def prepare_text(self):
        event = self.member.event
        site_settings = SiteSettings.load()
        today = datetime.now().strftime("%d.%m.%Y")
        academic = self.member.academic or ""
        if academic:
            full_name = academic + " " + self.member.firstname + " " + self.member.lastname
        else:
            full_name = self.member.firstname + " " + self.member.lastname
        place_date_string = site_settings.confirmation_place + ", " + today

        self.addCenteredText(full_name,(300,575))
        self.addCenteredText(event.name,(300,475))
        self.addCenteredText(event.date_string,(300,525))
        self.addCenteredText(event.speaker_string,(300,445))
        self.addParagraph(clean_html_for_reportlab(event.description),(150,350), (300,100))
        self.addCenteredText(place_date_string,(300,150))
        self.addText(site_settings.confirmation_signatory_speaker,(340,100), 'small')
        self.addText(site_settings.confirmation_signatory_vfll,(60,100), 'small')

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
