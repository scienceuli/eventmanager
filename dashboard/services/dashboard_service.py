from django.db.models.functions import ExtractYear
from django.db.models import Count, OuterRef, Subquery, IntegerField

from events.models import Event, EventMember
from shop.models import Order
from invoices.models import Invoice


class DashboardService:

    def get_event_stats(self, year=None, search=None):
        """Return aggregated event statistics, optionally filtered by year/search."""
        events = Event.objects.all()

        if year:
            events = events.annotate(year=ExtractYear("first_day")).filter(year=year)

        if search:
            events = events.filter(name__icontains=search)

        total_members = (
            EventMember.objects.filter(
                email__in=Order.objects.values_list("email", flat=True)
            )
            .distinct()
            .count()
        )

        event_data = events.annotate(num_orders=Count("order_items", distinct=True))

        data = [
            {
                "name": event.name,
                "num_orders": event.num_orders,
                "costs": event.get_balance(),
            }
            for event in event_data
        ]

        return {
            "total_members": total_members,
            "event_data": data,
        }

    def get_members_with_invoices(self):
        """Return all members enriched with order and invoice info."""
        members = EventMember.objects.all()

        enriched = []
        for member in members:
            try:
                order = Order.objects.filter(email=member.email).first()
                invoice = Invoice.objects.filter(order=order).first()
            except Exception:
                order = None
                invoice = None

            enriched.append(
                {
                    "member": member,
                    "invoice_url": (
                        invoice.pdf.url if invoice and invoice.pdf else None
                    ),
                    "order_id": order.id if order else None,
                }
            )

        return enriched

    def get_year_list(self):
        """Return distinct years from events, ordered descending."""
        return (
            Event.objects.annotate(year=ExtractYear("first_day"))
            .values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )

    def search_events(self, query, limit=10):
        """Search events by name, return formatted results for autocomplete."""
        events = Event.objects.filter(name__icontains=query).values(
            "id", "name", "first_day"
        )[:limit]

        results = []
        for e in events:
            if e["first_day"]:
                results.append(
                    {"id": e["id"], "text": f"{e['name']} ({e['first_day']})"}
                )
            else:
                results.append({"id": e["id"], "text": e["name"]})
        return results

    def get_members_for_event(self, event_id):
        """Return members for a specific event with matched order/invoice info."""
        order_subquery = (
            Order.objects.filter(
                email=OuterRef("email"), items__event__id=event_id
            ).values("id")[:1]
        )

        members = (
            EventMember.objects.filter(event__id=event_id)
            .annotate(matched_order_id=Subquery(order_subquery))
        )

        invoice_subquery = Invoice.objects.filter(
            order_id=OuterRef("matched_order_id")
        ).values("id")[:1]

        members = members.annotate(
            invoice_id=Subquery(invoice_subquery, output_field=IntegerField())
        )

        return [
            {
                "name": member.lastname,
                "email": member.email,
                "event": member.event.name,
                "invoice_id": (
                    Invoice.objects.get(id=member.invoice_id).id
                    if member.invoice_id
                    else None
                ),
            }
            for member in members
        ]
