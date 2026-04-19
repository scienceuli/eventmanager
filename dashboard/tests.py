from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from events.models import Event, EventCategory, EventFormat, EventLocation, EventMember
from shop.models import Order, OrderItem
from dashboard.services.dashboard_service import DashboardService


class DashboardServiceTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="testcat")
        cls.eventformat = EventFormat.objects.create(name="testformat")
        cls.location = EventLocation.objects.create(title="testloc")

        cls.event1 = Event.objects.create(
            name="Workshop Python",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            label="workshop-python",
            price="100.00",
            first_day=date(2025, 6, 15),
        )

        cls.event2 = Event.objects.create(
            name="Workshop Django",
            category=cls.category,
            eventformat=cls.eventformat,
            location=cls.location,
            label="workshop-django",
            price="150.00",
            first_day=date(2024, 3, 10),
        )

        cls.member1 = EventMember.objects.create(
            event=cls.event1,
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            attend_status="registered",
        )

        cls.member2 = EventMember.objects.create(
            event=cls.event1,
            firstname="Erika",
            lastname="Musterfrau",
            email="erika@example.com",
            attend_status="registered",
        )

        cls.member3 = EventMember.objects.create(
            event=cls.event2,
            firstname="Hans",
            lastname="Test",
            email="hans@example.com",
            attend_status="registered",
        )

        cls.order1 = Order.objects.create(
            firstname="Max",
            lastname="Mustermann",
            email="max@example.com",
            payment_type="r",
            payment_date=timezone.now(),
        )
        OrderItem.objects.create(
            order=cls.order1,
            event=cls.event1,
            price=Decimal("100.00"),
            premium_price=Decimal("135.00"),
            cost=Decimal("100.00"),
        )

        cls.service = DashboardService()


class GetEventStatsTest(DashboardServiceTestBase):

    def test_returns_all_events(self):
        stats = self.service.get_event_stats()
        self.assertEqual(len(stats["event_data"]), 2)

    def test_filter_by_year(self):
        stats = self.service.get_event_stats(year=2025)
        self.assertEqual(len(stats["event_data"]), 1)
        self.assertEqual(stats["event_data"][0]["name"], "Workshop Python")

    def test_filter_by_search(self):
        stats = self.service.get_event_stats(search="Django")
        self.assertEqual(len(stats["event_data"]), 1)
        self.assertEqual(stats["event_data"][0]["name"], "Workshop Django")

    def test_total_members_count(self):
        stats = self.service.get_event_stats()
        # Only max@example.com has an order
        self.assertEqual(stats["total_members"], 1)

    def test_event_data_has_required_fields(self):
        stats = self.service.get_event_stats()
        for event in stats["event_data"]:
            self.assertIn("name", event)
            self.assertIn("num_orders", event)
            self.assertIn("costs", event)


class GetYearListTest(DashboardServiceTestBase):

    def test_returns_distinct_years(self):
        years = list(self.service.get_year_list())
        self.assertEqual(years, [2025, 2024])


class SearchEventsTest(DashboardServiceTestBase):

    def test_search_by_name(self):
        results = self.service.search_events("Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.event1.id)

    def test_search_returns_formatted_text_with_date(self):
        results = self.service.search_events("Python")
        self.assertIn("2025-06-15", results[0]["text"])

    def test_search_respects_limit(self):
        results = self.service.search_events("Workshop", limit=1)
        self.assertEqual(len(results), 1)

    def test_empty_search_returns_results(self):
        results = self.service.search_events("")
        self.assertEqual(len(results), 2)


class GetMembersForEventTest(DashboardServiceTestBase):

    def test_returns_members_for_event(self):
        data = self.service.get_members_for_event(self.event1.id)
        self.assertEqual(len(data), 2)

    def test_member_data_has_required_fields(self):
        data = self.service.get_members_for_event(self.event1.id)
        for member in data:
            self.assertIn("name", member)
            self.assertIn("email", member)
            self.assertIn("event", member)
            self.assertIn("invoice_id", member)

    def test_member_without_order_has_no_invoice(self):
        data = self.service.get_members_for_event(self.event1.id)
        erika = next(m for m in data if m["email"] == "erika@example.com")
        self.assertIsNone(erika["invoice_id"])


class GetMembersWithInvoicesTest(DashboardServiceTestBase):

    def test_returns_all_members(self):
        enriched = self.service.get_members_with_invoices()
        self.assertEqual(len(enriched), 3)

    def test_member_with_order_has_order_id(self):
        enriched = self.service.get_members_with_invoices()
        max_entry = next(
            e for e in enriched if e["member"].email == "max@example.com"
        )
        self.assertEqual(max_entry["order_id"], self.order1.id)

    def test_member_without_order_has_no_order_id(self):
        enriched = self.service.get_members_with_invoices()
        erika_entry = next(
            e for e in enriched if e["member"].email == "erika@example.com"
        )
        self.assertIsNone(erika_entry["order_id"])
