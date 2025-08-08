from math import pi

from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "ANGLE",
    "Angle",
    "radians", "radian", "rad",
    "degrees", "degree", "deg",
    "gradians", "gradian", "gons", "gon",
    "turns", "turn", "tr",
]
# fmt: on


class ANGLE(QUANTITY):
    pass


Angle = Quantity[ANGLE]


radians = radian = rad = Unit(Angle, "rad", 1)
degrees = degree = deg = Unit(Angle, "°", 2 * pi / 360)
gradians = gradian = gons = gon = Unit(Angle, "ᵍ", 2 * pi / 400)
turns = turn = tr = Unit(Angle, "tr", 2 * pi)
