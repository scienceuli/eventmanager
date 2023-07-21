import os
import pytz
from io import StringIO, BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from django.contrib.staticfiles import finders

from django.template.loader import get_template
from xhtml2pdf import pisa


def get_local_datetime(value):
    return timezone.localtime(value, pytz.timezone("Europe/Berlin"))


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    result = finders.find(uri)
    print("result: ", result)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL  # Typically /static/
        sRoot = settings.STATIC_ROOT  # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL  # Typically /media/
        mRoot = settings.MEDIA_ROOT  # Typically /home/userX/project_static/media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        raise Exception("media URI must start with %s or %s" % (sUrl, mUrl))
    return path


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
