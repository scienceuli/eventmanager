# views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.db.models.functions import ExtractYear
from django.db.models import Count, Q
from django.db.models import OuterRef, Subquery, IntegerField
from django.contrib.auth.decorators import login_required

from events.models import Event, EventMember
from shop.models import Order
from invoices.models import Invoice


@login_required
def dashboard_stats(request):

    year = request.GET.get('year')
    search = request.GET.get('search', '').strip()
    events = Event.objects.all()

    if year:
        events = events.annotate(year=ExtractYear('first_day')).filter(year=year)

    if search:
        events = events.filter(name__icontains=search)

    total_members = EventMember.objects.filter(
        email__in=Order.objects.values_list('email', flat=True)
    ).distinct().count()

    # event_data = events.annotate(
    #     num_orders=Count('order_items', distinct=True)
    # ).values('name', 'num_orders', 'get_balance()')
    event_data = events.annotate(
        num_orders=Count('order_items', distinct=True)
    )
    
    data = []
    for event in event_data:
        data.append({
            "name": event.name,
            "num_orders": event.num_orders,
            # "costs": event.costs,
            "costs": event.get_balance(),
            # "balance": event.get_balance() 
        })
    stats = {
        "total_members": total_members,
        "event_data": list(data),
    }
    return JsonResponse(stats)

# views.py


@login_required
def dashboard(request):
    members = EventMember.objects.all()

    enriched = []
    for member in members:
        try:
            order = Order.objects.filter(email=member.email).first()
            invoice = Invoice.objects.filter(order=order).first()
        except:
            order = None
            invoice = None

        enriched.append({
            'member': member,
            'invoice_url': invoice.pdf.url if invoice and invoice.pdf else None,
            'order_id': order.id if order else None
        })
        year_list = Event.objects.annotate(year=ExtractYear('first_day')) \
                  .values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'dashboard/dashboard.html', {'members': enriched, 'year_list': year_list})


@login_required
def event_autocomplete(request):
    q = request.GET.get('q', '')
    events = Event.objects.filter(name__icontains=q).values('id', 'name', 'first_day')[:10]
    results = []
    for e in events:
        if e['first_day']:
            results.append({'id': e['id'], 'text': f"{e['name']} ({e['first_day']})"})
        else:
            results.append({'id': e['id'], 'text': e['name']})
    return JsonResponse({'results': results})
    
    

@login_required
def members_list(request):
    event_id = request.GET.get('event')
    members = EventMember.objects.all()

    order_subquery = Order.objects.filter(
        email=OuterRef('email'),
        items__event__id=event_id
    ).values('id')[:1]

    members= members.filter(event__id=event_id).annotate(
        matched_order_id=Subquery(order_subquery)
    )

    invoice_subquery = Invoice.objects.filter(
        order_id=OuterRef('matched_order_id')
    ).values('id')[:1]



    if event_id:
        #members = members.filter(event_id=event_id).distinct().select_related('event')
        members = members.annotate(
            invoice_id=Subquery(invoice_subquery, output_field=IntegerField())
        )

    data = [
        {
            'name': member.lastname,
            'email': member.email,
            'event': member.event.name,
            # 'invoice_url': p.invoice.pdf.url if p.invoice and p.invoice.pdf else None
            #'invoice_url': Invoice.objects.get(id=member.invoice_id).pdf.url if member.invoice_id else None
            'invoice_id': Invoice.objects.get(id=member.invoice_id).id if member.invoice_id else None
        }
        for member in members
    ]

    return JsonResponse({'members': data})






@login_required
def view_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    # Add your permission logic here:
    if not request.user.is_staff:
        raise Http404("Not authorized")

    if not invoice.pdf:
        raise Http404("PDF not found")

    return FileResponse(invoice.pdf.open('rb'), content_type='application/pdf')
