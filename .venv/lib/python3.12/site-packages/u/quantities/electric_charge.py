from .duration import DURATION, seconds
from .electric_current import ELECTRIC_CURRENT, amperes
from ..quantity import Quantity
from ..capital_quantities import MUL
from ..unit import Unit


# fmt: off
__all__ = [
    "ELECTRIC_CHARGE", "ElectricCharge",
    "coulombs", "coulomb", "C",
]
# fmt: on


ELECTRIC_CHARGE = MUL[DURATION, ELECTRIC_CURRENT]

ElectricCharge = Quantity[ELECTRIC_CHARGE]

coulombs = coulomb = C = Unit(seconds * amperes, "C")
