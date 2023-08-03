from decimal import Decimal
from django.conf import settings
from events.models import Event


def get_action_prices(event_id, cart):
    """
    returns action_price
    two conditions:
    1. The Action Events the actual event belongs to are subset of cart events
    2. The actual event is cheapest of action events
    """
    cart_events = cart.get_events()
    print("cart_events: ", cart_events)
    # ordered by price so action_events[0] is cheapest
    event = Event.objects.get(id=event_id)
    action_events = event.payless_collection.events.all().order_by("price")
    print("action_events: ", action_events)
    cheapest_action_event = action_events[0]
    print(set(action_events).issubset(set(cart_events)))

    # action price is returned
    if (set(action_events).issubset(cart_events)) and (
        event.id == cheapest_action_event.id
    ):
        return str(Decimal("0.00")), str(Decimal("0.00"))
    else:
        return str(event.price), str(event.premium_price)


class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, event, quantity=1, override_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        event_id = str(event.id)
        if event_id not in self.cart:
            self.cart[event_id] = {
                "quantity": 0,
                "price": str(event.price),
                "premium_price": str(event.premium_price),
                "is_full": event.is_full(),
                "action_price": False,
            }
        if override_quantity:
            self.cart[event_id]["quantity"] = quantity
        else:
            self.cart[event_id]["quantity"] += quantity

        self.save()

        # we have to calculate for all events possible action prices
        self.calculate_action_prices()

    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

    def remove(self, event):
        """
        Remove an event from the cart.
        """
        event_id = str(event.id)
        if event_id in self.cart:
            del self.cart[event_id]
            self.save()

        # have to calculate the prices again because of actions
        self.calculate_action_prices()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the events
        from the database.
        """
        event_ids = self.cart.keys()
        # get the event objects and add them to the cart
        events = Event.objects.filter(id__in=event_ids)
        cart = self.cart.copy()
        for event in events:
            cart[str(event.id)]["event"] = event
        for item in cart.values():
            item["price"] = Decimal(item["price"])  # the discounted price
            item["premium_price"] = Decimal(item["premium_price"])
            item["total_price"] = item["price"] * item["quantity"]
            item["total_premium_price"] = item["premium_price"] * item["quantity"]
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_price(self):
        # returns the non discounted price only for items in payment_cart
        return sum(
            Decimal(item["premium_price"]) * item["quantity"]
            for item in self.cart.values()
            if not item["is_full"]
        )

    def get_discounted_total_price(self):
        # returns the discounted price
        return sum(
            Decimal(item["price"]) * item["quantity"]
            for item in self.cart.values()
            if not item["is_full"]
        )

    def get_events(self):
        event_ids = self.cart.keys()
        # get the event objects
        events = Event.objects.filter(id__in=event_ids)
        return events

    def get_number_of_items(self):
        return self.__len__()

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def calculate_action_prices(self):
        cart_events = self.get_events()
        print("cart_events: ", cart_events)
        # ordered by price so action_events[0] is cheapest
        for id in self.cart.keys():
            event = Event.objects.get(id=id)
            print("event: ", event)
            action_events = event.payless_collection.events.all().order_by("price")
            print("action_events: ", action_events)
            cheapest_action_event = action_events[0]
            # with this condition also not full events can be part of action
            condition_for_action = set(action_events).issubset(cart_events)
            # with this additional condition only not full events can be part of action
            if settings.ONLY_NOT_FULL_EVENTS_CAN_HAVE_ACTION:
                condition_for_action = condition_for_action and all(
                    [not event.is_full() for event in cart_events]
                )

            if condition_for_action:
                if event.payless_collection.type == "n":
                    if event.id == cheapest_action_event.id:
                        self.cart[id]["price"] = str(Decimal("0.00"))
                        self.cart[id]["premium_price"] = str(Decimal("0.00"))
                        self.cart[id]["action_pcice"] = True
                    else:
                        self.cart[id]["price"] = str(event.price)
                        self.cart[id]["premium_price"] = str(event.premium_price)
                        self.cart[id]["action_pcice"] = False
                elif event.payless_collection.type == "p":
                    self.cart[id]["price"] = str(
                        round(
                            Decimal((100 - event.payless_collection.percents) / 100)
                            * event.price,
                            2,
                        )
                    )
                    self.cart[id]["premium_price"] = str(
                        round(
                            Decimal((100 - event.payless_collection.percents) / 100)
                            * event.premium_price,
                            2,
                        )
                    )
                    self.cart[id]["action_price"] = True
            else:
                self.cart[id]["price"] = str(event.price)
                self.cart[id]["premium_price"] = str(event.premium_price)
                self.cart[id]["action_price"] = False

        self.save()
