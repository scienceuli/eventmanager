from django.shortcuts import get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from invoices.models import Invoice
from dashboard.services.dashboard_service import DashboardService


@login_required
def dashboard_stats(request):
    year = request.GET.get("year")
    search = request.GET.get("search", "").strip()

    service = DashboardService()
    stats = service.get_event_stats(year=year, search=search)
    return JsonResponse(stats)


@login_required
def dashboard(request):
    service = DashboardService()
    enriched = service.get_members_with_invoices()
    year_list = service.get_year_list()
    return render(
        request,
        "dashboard/dashboard.html",
        {"members": enriched, "year_list": year_list},
    )


@login_required
def event_autocomplete(request):
    q = request.GET.get("q", "")
    service = DashboardService()
    results = service.search_events(q)
    return JsonResponse({"results": results})


@login_required
def members_list(request):
    event_id = request.GET.get("event")
    service = DashboardService()
    data = service.get_members_for_event(event_id)
    return JsonResponse({"members": data})


@login_required
def view_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if not request.user.is_staff:
        raise Http404("Not authorized")

    if not invoice.pdf:
        raise Http404("PDF not found")

    return FileResponse(invoice.pdf.open("rb"), content_type="application/pdf")
