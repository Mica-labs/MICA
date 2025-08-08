from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "ELECTRIC_CURRENT",
    "ElectricCurrent",
    "amperes", "ampere", "A",
]
# fmt: on


class ELECTRIC_CURRENT(QUANTITY):
    pass


ElectricCurrent = Quantity[ELECTRIC_CURRENT]


amperes = ampere = A = Unit(ElectricCurrent, "A", 1)
