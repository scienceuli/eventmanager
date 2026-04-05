from shop.models import Order, OrderItem
from invoices.models import Invoice
from invoices.utils import get_invoice_date

class OrderService:

    def __init__(self, form, email):
        self.form = form
        self.email = email
        self.order = None

    # -----------------------------
    # Order
    # -----------------------------
    def create_order(self):
        order = Order(
            academic=self.form.cleaned_data["academic"],
            firstname=self.form.cleaned_data["firstname"],
            lastname=self.form.cleaned_data["lastname"],
            address_line=self.form.cleaned_data["address_line"],
            company=self.form.cleaned_data["company"],
            street=self.form.cleaned_data["street"],
            city=self.form.cleaned_data["city"],
            state=self.form.cleaned_data["state"],
            postcode=self.form.cleaned_data["postcode"],
            email=self.email,
            phone=self.form.cleaned_data["phone"],
        )
        vfll = self.form.cleaned_data["vfll"]
        memberships = self.form.cleaned_data["memberships"]
        order.discounted = vfll or (len(memberships) > 0)

        # only cart items where payment is possible belong to order
        order.save()
        return order

    def ensure_order(self):
        """Create order only once."""
        if not self.order:
            self.order = self.create_order()
        return self.order

    # -----------------------------
    # Order Items
    # -----------------------------
    def add_item(self, item):
        """Add item to order."""
        order = self.ensure_order()

        return OrderItem.objects.create(
            order=order,
            event=item["event"],
            price=item["price"],
            premium_price=item["premium_price"],
            quantity=item["quantity"],
            is_action_price=item["action_price"],
        )

    # -----------------------------
    # Invoice
    # -----------------------------

    def create_invoice(self, order):
        invoice_name = (
            f"Rechnung {order.lastname}, {order.firstname} "
            f"({', '.join([ev.label for ev in order.get_registered_items_events()])})"
        )

        new_invoice = Invoice.objects.create(
            order=order,
            invoice_number=order.get_order_number,
            invoice_date=get_invoice_date(order),
            invoice_type="i",
            name=invoice_name,
            amount=order.get_total_cost(),
        )
        if new_invoice:
            new_invoice.create_invoice_message()

        return new_invoice

    # -----------------------------
    # Finalization
    # -----------------------------
    def finalize(self):
        if self.order and self.order.items.exists():
            self.create_invoice(self.order)
        elif self.order:
            self.order.delete()
        return self.order
