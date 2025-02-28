from io import StringIO, BytesIO

from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.template.loader import get_template

from xhtml2pdf import pisa


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)

    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type="application/pdf")
    pdf_status = pisa.CreatePDF(html, dest=response)

    if pdf_status.err:
        return HttpResponse("Es gab Probleme mit <pre>" + html + "</pre>")

    return response


def render_to_pdf_directly(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    # with open("html_out.html", "w") as out:
    #    out.write(html)
    # result = StringIO()
    result = BytesIO()
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("utf-8")),
        result,
        encoding="utf-8",
        # link_callback=link_callback,
    )
    if not pdf.err:
        return result.getvalue()
        # return HttpResponse(result.getvalue(), content_type="application/pdf")
        # return pdf
    else:
        return HttpResponse("Errors")
