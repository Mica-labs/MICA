from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


__all__ = ["PIXELS", "Pixels", "pixels", "pixel", "px"]


class PIXELS(QUANTITY):
    pass


Pixels = Quantity[PIXELS]


pixels = pixel = px = Unit(Pixels, "px", 1)
