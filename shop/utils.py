import math
from decimal import Decimal


def round_up(n, decimals=0):
    multiplier = 10**decimals
    return math.ceil(n * multiplier) / multiplier


def premium_price(price):
    premium_price = round_up(float(1.35) * float(price), -1)
    return round(Decimal(premium_price), 2)
