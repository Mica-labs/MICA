from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "SOLID_ANGLE",
    "SolidAngle",
    "steradians", "steradian", "sr",
]
# fmt: on


class SOLID_ANGLE(QUANTITY):
    pass


SolidAngle = Quantity[SOLID_ANGLE]


steradians = steradian = sr = Unit(SolidAngle, "sr", 1)
